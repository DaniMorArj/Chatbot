# Chatbot de Soporte IT para Tiendas

Chatbot que ayuda al **personal de tienda** a resolver por sí mismo las incidencias del material
informático (impresoras, TPV, lector de códigos, altavoz, impresora fiscal…), guiándose por un
**manual de material informático** ([Docs/Manual Uso del Material Informatico de Tienda.pdf](Manual%20Uso%20del%20Material%20Informatico%20de%20Tienda.pdf)).

- Guía paso a paso, con lenguaje sencillo y **mostrando imágenes** del manual.
- Si no se resuelve, muestra los **contactos de soporte** en dos niveles.
- Registra las incidencias que no sabe resolver para ir **ampliando** el manual.
- **Sin coste de IA:** el motor es un árbol de decisiones + búsqueda por palabras clave, no llama a ningún modelo.

## Documentación (`Docs/`)

| Documento | Para qué |
|---|---|
| **[README.md](README.md)** (este) | Visión general e índice. |
| **[arquitectura.md](arquitectura.md)** | Cómo está construido por dentro: componentes, flujo de datos, stack, base de conocimiento, seguridad, MCP. |
| **[operaciones.md](operaciones.md)** | Arrancar y probar en local, configurar, ampliar el manual, usar el panel y desplegar. |

## Estructura del repositorio

```
.
├── Docs/                     ← documentación + el manual (PDF)
│   ├── README.md · arquitectura.md · operaciones.md
│   └── Manual Uso del Material Informatico de Tienda.pdf
│
└── chatbot-guiado/           ← el servicio que se despliega
    ├── server.py · requirements.txt · Dockerfile · Procfile · .env.example
    ├── public/               ← el chatbot: index.html, styles.css, app.js, flows.js, i18n.js, embed.js, images/
    └── data/                 ← (se crea sola; datos locales)
```

## Arranque rápido

```bash
cd chatbot-guiado
pip install -r requirements.txt
python server.py
```

- Chat (como lo verá la tienda): http://localhost:3100/?tienda=demo-01
- Panel interno: http://localhost:3100/panel

Requiere PostgreSQL en marcha (ver [operaciones.md](operaciones.md) §2).
