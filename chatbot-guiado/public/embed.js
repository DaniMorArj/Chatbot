/*
 * Widget de inserción del Chatbot de Soporte de Tienda.
 *
 * Uso en cualquier web — una sola línea:
 *   <script src="https://TU-DOMINIO/embed.js" data-tienda="042"></script>
 *
 * Atributos (en la etiqueta <script>):
 *   data-tienda   Número de tienda (recomendado; entra directo sin pedirlo). Obligatorio para saltar el setup.
 *   data-label    Texto del botón flotante. Por defecto "Soporte IT".
 *   data-title    Título de la cabecera del widget. Por defecto "Asistente de soporte".
 *   data-color    Color del botón (CSS). Por defecto "#1c2430".
 *   data-position "right" (por defecto) o "left".
 *
 * El widget abre el chat en un iframe a  <origen>/?tienda=<id>&embed=1 . No tiene dependencias.
 */
(function () {
  "use strict";
  if (window.__chatsoporteWidgetCargado) return;
  window.__chatsoporteWidgetCargado = true;

  var script = document.currentScript || (function () {
    var s = document.getElementsByTagName("script");
    return s[s.length - 1];
  })();

  // Origen desde el que se sirvió este embed.js (así el iframe apunta al sitio correcto).
  var base = window.location.origin;
  try { base = new URL(script.src).origin; } catch (e) {}

  var tienda = (script.getAttribute("data-tienda") || "").trim();
  var label = script.getAttribute("data-label") || "Soporte IT";
  var titulo = script.getAttribute("data-title") || "Asistente de soporte";
  var color = script.getAttribute("data-color") || "linear-gradient(135deg,#7947F8,#A855F7)";
  var lado = (script.getAttribute("data-position") || "right").toLowerCase() === "left" ? "left" : "right";

  var iframeSrc = base + "/?embed=1" + (tienda ? "&tienda=" + encodeURIComponent(tienda) : "");

  var css =
    ".cs-launcher{position:fixed;" + lado + ":20px;bottom:20px;z-index:2147483000;display:inline-flex;" +
    "align-items:center;gap:8px;border:none;border-radius:999px;padding:12px 18px;cursor:pointer;" +
    "font:600 15px/1 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#fff;" +
    "box-shadow:0 6px 20px rgba(0,0,0,.25);transition:transform .15s ease}" +
    ".cs-launcher:hover{transform:translateY(-2px)}" +
    ".cs-panel{position:fixed;" + lado + ":20px;bottom:88px;width:390px;height:640px;" +
    "max-width:calc(100vw - 40px);max-height:calc(100vh - 120px);z-index:2147483000;" +
    "background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.30);overflow:hidden;" +
    "display:none;flex-direction:column}" +
    ".cs-panel.cs-open{display:flex}" +
    ".cs-panel.cs-large{width:min(920px,calc(100vw - 40px));height:calc(100vh - 40px);bottom:20px}" +
    ".cs-head{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;" +
    "background:linear-gradient(135deg,#7947F8,#A855F7);color:#fff;" +
    "font:600 14px/1 'Poppins',system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}" +
    ".cs-actions{display:flex;align-items:center;gap:2px}" +
    ".cs-hbtn{background:none;border:none;color:#fff;cursor:pointer;padding:5px 6px;display:inline-flex;" +
    "align-items:center;line-height:0;border-radius:6px}" +
    ".cs-hbtn:hover{background:rgba(255,255,255,.18)}" +
    ".cs-panel iframe{flex:1;width:100%;border:0}" +
    "@media (max-width:480px){.cs-panel,.cs-panel.cs-large{" + lado + ":0;bottom:0;width:100vw;height:100dvh;" +
    "max-width:100vw;max-height:100dvh;border-radius:0}}";

  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var launcher = document.createElement("button");
  launcher.type = "button";
  launcher.className = "cs-launcher";
  launcher.style.background = color;
  launcher.setAttribute("aria-label", titulo);
  launcher.setAttribute("aria-expanded", "false");
  launcher.innerHTML = "<span aria-hidden='true'>💬</span><span>" + label + "</span>";

  var panel = document.createElement("div");
  panel.className = "cs-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", titulo);

  var head = document.createElement("div");
  head.className = "cs-head";
  var h = document.createElement("span");
  h.textContent = titulo;
  var EXPAND_ICON = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-8 8M3 21l8-8"/></svg>';
  var COLLAPSE_ICON = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 9h-5V4M4 15h5v5M15 9l6-6M9 15l-6 6"/></svg>';

  var expand = document.createElement("button");
  expand.type = "button";
  expand.className = "cs-hbtn";
  expand.setAttribute("aria-label", "Agrandar");
  expand.innerHTML = EXPAND_ICON;
  expand.addEventListener("click", function () {
    var grande = panel.classList.toggle("cs-large");
    expand.innerHTML = grande ? COLLAPSE_ICON : EXPAND_ICON;
    expand.setAttribute("aria-label", grande ? "Reducir" : "Agrandar");
    syncLauncher();
  });

  var close = document.createElement("button");
  close.type = "button";
  close.className = "cs-hbtn cs-close";
  close.setAttribute("aria-label", "Cerrar");
  close.innerHTML = "&times;";
  close.style.fontSize = "20px";
  close.style.lineHeight = "1";

  var actions = document.createElement("div");
  actions.className = "cs-actions";
  actions.appendChild(expand);
  actions.appendChild(close);

  head.appendChild(h);
  head.appendChild(actions);
  panel.appendChild(head);

  var cargado = false;
  // El botón flotante se oculta cuando el chat está abierto y agrandado (si no, se superpone).
  function syncLauncher() {
    launcher.style.display = (panel.classList.contains("cs-open") && panel.classList.contains("cs-large")) ? "none" : "";
  }
  function abrir() {
    if (!cargado) {
      var f = document.createElement("iframe");
      f.src = iframeSrc;
      f.title = titulo;
      panel.appendChild(f);
      cargado = true;
    }
    panel.classList.add("cs-open");
    launcher.setAttribute("aria-expanded", "true");
    syncLauncher();
  }
  function cerrar() {
    panel.classList.remove("cs-open");
    launcher.setAttribute("aria-expanded", "false");
    syncLauncher();
  }
  launcher.addEventListener("click", function () {
    panel.classList.contains("cs-open") ? cerrar() : abrir();
  });
  close.addEventListener("click", cerrar);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && panel.classList.contains("cs-open")) cerrar();
  });

  function montar() {
    document.body.appendChild(panel);
    document.body.appendChild(launcher);
  }
  if (document.body) montar();
  else document.addEventListener("DOMContentLoaded", montar);
})();
