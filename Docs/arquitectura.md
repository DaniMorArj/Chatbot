# Arquitectura

Cómo está construido el chatbot por dentro. Para arrancarlo y operarlo, ver
[operaciones.md](operaciones.md).

---

## 1. Visión general

El chatbot razona por **árbol de decisiones + palabras clave**. No llama a ninguna IA, así que no
consume tokens ni gasta crédito. Un único servicio FastAPI sirve el frontend estático, el registro de
consultas, el panel interno, el widget embebible y un servidor MCP de solo lectura.

---

## 2. Componentes

```
Tienda (navegador)                        Servidor
┌────────────────────────┐                ┌────────────────────────────────────────────┐
│  Frontend estático      │  ── HTTP ────▶ │  server.py  (FastAPI, SIN IA)                │
│  public/                │                │   • sirve public/ (el chatbot)               │
│   • index.html          │                │   • POST /api/log → guarda en PostgreSQL las │
│   • styles.css          │                │        consultas y su resultado              │
│   • app.js  (motor)     │                │   • GET  /panel   → panel interno (protegido)│
│   • flows.js (manual)   │                │   • /mcp → servidor MCP (solo lectura)       │
│   • images/manual/      │                │                                              │
│  URL: …/?tienda=<id>    │                │  PostgreSQL (registro, soluciones, fotos)    │
└────────────────────────┘                └────────────────────────────────────────────┘
Oficina (navegador) ── HTTP + usuario/contraseña ──▶ /panel
```

| Componente | Tecnología | Función |
|---|---|---|
| Frontend | HTML + CSS + JavaScript "vanilla" (sin frameworks) | La interfaz de chat, los menús y la búsqueda por palabras clave. |
| Motor de conversación | `public/app.js` | Máquina de estados: dispositivo → problema → pasos → escalado. Sin IA. |
| Base de conocimiento | `public/flows.js` | Todo el contenido del manual estructurado (ver §4). |
| Idiomas | `public/i18n.js` | Diccionario ES / IT / EN de la interfaz y del contenido; selector con autodetección. |
| Servicio | `server.py` (FastAPI + Uvicorn) | Sirve el frontend y expone `/api/log`, `/panel`, `/mcp` y el widget. |
| Almacenamiento | **PostgreSQL** (`psycopg` 3 + pool) | Registro de consultas, soluciones y fotos (tabla `fotos`, `bytea`). |
| Empaquetado | `Procfile` + `requirements.txt` (o `Dockerfile`) | Arranca con `uvicorn`. |

**Por qué Python/FastAPI:** el frontend es estático y portable; el backend es un único fichero fácil de
desplegar en cualquier hosting con Python y PostgreSQL.

---

## 3. Flujo de una consulta

1. Al entrar, una **pantalla inicial** pide el **número de tienda** (se recuerda en el dispositivo, y
   puede llegar por `?tienda=<id>` en la URL).
2. El usuario **elige por menús** (dispositivo → problema) o **escribe** una incidencia.
3. Si escribe, `app.js` puntúa cada dispositivo/problema por **palabras clave** (ignorando mayúsculas y
   tildes). Una coincidencia → lanza su flujo; varias → **pregunta a cuál se refiere**; ninguna → menús.
4. Cada **paso** se muestra de uno en uno, con su imagen si la tiene, y botones "¡Resuelto!" /
   "Sigo igual". Al agotar los pasos (o pulsar "Contactar soporte") se muestra el **escalado**.
5. Cada incidencia se registra una vez al cerrarse vía `POST /api/log` con su **resultado**
   (`resuelto` / `escalado` / `sin_respuesta`) y la tienda. Es "fail-safe": si no hay servidor, el chat
   sigue funcionando aunque no se guarde.

---

## 4. La base de conocimiento (`public/flows.js`)

Es el corazón del chatbot y **se puede editar sin tocar el resto del código**. Estructura:

```js
window.FLOWS = {
  soporte: {
    primario:   { nombre, telefono, correo },   // a quién se llama primero
    secundario: { nombre, telefono, correo },    // si el primero no responde
  },
  devices: [
    {
      id, label, emoji,
      keywords: [ ... ],                          // para la búsqueda por texto
      problems: [
        {
          id, label, keywords: [ ... ],
          intro: "…",                             // opcional
          steps: [
            { text: "…", image: { file, caption } },  // image es opcional
            ...
          ],
          escalate_note: "…"                      // opcional
        }
      ]
    }
  ]
}
```

- **Las imágenes** referenciadas en `image.file` viven en `public/images/manual/`. Se muestran en el
  paso y se pueden ampliar al pulsarlas.
- **Los contactos de soporte** (escalado en dos niveles) están en `soporte`.

Cómo ampliarlo: ver [operaciones.md](operaciones.md) §"Ampliar el manual".

---

## 5. Registro de consultas

- **Qué guarda:** cada incidencia consultada, con su resultado. Campos: fecha (UTC), `tienda_numero`,
  `tienda_nombre`, `consulta`, `origen` (`texto`/`menu`) y `resultado`.
- **Cuándo:** una vez por incidencia, al cerrarse.
- **Dónde:** tabla `consultas` en PostgreSQL.
- **Para qué:** el panel resume resultados y lista las **preguntas sin resolver** → qué falta por añadir.
- **Privacidad:** no se guardan datos personales; solo el número/nombre de tienda y el texto.

---

## 6. El panel interno (`/panel`)

- Página HTML generada por `server.py` con un **resumen** (total, resueltas, escaladas, sin respuesta),
  la lista de **preguntas sin resolver** (sin respuesta o escaladas, agrupadas por frecuencia y con
  etiqueta de tipo) y las **últimas consultas**.
- **Protegido con autenticación básica** (`PANEL_USER` / `PANEL_PASSWORD`). Si no se define contraseña,
  el panel queda abierto (solo desarrollo, con aviso por consola).

### Alimentar el chat desde el panel (soluciones)

El manual base sigue en `flows.js`. El panel permite **añadir soluciones nuevas** que se guardan en la
base de datos y que el chat **fusiona** con el manual — sin redesplegar.

- **Tabla `soluciones`**: `device_id`, `label`, `keywords`, `intro`, `escalate_note`, `pasos_json`, `creada`.
- **Fotos:** se suben desde el editor y se guardan **en la BD** (tabla `fotos`: `nombre`, `mime`,
  `data` `bytea`); se sirven en `GET /uploads/<archivo>`.
- **Flujo:** cada pregunta "sin respuesta" tiene un botón **"Crear solución"** que abre el editor
  prerrellenado; al guardar se inserta la solución y la pregunta se añade a las palabras clave.
- **El chat** pide `GET /api/soluciones` (público, solo lectura) al arrancar y las fusiona.

---

## 7. Seguridad

- El frontend se sirve **solo desde `public/`**: `server.py`, `.env` y la base de datos **no quedan
  expuestos** (verificado: `/server.py` → 404).
- El panel está detrás de contraseña (básica). Define `PANEL_PASSWORD` en producción.
- El registro limita el tamaño del texto guardado y escapa el contenido al mostrarlo (evita inyección
  de HTML).
- **Widget/iframe:** los dominios que pueden embeber el chat se controlan con la variable
  `EMBED_FRAME_ANCESTORS` (cabecera `Content-Security-Policy: frame-ancestors`).

---

## 8. Servidor MCP (`/mcp`)

El servicio expone un **servidor MCP** (Model Context Protocol) en **`/mcp`**, para que **Claude u
otras IAs** consulten el registro y el manual y ayuden a **mejorar el chat** (analizar qué preguntan
las tiendas, qué queda sin respuesta, y proponer soluciones).

- **Transporte:** HTTP "streamable" del SDK oficial de MCP (`mcp`), montado en la misma app FastAPI.
- **Solo lectura:** no modifica nada. Las soluciones se crean desde el panel.
- **Protegido por token:** si `MCP_TOKEN` está definido, el cliente debe enviar
  `Authorization: Bearer <MCP_TOKEN>`.
- **Herramientas:** `resumen_consultas`, `preguntas_sin_respuesta(limite)`,
  `consultas_recientes(limite, resultado, tienda)`, `estado_del_manual`.
