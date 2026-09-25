# Operaciones

Cómo arrancar, **probar en local**, configurar, mantener, ampliar y **desplegar** el chatbot. Para
entender cómo está construido, ver [arquitectura.md](arquitectura.md).

---

## 1. Requisitos

- **Python 3.12** (probado; 3.10+ debería valer).
- **PostgreSQL** para el registro. En local, lo más rápido es un contenedor Docker (ver §2).

---

## 2. Arrancar y probar en local

```bash
# 1) PostgreSQL en local (contenedor Docker)
docker run -d --name store-support-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=store_support -p 5432:5432 postgres:16-alpine

# 2) La app (lee DATABASE_URL de .env; por defecto apunta a ese contenedor)
cd chatbot-guiado
cp .env.example .env          # y ajusta PANEL_PASSWORD / MCP_TOKEN
pip install -r requirements.txt
python server.py
```

URLs:

- **Como lo verá la tienda:** http://localhost:3100/?tienda=demo-01
- **Panel interno:** http://localhost:3100/panel (usuario/contraseña de tu `.env`).

### Guía de prueba (flujo completo)

1. Al entrar, escribe el **número de tienda** y pulsa "Entrar".
2. Pulsa un dispositivo (p. ej. "Impresora de tickets") y sigue los pasos con **"¡Resuelto!"** /
   **"Sigo igual"**. Comprueba que se ven las **imágenes**.
3. Llega al último paso y pulsa **"Sigue sin funcionar"**: deben aparecer los **dos contactos** de
   soporte en orden.
4. Escribe una frase ambigua (p. ej. `la impresora no imprime`): el chat te ofrecerá **elegir**. Escribe
   algo que **no** esté en el manual (p. ej. `huele a quemado`): te llevará a los menús.
5. Abre `/panel`: verás el **resumen**, las **preguntas sin resolver** y las **últimas consultas**.

> **Demo rápida sin servidor:** puedes abrir `chatbot-guiado/public/index.html` con doble clic. El
> chat funciona, pero **no se guarda el registro** (no hay servidor detrás).

---

## 3. Configuración (`.env`)

Archivo `chatbot-guiado/.env` (plantilla en `.env.example`):

| Variable | Descripción |
|---|---|
| `PORT` | Puerto del servicio (por defecto 3100). |
| `DATABASE_URL` | Cadena de conexión a PostgreSQL. |
| `PANEL_USER` | Usuario del panel `/panel`. |
| `PANEL_PASSWORD` | Contraseña del panel. **Sin ella, el panel queda abierto** (solo desarrollo). |
| `MCP_TOKEN` | Token del endpoint MCP `/mcp`. **Sin él, `/mcp` queda abierto** (solo desarrollo). |
| `TZ_PANEL` | Zona horaria de las fechas del panel (por defecto `Europe/Madrid`). |
| `EMBED_FRAME_ANCESTORS` | Dominios que pueden embeber el chat como widget (por defecto `'self'`). |

No escribas los valores reales en la documentación: van en tu `.env` local (gitignored) o en las
variables de entorno de tu hosting.

---

## 4. Identificar cada tienda

Al abrir el chat se pide el **número de tienda**. El dato se **recuerda en el dispositivo** y se guarda
con **cada consulta** para saber en el panel de qué tienda vino. Se puede prerrellenar con `?tienda=` en
la URL (así lo usa el widget embebible).

---

## 5. Ampliar el manual (alimentar el chatbot)

Todo el contenido vive en **`chatbot-guiado/public/flows.js`**. No hay que tocar código. La estructura
está en [arquitectura.md](arquitectura.md) §4.

Para añadir una incidencia, usa esta plantilla (o edítala directamente en `flows.js`):

```
Dispositivo: (ej. Impresora de tickets)   ← o uno nuevo
Problema: (ej. Imprime muy claro)
Palabras clave: claro, tenue, no se lee
Pasos:
  1. (paso 1)   [imagen: adjunta foto/captura si tienes]
  2. (paso 2)
Si no se resuelve: escalar a soporte
```

- **Imagen nueva:** colócala en `chatbot-guiado/public/images/manual/` y referénciala en el `file` del
  paso, con un `caption`.
- **Traducciones:** los textos de la interfaz y del contenido están en `public/i18n.js` (ES / IT / EN);
  si no hay traducción de una cadena, cae al español.

---

## 6. Contactos de soporte (escalado en dos niveles)

Se muestran, en orden, cuando se agotan los pasos o se pulsa "Contactar soporte". Se editan en el
bloque `soporte` de `chatbot-guiado/public/flows.js` (`primario` y `secundario`, cada uno con
`nombre`, `telefono`, `correo`).

---

## 7. El panel interno

- URL: `/panel` (en producción `https://<dominio>/panel`).
- **Autenticación básica** (`PANEL_USER` / `PANEL_PASSWORD`).
- Muestra el **resumen**, las **preguntas sin resolver** (sin respuesta o escaladas, agrupadas por
  frecuencia y con etiqueta de tipo) y las **últimas consultas** con tienda, consulta, origen y resultado.
- **Ver la conversación:** pulsa cualquier fila de "Últimas consultas" para abrir, en pestaña nueva, la
  conversación paso a paso.
- **Filtrar, paginar y exportar:** por resultado, tienda y texto; paginado (50/pág) y **exportar a CSV**.
- **Descartar / crear solución:** desde "Preguntas sin resolver" puedes descartar una pregunta o crear
  una solución que aparece en el chat al instante.
- Las fotos subidas se guardan **en la base de datos** (tabla `fotos`, `bytea`), así que entran en el
  backup de la BD y no requieren volumen.

> **Por diseño, el panel NO está enlazado desde el chatbot.** Son dos herramientas para dos públicos
> (personal de tienda vs. oficina). Se accede al panel por su propia URL.

---

## 8. Copias de seguridad

Todo (registro, soluciones y fotos) vive en **PostgreSQL**. Para un respaldo manual, `pg_dump` de la BD
(en local: `docker exec store-support-pg pg_dump -U postgres store_support > backup.sql`).

---

## 9. Despliegue

La app es un único servicio FastAPI que arranca con `uvicorn` (ver `Procfile`). Se puede desplegar en
cualquier hosting con Python y PostgreSQL.

1. Provisiona una **base de datos PostgreSQL** y anota su cadena de conexión.
2. Despliega la carpeta `chatbot-guiado/` (build Nixpacks/buildpacks con el `Procfile`, o el
   `Dockerfile` incluido). Puerto por defecto en producción: **8000**.
3. Define las variables de entorno: `DATABASE_URL`, `PANEL_USER`, `PANEL_PASSWORD`, `MCP_TOKEN`,
   `TZ_PANEL` y (si usas el widget desde otro dominio) `EMBED_FRAME_ANCESTORS`.
4. Configura el **healthcheck** apuntando a `/health` (responde `{"status":"ok"}`).
5. Reparte a cada tienda su URL: `https://<dominio>/?tienda=<id-tienda>`.

Comando de arranque (Procfile):

```
web: uvicorn server:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
```

---

## 10. Servidor MCP (`/mcp`) — consultar el registro desde Claude

El servicio expone un servidor **MCP** en `http://<host>:<puerto>/mcp` (en producción
`https://<dominio>/mcp`). Sirve para que **Claude** consulte, en solo lectura, qué preguntan las tiendas
y qué queda sin respuesta.

- **Token:** define `MCP_TOKEN`; el cliente debe enviar `Authorization: Bearer <MCP_TOKEN>`.
- **Herramientas:** `resumen_consultas`, `preguntas_sin_respuesta`, `consultas_recientes`, `estado_del_manual`.

**Claude Code (CLI):**

```bash
claude mcp add --transport http soporte-tienda http://localhost:3100/mcp \
  --header "Authorization: Bearer <TU_MCP_TOKEN_LOCAL>"
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "soporte-tienda": {
      "url": "http://localhost:3100/mcp",
      "headers": { "Authorization": "Bearer <TU_MCP_TOKEN_LOCAL>" }
    }
  }
}
```

---

## 11. Insertar el chat en otras webs (widget)

Hay un **widget flotante** embebible. Instrucciones copiables en `https://<dominio>/integration`.

- **Instalación (una línea)** en la web anfitriona, antes de `</body>`:
  ```html
  <script src="https://TU-DOMINIO/embed.js" data-tienda="042"></script>
  ```
  Pone un botón flotante **"Soporte IT"** (configurable con `data-label`) que abre el chat en un iframe.
  `data-tienda` = número de tienda (el chat entra directo sin pedirlo). Otros atributos: `data-label`,
  `data-title`, `data-color`, `data-position` (`right`/`left`).
- **Cómo funciona:** el widget abre `https://TU-DOMINIO/?tienda=<id>&embed=1` en un iframe. `embed=1`
  hace que el chat salte la pantalla de número. Al **agrandar** el chat, el botón flotante se oculta.
- **Permisos:** autoriza los dominios anfitriones con `EMBED_FRAME_ANCESTORS` (cabecera CSP
  `frame-ancestors`). Por defecto solo se permite el propio sitio.
