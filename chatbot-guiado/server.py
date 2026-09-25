"""Servicio del chatbot guiado de soporte de tienda.

- Sirve el chatbot estático (sin IA, sin coste de tokens).
- Registra CADA consulta con su resultado (resuelto / escalado / sin respuesta) y la tienda.
- Panel interno (protegido) para verlas y para AÑADIR soluciones nuevas (con fotos) que alimentan
  el chat, especialmente para las preguntas que se quedaron sin respuesta.
"""
from __future__ import annotations

import csv
import io
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from mcp.server.fastmcp import FastMCP
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- Configuración ---
PORT = int(os.getenv("PORT", "3100"))
# Cadena de conexión a PostgreSQL (variable de entorno DATABASE_URL).
# El valor por defecto es solo para desarrollo local (contenedor Docker de Postgres).
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/store_support")

PANEL_USER = os.getenv("PANEL_USER", "oficina")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "")
if not PANEL_PASSWORD:
    print("\n[AVISO] PANEL_PASSWORD no configurada: el panel /panel estara ABIERTO. Ponla en .env antes de desplegar.\n")

# Token para el endpoint MCP (/mcp). Si se define, el cliente debe enviar Authorization: Bearer <token>.
MCP_TOKEN = os.getenv("MCP_TOKEN", "")
if not MCP_TOKEN:
    print("[AVISO] MCP_TOKEN no configurado: el endpoint /mcp estara ABIERTO. Ponlo en .env antes de desplegar.")

# Orígenes permitidos para embeber el chat como widget (cabecera CSP frame-ancestors).
# Por defecto solo el propio sitio; para permitir otras webs: "'self' https://*.tu-dominio.com".
EMBED_FRAME_ANCESTORS = os.getenv("EMBED_FRAME_ANCESTORS", "'self'")

RESULTADOS = {"resuelto", "escalado", "sin_respuesta"}
EXT_IMG = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MIME_BY_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
               ".gif": "image/gif", ".webp": "image/webp"}
MAX_PASOS = 6
PAGE_SIZE = 50  # consultas por página en el panel

try:
    TZ = ZoneInfo(os.getenv("TZ_PANEL", "Europe/Madrid"))
except Exception:  # noqa: BLE001
    TZ = timezone.utc


def fmt_fecha(ts: str) -> str:
    """Convierte una fecha ISO (UTC) al horario local del panel (Europe/Madrid)."""
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TZ).strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return ts


# Pool de conexiones a PostgreSQL. Las filas se devuelven como diccionarios (row["columna"]).
pool = ConnectionPool(
    conninfo=DATABASE_URL, min_size=1, max_size=5,
    kwargs={"row_factory": dict_row}, open=True,
)


def db():
    """Conexión del pool como context manager: `with db() as conn:` (commit al salir)."""
    return pool.connection()


def init_db():
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS consultas (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                ts TEXT NOT NULL,
                tienda_numero TEXT NOT NULL DEFAULT '',
                tienda_nombre TEXT NOT NULL DEFAULT '',
                consulta TEXT NOT NULL,
                origen TEXT NOT NULL DEFAULT 'texto',
                resultado TEXT NOT NULL,
                conversacion TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        # Preguntas "sin respuesta" ya atendidas (para que no sigan en la lista de pendientes).
        conn.execute(
            "CREATE TABLE IF NOT EXISTS atendidas (consulta_norm TEXT PRIMARY KEY, ts TEXT NOT NULL)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS soluciones (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                creada TEXT NOT NULL,
                device_id TEXT NOT NULL,
                label TEXT NOT NULL,
                keywords TEXT NOT NULL DEFAULT '',
                intro TEXT NOT NULL DEFAULT '',
                escalate_note TEXT NOT NULL DEFAULT '',
                pasos_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        # Fotos subidas desde el panel (antes en disco; ahora dentro de la BD para no depender de un volumen).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fotos (
                nombre TEXT PRIMARY KEY,
                mime TEXT NOT NULL DEFAULT 'application/octet-stream',
                data BYTEA NOT NULL,
                creada TEXT NOT NULL
            )
            """
        )


init_db()


def cargar_dispositivos():
    """Lee public/flows.js para conocer los dispositivos (para el desplegable del editor)."""
    try:
        txt = (BASE_DIR / "public" / "flows.js").read_text(encoding="utf-8").strip()
        txt = txt[len("window.FLOWS ="):].strip().rstrip(";").strip()
        data = json.loads(txt)
        return [{"id": d["id"], "label": d["label"], "emoji": d.get("emoji", "")} for d in data["devices"]]
    except Exception as e:  # noqa: BLE001
        print("No se pudo leer flows.js:", e)
        return []


def manual_completo():
    """Devuelve el manual completo (base flows.js + soluciones del panel) en forma compacta."""
    devices = {}
    try:
        txt = (BASE_DIR / "public" / "flows.js").read_text(encoding="utf-8").strip()
        txt = txt[len("window.FLOWS ="):].strip().rstrip(";").strip()
        data = json.loads(txt)
        for d in data["devices"]:
            devices[d["id"]] = {
                "dispositivo": d["label"],
                "problemas": [
                    {"titulo": p["label"], "palabras_clave": p.get("keywords", []),
                     "pasos": [s.get("text", "") for s in p.get("steps", [])]}
                    for p in d.get("problems", [])
                ],
            }
    except Exception as e:  # noqa: BLE001
        print("manual_completo: no se pudo leer flows.js:", e)
    with db() as conn:
        sols = conn.execute("SELECT device_id, label, keywords, pasos_json FROM soluciones ORDER BY id").fetchall()
    for s in sols:
        dev = devices.setdefault(s["device_id"], {"dispositivo": s["device_id"], "problemas": []})
        dev["problemas"].append({
            "titulo": s["label"],
            "palabras_clave": [k.strip() for k in (s["keywords"] or "").split(",") if k.strip()],
            "pasos": [p.get("text", "") for p in json.loads(s["pasos_json"] or "[]")],
            "origen": "panel",
        })
    return list(devices.values())


# ---------------- Servidor MCP (/mcp) — solo lectura del registro y del manual ----------------
mcp = FastMCP("Panel Soporte Tienda", streamable_http_path="/", stateless_http=True)


@mcp.tool()
def resumen_consultas() -> dict:
    """Total de consultas de las tiendas y cuántas fueron resueltas, escaladas o quedaron sin respuesta."""
    with db() as conn:
        d = {r["resultado"]: r["n"] for r in conn.execute(
            "SELECT resultado, COUNT(*) n FROM consultas GROUP BY resultado").fetchall()}
    return {"total": sum(d.values()), "resueltas": d.get("resuelto", 0),
            "escaladas": d.get("escalado", 0), "sin_respuesta": d.get("sin_respuesta", 0)}


@mcp.tool()
def preguntas_sin_respuesta(limite: int = 50) -> list:
    """Preguntas que el chat NO resolvió (quedaron SIN respuesta o se ESCALARON a soporte),
    agrupadas y ordenadas por frecuencia. Cada una indica cuántas veces se escaló y cuántas
    se quedó sin respuesta.

    Úsalo para saber qué falta por añadir o mejorar en el manual.
    """
    limite = max(1, min(limite, 500))
    with db() as conn:
        filas = conn.execute(
            "SELECT MAX(consulta) AS consulta, COUNT(*) veces, "
            "SUM(CASE WHEN resultado='escalado' THEN 1 ELSE 0 END) AS escaladas, "
            "SUM(CASE WHEN resultado='sin_respuesta' THEN 1 ELSE 0 END) AS sin_respuesta, "
            "MAX(ts) ultima FROM consultas WHERE resultado IN ('escalado', 'sin_respuesta') "
            "AND lower(trim(consulta)) NOT IN (SELECT consulta_norm FROM atendidas) "
            "GROUP BY lower(consulta) ORDER BY veces DESC, ultima DESC LIMIT %s", (limite,)).fetchall()
    return [{"pregunta": r["consulta"], "veces": r["veces"], "escaladas": int(r["escaladas"] or 0),
             "sin_respuesta": int(r["sin_respuesta"] or 0), "ultima_vez": r["ultima"]} for r in filas]


@mcp.tool()
def consultas_recientes(limite: int = 100, resultado: str = "", tienda: str = "") -> list:
    """Últimas consultas de las tiendas.

    Filtros opcionales: resultado ('resuelto' | 'escalado' | 'sin_respuesta') y tienda
    (texto a buscar en el número o el nombre de la tienda).
    """
    limite = max(1, min(limite, 500))
    sql = "SELECT ts, tienda_numero, tienda_nombre, consulta, origen, resultado FROM consultas"
    cond, params = [], []
    if resultado in RESULTADOS:
        cond.append("resultado=%s"); params.append(resultado)
    if tienda.strip():
        cond.append("(tienda_numero LIKE %s OR tienda_nombre LIKE %s)"); params += [f"%{tienda.strip()}%"] * 2
    if cond:
        sql += " WHERE " + " AND ".join(cond)
    sql += " ORDER BY id DESC LIMIT %s"; params.append(limite)
    with db() as conn:
        filas = conn.execute(sql, params).fetchall()
    return [dict(r) for r in filas]


@mcp.tool()
def estado_del_manual() -> list:
    """Contenido actual del manual (dispositivos, problemas y pasos), incluyendo las soluciones
    añadidas desde el panel. Úsalo para ver qué está cubierto y proponer mejoras."""
    return manual_completo()


mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield
    pool.close()


app = FastAPI(title="Chatbot Soporte Tienda (guiado)", lifespan=lifespan)
security = HTTPBasic(auto_error=False)


@app.middleware("http")
async def middleware(request, call_next):
    # Protege /mcp con token (si está configurado) y evita cachés de versiones antiguas.
    if MCP_TOKEN and request.url.path.startswith("/mcp"):
        if request.headers.get("authorization", "") != f"Bearer {MCP_TOKEN}":
            return JSONResponse(status_code=401, content={"error": "Token MCP inválido o ausente."})
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    # Orígenes autorizados a embeber el chat en un iframe (configurable por entorno).
    response.headers["Content-Security-Policy"] = f"frame-ancestors {EMBED_FRAME_ANCESTORS}"
    return response


@app.get("/health")
def health():
    """Comprobación de estado (healthcheck) del servicio."""
    return {"status": "ok"}


@app.get("/integration", response_class=HTMLResponse)
def integration():
    """Página con instrucciones para insertar el chat (widget) en otras webs."""
    return HTMLResponse(INTEGRATION_HTML)


INTEGRATION_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Integrar el chatbot de soporte</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:820px;margin:0 auto;padding:32px 20px;color:#1c2430;line-height:1.5}
 h1{font-size:22px} h2{font-size:16px;margin-top:28px}
 code,pre{background:#f4f5f7;border:1px solid #e2e5ea;border-radius:8px}
 code{padding:2px 6px} pre{padding:14px;overflow:auto}
 table{border-collapse:collapse;width:100%;margin:10px 0} th,td{border:1px solid #e2e5ea;padding:8px 10px;text-align:left;font-size:14px}
 th{background:#f7f9fc} .muted{color:#6b7482;font-size:14px}
</style></head>
<body>
 <h1>Integrar el chatbot de soporte en otra app</h1>
 <p class="muted">Widget flotante para insertar el chat de soporte de tienda en cualquier web.</p>

 <h2>1. Anade una linea</h2>
 <p>En la pagina donde quieras el chat, antes de <code>&lt;/body&gt;</code>:</p>
 <pre>&lt;script src="https://TU-DOMINIO/embed.js" data-tienda="042"&gt;&lt;/script&gt;</pre>
 <p class="muted">Sustituye <code>042</code> por el numero de la tienda (tu app ya lo conoce). Aparecera un boton flotante "Soporte" que abre el chat.</p>

 <h2>2. Opciones (atributos del &lt;script&gt;)</h2>
 <table>
  <tr><th>Atributo</th><th>Para que</th><th>Por defecto</th></tr>
  <tr><td><code>data-tienda</code></td><td>Numero de tienda. Si se pasa, el chat entra directo sin pedirlo.</td><td>&mdash;</td></tr>
  <tr><td><code>data-label</code></td><td>Texto del boton flotante.</td><td>Soporte IT</td></tr>
  <tr><td><code>data-title</code></td><td>Titulo de la cabecera del widget.</td><td>Asistente de soporte</td></tr>
  <tr><td><code>data-color</code></td><td>Color del boton (CSS).</td><td>#1c2430</td></tr>
  <tr><td><code>data-position</code></td><td>Lado del boton: <code>right</code> o <code>left</code>.</td><td>right</td></tr>
 </table>

 <h2>3. Ficheros</h2>
 <ul>
  <li>Widget: <a href="/embed.js">/embed.js</a> (se referencia por URL; no hace falta copiarlo, pero puedes descargarlo si quieres auto-alojarlo).</li>
  <li>El chat vive en el dominio donde despliegues esta app; el widget lo abre en un iframe con <code>?tienda=&lt;id&gt;&amp;embed=1</code>.</li>
 </ul>

 <h2>Notas</h2>
 <ul>
  <li>Autoriza los dominios que pueden embeber el chat con la variable <code>EMBED_FRAME_ANCESTORS</code> (cabecera <code>Content-Security-Policy: frame-ancestors</code>).</li>
  <li>El chat no requiere login; solo necesita el numero de tienda. El registro de consultas se guarda en este servicio.</li>
  <li>Sin dependencias ni build: es JavaScript plano.</li>
 </ul>
 <p class="muted">Consulta el README del proyecto para más detalles.</p>
</body></html>"""


# ---------------- Registro de consultas ----------------
class LogEntry(BaseModel):
    consulta: str
    resultado: str
    origen: str | None = "texto"
    tienda_numero: str | None = ""
    tienda_nombre: str | None = ""
    conversacion: list | None = None


def _sanea_conversacion(conv) -> str:
    safe = []
    for m in (conv or [])[:100]:
        if not isinstance(m, dict):
            continue
        item = {"who": str(m.get("who", ""))[:10], "text": str(m.get("text", ""))[:1000]}
        if m.get("imagen"):
            item["imagen"] = str(m.get("imagen"))[:300]
        safe.append(item)
    return json.dumps(safe, ensure_ascii=False)


@app.post("/api/log")
def log_consulta(entry: LogEntry):
    consulta = (entry.consulta or "").strip()[:500]
    resultado = (entry.resultado or "").strip()
    if not consulta or resultado not in RESULTADOS:
        return JSONResponse(status_code=400, content={"error": "datos de registro inválidos"})
    origen = (entry.origen or "texto").strip()[:20] or "texto"
    numero = (entry.tienda_numero or "").strip()[:50]
    nombre = (entry.tienda_nombre or "").strip()[:120]
    conversacion = _sanea_conversacion(entry.conversacion)
    with db() as conn:
        conn.execute(
            "INSERT INTO consultas (ts, tienda_numero, tienda_nombre, consulta, origen, resultado, conversacion) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), numero, nombre, consulta, origen, resultado, conversacion),
        )
    return {"ok": True}


# ---------------- Soluciones (lectura pública para el chat) ----------------
@app.get("/api/soluciones")
def soluciones_publicas():
    with db() as conn:
        filas = conn.execute("SELECT * FROM soluciones ORDER BY id ASC").fetchall()
    out = []
    for r in filas:
        pasos = json.loads(r["pasos_json"] or "[]")
        steps = []
        for p in pasos:
            img = None
            if p.get("imagen"):
                img = {"src": f"uploads/{p['imagen']}", "caption": ""}
            steps.append({"text": p.get("text", ""), "image": img})
        out.append({
            "id": r["id"],
            "device_id": r["device_id"],
            "label": r["label"],
            "keywords": [k.strip() for k in (r["keywords"] or "").split(",") if k.strip()],
            "intro": r["intro"] or "",
            "escalate_note": r["escalate_note"] or "",
            "steps": steps,
        })
    return out


@app.get("/uploads/{name}")
def servir_upload(name: str):
    # Sirve una imagen subida, ahora almacenada en la BD (tabla fotos).
    with db() as conn:
        r = conn.execute("SELECT mime, data FROM fotos WHERE nombre=%s", (name,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="no encontrado")
    return Response(content=bytes(r["data"]), media_type=r["mime"] or "application/octet-stream")


# ---------------- Autenticación del panel ----------------
def require_panel_auth(request: Request, credentials: HTTPBasicCredentials | None = Depends(security)):
    # Autenticación básica usuario+contraseña (o abierto si no hay contraseña definida).
    if not PANEL_PASSWORD:
        return
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación requerida",
                            headers={"WWW-Authenticate": "Basic"})
    if not (secrets.compare_digest(credentials.username, PANEL_USER) and
            secrets.compare_digest(credentials.password, PANEL_PASSWORD)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas",
                            headers={"WWW-Authenticate": "Basic"})


# ---------------- Panel: dashboard ----------------
def _filtro_consultas(resultado: str, tienda: str, q: str):
    cond, params = [], []
    if resultado in RESULTADOS:
        cond.append("resultado=%s"); params.append(resultado)
    if tienda.strip():
        cond.append("(tienda_numero LIKE %s OR tienda_nombre LIKE %s)"); params += [f"%{tienda.strip()}%"] * 2
    if q.strip():
        cond.append("consulta LIKE %s"); params.append(f"%{q.strip()}%")
    where = (" WHERE " + " AND ".join(cond)) if cond else ""
    return where, params


@app.get("/panel", response_class=HTMLResponse)
def panel(resultado: str = "", tienda: str = "", q: str = "", pag: int = 1, _auth=Depends(require_panel_auth)):
    pag = max(1, pag)
    where, params = _filtro_consultas(resultado, tienda, q)
    with db() as conn:
        resumen = {r["resultado"]: r["n"] for r in conn.execute(
            "SELECT resultado, COUNT(*) AS n FROM consultas GROUP BY resultado").fetchall()}
        total = sum(resumen.values())
        sin_resp = conn.execute(
            "SELECT MAX(consulta) AS q, COUNT(*) AS n, "
            "SUM(CASE WHEN resultado='escalado' THEN 1 ELSE 0 END) AS n_esc, "
            "SUM(CASE WHEN resultado='sin_respuesta' THEN 1 ELSE 0 END) AS n_sin, "
            "MAX(ts) AS ultima FROM consultas "
            "WHERE resultado IN ('escalado', 'sin_respuesta') AND lower(trim(consulta)) NOT IN (SELECT consulta_norm FROM atendidas) "
            "GROUP BY lower(consulta) ORDER BY n DESC, ultima DESC LIMIT 100"
        ).fetchall()
        total_filtradas = conn.execute("SELECT COUNT(*) c FROM consultas" + where, params).fetchone()["c"]
        ultimas = conn.execute(
            "SELECT id, ts, tienda_numero, tienda_nombre, consulta, origen, resultado FROM consultas"
            + where + " ORDER BY id DESC LIMIT %s OFFSET %s", params + [PAGE_SIZE, (pag - 1) * PAGE_SIZE]
        ).fetchall()
        soluciones = conn.execute("SELECT * FROM soluciones ORDER BY id DESC").fetchall()
    filtros = {"resultado": resultado, "tienda": tienda, "q": q}
    paginacion = {"pag": pag, "size": PAGE_SIZE, "total": total_filtradas}
    return HTMLResponse(render_panel(resumen, total, sin_resp, ultimas, soluciones, filtros, paginacion))


def render_panel(resumen, total, sin_resp, ultimas, soluciones, filtros, paginacion) -> str:
    def badge(res):
        c = {"resuelto": "ok", "escalado": "warn", "sin_respuesta": "bad"}.get(res, "")
        t = {"resuelto": "Resuelto", "escalado": "Escalado", "sin_respuesta": "Sin respuesta"}.get(res, res)
        return f'<span class="badge {c}">{t}</span>'

    def tipo_badges(r):
        parts = []
        n_esc, n_sin = int(r["n_esc"] or 0), int(r["n_sin"] or 0)
        if n_esc:
            parts.append(f"<span class='badge warn'>{n_esc} escalada{'s' if n_esc != 1 else ''}</span>")
        if n_sin:
            parts.append(f"<span class='badge bad'>{n_sin} sin respuesta</span>")
        return " ".join(parts)

    sin_rows = "".join(
        f"<tr><td>{escape(r['q'])}</td><td class='num'>{r['n']}</td>"
        f"<td>{tipo_badges(r)}</td>"
        f"<td><a class='btn' href='/panel/nueva?consulta={quote(r['q'])}'>+ Crear solución</a> "
        f"<form method='post' action='/panel/atender' style='display:inline'>"
        f"<input type='hidden' name='consulta' value=\"{escape(r['q'])}\">"
        f"<button class='btn ghost'>Descartar</button></form></td></tr>"
        for r in sin_resp
    ) or "<tr><td colspan='4' class='vacio'>No hay preguntas sin resolver pendientes. 🎉</td></tr>"

    ult_rows = "".join(
        f"<tr class='clicable' onclick=\"window.open('/panel/consulta/{r['id']}','_blank')\" "
        f"title='Abrir la conversación en una pestaña nueva'>"
        f"<td>{fmt_fecha(r['ts'])}</td><td>{escape(r['tienda_numero'])}{' · ' + escape(r['tienda_nombre']) if r['tienda_nombre'] else ''}</td>"
        f"<td class='consulta'><span class='trunc' title=\"{escape(r['consulta'])}\">{escape(r['consulta'])}</span></td>"
        f"<td>{'texto' if r['origen']=='texto' else 'menú'}</td>"
        f"<td>{badge(r['resultado'])}</td>"
        f"<td class='chev'>›</td></tr>"
        for r in ultimas
    ) or "<tr><td colspan='6' class='vacio'>Sin registros.</td></tr>"

    # Barra de filtros para "Últimas consultas" + exportar CSV.
    fr, ft, fq = filtros.get("resultado", ""), filtros.get("tienda", ""), filtros.get("q", "")
    def sel(v):
        return " selected" if fr == v else ""
    qs = f"resultado={quote(fr)}&tienda={quote(ft)}&q={quote(fq)}"
    filtro_html = f"""
    <form method="get" action="/panel" class="filtros">
      <select name="resultado">
        <option value=""{' selected' if not fr else ''}>Todos los resultados</option>
        <option value="resuelto"{sel('resuelto')}>Resueltas</option>
        <option value="escalado"{sel('escalado')}>Escaladas</option>
        <option value="sin_respuesta"{sel('sin_respuesta')}>Sin respuesta</option>
      </select>
      <input type="text" name="tienda" value="{escape(ft)}" placeholder="Tienda (nº o nombre)">
      <input type="text" name="q" value="{escape(fq)}" placeholder="Texto de la consulta">
      <button class="btn primary">Filtrar</button>
      <a class="btn" href="/panel">Limpiar</a>
      <a class="btn" href="/panel/export.csv?{qs}">⬇ Exportar CSV</a>
    </form>"""

    # Controles de paginación de "Últimas consultas".
    pag, size, totalf = paginacion["pag"], paginacion["size"], paginacion["total"]
    paginas = max(1, (totalf + size - 1) // size)
    prev = (f"<a class='btn' href='/panel?{qs}&pag={pag - 1}'>‹ Anteriores</a>" if pag > 1
            else "<span class='btn disabled'>‹ Anteriores</span>")
    sig = (f"<a class='btn' href='/panel?{qs}&pag={pag + 1}'>Siguientes ›</a>" if pag < paginas
           else "<span class='btn disabled'>Siguientes ›</span>")
    paginacion_html = (f"<div class='paginacion'>{prev}"
                       f"<span class='pag-info'>Página {pag} de {paginas} · {totalf} consultas</span>{sig}</div>")

    sol_rows = ""
    for r in soluciones:
        pasos = json.loads(r["pasos_json"] or "[]")
        sol_rows += (
            f"<tr><td>{escape(r['device_id'])}</td><td>{escape(r['label'])}</td>"
            f"<td>{len(pasos)} paso(s)</td><td>{escape(r['keywords'])}</td>"
            f"<td><form method='post' action='/panel/borrar' onsubmit=\"return confirm('¿Borrar esta solución?')\">"
            f"<input type='hidden' name='id' value='{r['id']}'><button class='btn danger'>Borrar</button></form></td></tr>"
        )
    sol_rows = sol_rows or "<tr><td colspan='5' class='vacio'>Aún no has añadido soluciones.</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel · Soporte tienda</title>{PANEL_CSS}</head>
<body>
  <header><h1>Panel de soporte</h1><p>Consultas de las tiendas y soluciones que alimentan el chat.</p></header>
  <main>
    <div class="cards">
      <div class="card"><div class="n">{total}</div><div class="l">Consultas</div></div>
      <div class="card ok"><div class="n">{resumen.get('resuelto', 0)}</div><div class="l">Resueltas</div></div>
      <div class="card warn"><div class="n">{resumen.get('escalado', 0)}</div><div class="l">Escaladas</div></div>
      <div class="card bad"><div class="n">{resumen.get('sin_respuesta', 0)}</div><div class="l">Sin respuesta</div></div>
    </div>

    <div class="head-row"><h2>Preguntas sin resolver</h2><a class="btn primary" href="/panel/nueva">+ Nueva solución</a></div>
    <p class="hint">Incluye las consultas <strong>sin respuesta</strong> y las <strong>escaladas a soporte</strong> (no se resolvieron en el chat). Crea una solución para las recurrentes: aparecerá en el chat al momento.</p>
    <table><thead><tr><th>Pregunta</th><th class="num">Veces</th><th>Tipo</th><th>Acción</th></tr></thead><tbody>{sin_rows}</tbody></table>

    <h2>Soluciones añadidas (activas en el chat)</h2>
    <table><thead><tr><th>Dispositivo</th><th>Título</th><th>Pasos</th><th>Palabras clave</th><th></th></tr></thead><tbody>{sol_rows}</tbody></table>

    <h2>Últimas consultas</h2>
    <p class="hint">Pulsa una fila para ver la conversación que tuvo la tienda con el chat.</p>
    {filtro_html}
    <table class="ultimas"><thead><tr><th>Fecha</th><th>Tienda</th><th>Consulta</th><th>Origen</th><th>Resultado</th><th></th></tr></thead><tbody>{ult_rows}</tbody></table>
    {paginacion_html}
  </main>
</body></html>"""


# ---------------- Panel: editor de solución ----------------
@app.get("/panel/nueva", response_class=HTMLResponse)
def nueva_solucion(consulta: str = "", device: str = "", _auth=Depends(require_panel_auth)):
    dispositivos = cargar_dispositivos()
    opts = "".join(
        f'<option value="{escape(d["id"])}" {"selected" if d["id"]==device else ""}>{escape(d["emoji"])} {escape(d["label"])}</option>'
        for d in dispositivos
    )
    opts += '<option value="otros">❓ Otros</option>'
    label_val = escape(consulta)
    kw_val = escape(consulta)
    pasos_html = ""
    for i in range(1, MAX_PASOS + 1):
        pasos_html += f"""
        <fieldset class="paso"><legend>Paso {i}{' (obligatorio)' if i==1 else ' (opcional)'}</legend>
          <textarea name="paso_texto_{i}" rows="2" placeholder="Qué debe hacer en este paso"></textarea>
          <label class="file">Foto (opcional): <input type="file" name="paso_img_{i}" accept="image/*"></label>
        </fieldset>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nueva solución · Panel</title>{PANEL_CSS}</head>
<body>
  <header><h1>Crear solución</h1><p>Se añadirá al chat (menús y búsqueda) en cuanto guardes.</p></header>
  <main>
    <form method="post" action="/panel/crear" enctype="multipart/form-data" class="editor">
      <input type="hidden" name="consulta_original" value="{escape(consulta)}">
      <label>Dispositivo
        <select name="device_id" required>{opts}</select>
      </label>
      <label>Título del problema (lo que verá la tienda)
        <input type="text" name="label" value="{label_val}" placeholder="Ej. La pantalla no enciende" required>
      </label>
      <label>Palabras clave para la búsqueda (separadas por comas)
        <input type="text" name="keywords" value="{kw_val}" placeholder="pantalla, negra, no enciende">
      </label>
      <label>Introducción (opcional)
        <input type="text" name="intro" placeholder="Vamos a revisar…">
      </label>
      <div class="pasos">{pasos_html}</div>
      <label>Nota de escalado (opcional, si tras los pasos no se resuelve)
        <input type="text" name="escalate_note" placeholder="Si sigue igual, avisa a soporte.">
      </label>
      <div class="acciones">
        <a class="btn" href="/panel">Cancelar</a>
        <button class="btn primary" type="submit">Guardar solución</button>
      </div>
    </form>
  </main>
</body></html>""")


@app.post("/panel/crear")
async def crear_solucion(
    device_id: str = Form(...),
    label: str = Form(...),
    keywords: str = Form(""),
    intro: str = Form(""),
    escalate_note: str = Form(""),
    consulta_original: str = Form(""),
    paso_texto_1: str = Form(""), paso_texto_2: str = Form(""), paso_texto_3: str = Form(""),
    paso_texto_4: str = Form(""), paso_texto_5: str = Form(""), paso_texto_6: str = Form(""),
    paso_img_1: UploadFile | None = File(None), paso_img_2: UploadFile | None = File(None),
    paso_img_3: UploadFile | None = File(None), paso_img_4: UploadFile | None = File(None),
    paso_img_5: UploadFile | None = File(None), paso_img_6: UploadFile | None = File(None),
    _auth=Depends(require_panel_auth),
):
    textos = [paso_texto_1, paso_texto_2, paso_texto_3, paso_texto_4, paso_texto_5, paso_texto_6]
    imgs = [paso_img_1, paso_img_2, paso_img_3, paso_img_4, paso_img_5, paso_img_6]

    pasos = []
    for texto, img in zip(textos, imgs):
        t = (texto or "").strip()
        if not t:
            continue
        nombre_img = await guardar_imagen(img)
        pasos.append({"text": t, "imagen": nombre_img})

    if not label.strip() or not pasos:
        return JSONResponse(status_code=400, content={"error": "Faltan el título o al menos un paso."})

    # La pregunta original se añade como palabra clave para que el chat la encuentre.
    kw = keywords.strip()
    if consulta_original.strip() and consulta_original.strip().lower() not in kw.lower():
        kw = (kw + ", " + consulta_original.strip()).strip(", ")

    with db() as conn:
        conn.execute(
            "INSERT INTO soluciones (creada, device_id, label, keywords, intro, escalate_note, pasos_json) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), device_id.strip() or "otros",
             label.strip(), kw, intro.strip(), escalate_note.strip(), json.dumps(pasos, ensure_ascii=False)),
        )
        # Al crear la solución para una pregunta pendiente, la marcamos como atendida.
        if consulta_original.strip():
            conn.execute("INSERT INTO atendidas (consulta_norm, ts) VALUES (%s, %s) ON CONFLICT (consulta_norm) DO NOTHING",
                         (consulta_original.strip().lower(), datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return RedirectResponse(url="/panel", status_code=303)


async def guardar_imagen(img: UploadFile | None) -> str | None:
    if not img or not img.filename:
        return None
    ext = Path(img.filename).suffix.lower()
    if ext not in EXT_IMG:
        return None
    data = await img.read()
    nombre = f"{secrets.token_hex(8)}{ext}"
    mime = img.content_type or MIME_BY_EXT.get(ext, "application/octet-stream")
    with db() as conn:
        conn.execute("INSERT INTO fotos (nombre, mime, data, creada) VALUES (%s, %s, %s, %s)",
                     (nombre, mime, data, datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return nombre


@app.get("/panel/consulta/{cid}", response_class=HTMLResponse)
def ver_consulta(cid: int, _auth=Depends(require_panel_auth)):
    with db() as conn:
        r = conn.execute("SELECT * FROM consultas WHERE id=%s", (cid,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return HTMLResponse(render_consulta(r))


def render_consulta(r) -> str:
    fecha = fmt_fecha(r["ts"])
    etiquetas = {"resuelto": ("ok", "Resuelto"), "escalado": ("warn", "Escalado"),
                 "sin_respuesta": ("bad", "Sin respuesta")}
    c, t = etiquetas.get(r["resultado"], ("", r["resultado"]))

    conv = json.loads(r["conversacion"] or "[]")
    burbujas = ""
    for m in conv:
        lado = "u" if m.get("who") == "usuario" else "b"
        img = ""
        if m.get("imagen"):
            src = m["imagen"]
            if not src.startswith("/"):
                src = "/" + src
            img = f"<img src='{escape(src)}' alt=''>"
        texto = escape(m.get("text", "")).replace("\n", "<br>")
        burbujas += f"<div class='fila {lado}'><div class='burbuja'>{texto}{img}</div></div>"
    if not conv:
        burbujas = "<p class='vacio'>Esta consulta no guardó la conversación (es anterior a esta función).</p>"

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conversación · Panel</title>{PANEL_CSS}
<style>
  .conv {{ max-width: 720px; }}
  .meta {{ background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); padding:14px 16px; margin-bottom:16px; font-size:14px; box-shadow:var(--shadow); }}
  .fila {{ display:flex; margin:8px 0; }}
  .fila.u {{ justify-content:flex-end; }}
  .burbuja {{ max-width:80%; padding:11px 14px; border-radius:var(--radius); font-size:14px; line-height:1.45; white-space:pre-wrap; }}
  .fila.b .burbuja {{ background:var(--bg-card-2); color:var(--text); border:1px solid var(--border); border-bottom-left-radius:6px; }}
  .fila.u .burbuja {{ background:var(--accent-grad); color:#fff; border-bottom-right-radius:6px; }}
  .burbuja img {{ display:block; max-width:200px; margin-top:8px; border-radius:var(--radius-sm); border:1px solid var(--border); background:#fff; }}
</style></head>
<body>
  <header><h1>Conversación</h1><p><a style="color:var(--accent);font-weight:600;text-decoration:none" href="/panel">← Volver al panel</a></p></header>
  <main class="conv">
    <div class="meta">
      <strong>Tienda:</strong> {escape(r['tienda_numero'])}{' · ' + escape(r['tienda_nombre']) if r['tienda_nombre'] else ''}<br>
      <strong>Fecha:</strong> {fecha}<br>
      <strong>Consulta:</strong> {escape(r['consulta'])}<br>
      <strong>Resultado:</strong> <span class="badge {c}">{t}</span>
    </div>
    {burbujas}
  </main>
</body></html>"""


@app.post("/panel/atender")
def atender_pregunta(consulta: str = Form(...), _auth=Depends(require_panel_auth)):
    norm = (consulta or "").strip().lower()
    if norm:
        with db() as conn:
            conn.execute("INSERT INTO atendidas (consulta_norm, ts) VALUES (%s, %s) ON CONFLICT (consulta_norm) DO NOTHING",
                         (norm, datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return RedirectResponse(url="/panel", status_code=303)


@app.get("/panel/export.csv")
def export_csv(resultado: str = "", tienda: str = "", q: str = "", _auth=Depends(require_panel_auth)):
    where, params = _filtro_consultas(resultado, tienda, q)
    with db() as conn:
        filas = conn.execute(
            "SELECT ts, tienda_numero, tienda_nombre, consulta, origen, resultado FROM consultas"
            + where + " ORDER BY id DESC", params).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Fecha", "Tienda nº", "Tienda nombre", "Consulta", "Origen", "Resultado"])
    for r in filas:
        w.writerow([fmt_fecha(r["ts"]), r["tienda_numero"], r["tienda_nombre"], r["consulta"], r["origen"], r["resultado"]])
    contenido = buf.getvalue().encode("utf-8-sig")  # BOM para que Excel muestre bien las tildes
    return Response(content=contenido, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=consultas.csv"})


@app.post("/panel/borrar")
def borrar_solucion(id: int = Form(...), _auth=Depends(require_panel_auth)):
    with db() as conn:
        fila = conn.execute("SELECT pasos_json FROM soluciones WHERE id=%s", (id,)).fetchone()
        if fila:
            for p in json.loads(fila["pasos_json"] or "[]"):
                if p.get("imagen"):
                    conn.execute("DELETE FROM fotos WHERE nombre=%s", (p["imagen"],))
            conn.execute("DELETE FROM soluciones WHERE id=%s", (id,))
    return RedirectResponse(url="/panel", status_code=303)


PANEL_CSS = """<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
  :root {
    --bg-base:#F5F0EB; --bg-card:rgba(255,255,255,.70); --bg-card-2:rgba(255,255,255,.90); --bg-input:rgba(255,255,255,.80);
    --border:rgba(45,42,38,.08); --border-light:rgba(45,42,38,.05);
    --text:#2D2A26; --text-secondary:rgba(45,42,38,.60); --text-muted:rgba(45,42,38,.35);
    --accent:#7947F8; --accent-grad:linear-gradient(135deg,#7947F8,#A855F7); --accent-soft:rgba(121,71,248,.10);
    --green:#5C8A6C; --green-soft:rgba(92,138,108,.12); --amber:#C99555; --amber-soft:rgba(201,149,85,.12);
    --red:#E05252; --red-soft:rgba(224,82,82,.12);
    --radius-sm:8px; --radius:16px; --shadow:0 1px 4px rgba(45,42,38,.06); --shadow-md:0 4px 16px rgba(45,42,38,.08);
    --font:'Poppins',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  }
  * { box-sizing: border-box; }
  body { font-family: var(--font); margin: 0; background: var(--bg-base); color: var(--text); }
  header { background: rgba(245,240,235,.85); -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
           border-bottom: 1px solid var(--border); padding: 16px 32px; }
  header h1 { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -.5px; }
  header h1::before { content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%;
           background: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); margin-right: 10px; vertical-align: middle; }
  header p { margin: 6px 0 0; font-size: 13px; color: var(--text-secondary); }
  main { max-width: 1040px; margin: 0 auto; padding: 24px 32px; }
  .cards { display: flex; gap: 16px; flex-wrap: wrap; }
  .card { flex: 1; min-width: 130px; background: var(--bg-card); border: 1px solid var(--border);
          border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); }
  .card .n { font-size: 28px; font-weight: 800; letter-spacing: -1px; color: var(--accent); }
  .card .l { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
  .card.ok .n { color: var(--green); } .card.warn .n { color: var(--amber); } .card.bad .n { color: var(--red); }
  h2 { font-size: 15px; font-weight: 700; margin: 30px 0 10px; }
  .head-row { display: flex; align-items: center; justify-content: space-between; }
  .hint { font-size: 13px; color: var(--text-secondary); margin: 0 0 12px; }
  table { width: 100%; border-collapse: collapse; background: var(--bg-card-2); border: 1px solid var(--border);
          border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); }
  th, td { text-align: left; padding: 11px 14px; border-bottom: 1px solid var(--border-light); font-size: 13px; vertical-align: middle; }
  th { background: #F0EAE3; font-size: 10px; text-transform: uppercase; letter-spacing: .5px; color: var(--text-muted); font-weight: 600; }
  td.num { text-align: right; font-weight: 700; width: 70px; } td.vacio { color: var(--text-secondary); text-align: center; padding: 22px; }
  tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; }
  .badge.ok { background: var(--green-soft); color: var(--green); } .badge.warn { background: var(--amber-soft); color: var(--amber); } .badge.bad { background: var(--red-soft); color: var(--red); }
  .btn { display: inline-block; border: 1px solid var(--border); background: var(--bg-card-2); color: var(--text); text-decoration: none;
         font-family: inherit; font-size: 13px; font-weight: 600; padding: 8px 14px; border-radius: var(--radius-sm); cursor: pointer;
         transition: border-color .15s, background .15s; }
  .btn:hover { border-color: var(--accent); background: var(--accent-soft); }
  .btn.primary { background: var(--accent-grad); color: #fff; border-color: transparent; border-radius: 999px; padding: 8px 20px; }
  .btn.primary:hover { filter: brightness(1.05); background: var(--accent-grad); }
  .btn.danger { color: var(--red); border-color: rgba(224,82,82,.35); background: var(--red-soft); }
  .btn.ghost { color: var(--text-secondary); background: transparent; }
  .btn.disabled { opacity: .45; pointer-events: none; }
  form { margin: 0; }
  .editor { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; display: flex; flex-direction: column; gap: 14px; max-width: 640px; box-shadow: var(--shadow); }
  .editor > label { display: flex; flex-direction: column; gap: 5px; font-size: 13px; font-weight: 600; }
  .editor input[type=text], .editor select, .editor textarea { border: 1px solid var(--border); background: var(--bg-input); border-radius: var(--radius-sm); padding: 11px 13px; font-size: 14px; font-family: inherit; font-weight: 400; color: var(--text); }
  .editor input[type=text]:focus, .editor select:focus, .editor textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
  .pasos { display: flex; flex-direction: column; gap: 10px; }
  fieldset.paso { border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; }
  fieldset.paso legend { font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; padding: 0 6px; }
  fieldset.paso textarea { width: 100%; box-sizing: border-box; }
  .file { font-size: 12.5px; color: var(--text-secondary); font-weight: 400; }
  .acciones { display: flex; gap: 10px; justify-content: flex-end; }
  .filtros { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 0 0 12px; }
  .filtros select, .filtros input { border: 1px solid var(--border); background: var(--bg-input); border-radius: var(--radius-sm); padding: 9px 12px; font-size: 13px; font-family: inherit; color: var(--text); }
  tr.clicable { cursor: pointer; }
  td.consulta { font-weight: 500; }
  td.consulta .trunc { display: block; max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  td.chev { color: var(--text-muted); font-size: 20px; font-weight: 700; text-align: right; width: 30px; }
  /* Filas alternadas (zebra) */
  table.ultimas tbody tr:nth-child(even) td { background: rgba(45,42,38,.02); }
  /* Hover de fila (gana sobre la zebra) */
  tr.clicable:hover td { background: var(--accent-soft); }
  tr.clicable:hover td.chev { color: var(--accent); }
  /* Cabecera fija al hacer scroll */
  table.ultimas thead th { position: sticky; top: 0; z-index: 1; }
  /* Paginación */
  .paginacion { display: flex; align-items: center; gap: 12px; margin: 14px 0 4px; }
  .pag-info { font-size: 13px; color: var(--text-secondary); }
</style>"""


# Servidor MCP en /mcp (para que Claude consulte el registro y el manual).
# La sub-app sirve en "/", así que /mcp (sin barra) se redirige a /mcp/ conservando el método.
@app.api_route("/mcp", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def _mcp_slash():
    return RedirectResponse(url="/mcp/", status_code=307)


app.mount("/mcp", mcp_app)

# El chatbot estático se sirve desde public/ (así server.py y .env NO quedan expuestos).
app.mount("/", StaticFiles(directory=str(BASE_DIR / "public"), html=True), name="static")


if __name__ == "__main__":
    print(f"\nChatbot guiado en marcha:  http://localhost:{PORT}")
    print(f"Panel de la oficina:        http://localhost:{PORT}/panel\n")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
