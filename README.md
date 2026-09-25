# Chatbot de Soporte IT para Tiendas

Chatbot **guiado** (sin coste de IA) que ayuda al personal de tienda a resolver por sí mismo las
incidencias del material informático (impresoras, TPV, lector de códigos, altavoz, impresora fiscal…).
Guía paso a paso con imágenes; si no lo resuelve, escala a soporte; y registra lo que no sabe resolver
para ir ampliando el manual.

- **Chatbot guiado** (`/`): ayuda paso a paso, sin IA, sin coste de tokens.
- **Panel interno** (`/panel`): protegido con usuario/contraseña; revisa consultas y añade soluciones.
- **Servidor MCP** (`/mcp`): solo lectura, protegido con token, para analizar el registro desde Claude.
- **Widget embebible** (`/embed.js` + `/integration`): inserta el chat en otra web con una línea.

Multiidioma **ES / IT / EN** con autodetección.

## Stack

Python 3.12 · FastAPI · Uvicorn · **PostgreSQL** (`psycopg` 3 + pool) · frontend estático (HTML/CSS/JS
sin frameworks) · MCP mediante el SDK oficial `mcp`. Las fotos se guardan en la BD (`bytea`), sin volumen.

## Arranque rápido

```bash
# PostgreSQL local (Docker)
docker run -d --name store-support-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=store_support -p 5432:5432 postgres:16-alpine

cd chatbot-guiado
cp .env.example .env          # ajusta PANEL_PASSWORD / MCP_TOKEN
pip install -r requirements.txt
python server.py              # http://localhost:3100  (panel en /panel)
```

## Documentación

Todo en [`Docs/`](Docs/): [visión general](Docs/README.md), [arquitectura](Docs/arquitectura.md) y
[operaciones/despliegue](Docs/operaciones.md).

## Configuración

Variables de entorno (plantilla en [`chatbot-guiado/.env.example`](chatbot-guiado/.env.example)):
`DATABASE_URL`, `PANEL_USER`, `PANEL_PASSWORD`, `MCP_TOKEN`, `TZ_PANEL`, `EMBED_FRAME_ANCESTORS`.
Los secretos van solo en `.env` (gitignored) o en las variables de entorno del hosting.

## Licencia

Sin licencia definida. Añade la que prefieras (por ejemplo MIT) antes de publicarlo si quieres permitir su reutilización.
