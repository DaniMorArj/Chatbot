// Chatbot de soporte guiado — sin IA, sin coste. El conocimiento está en flows.js (window.FLOWS).

const FLOWS = window.FLOWS;
const SOPORTE = FLOWS.soporte;
const IMG_BASE = 'images/manual/';

// ---------- Idioma (ES base · IT · EN), con fallback a español ----------
const I18N = window.I18N || { es: { ui: {} } };
let LANG = (function () {
  try { const s = localStorage.getItem('lang'); if (s === 'es' || s === 'it' || s === 'en') return s; } catch (_) {}
  const n = (navigator.language || 'es').slice(0, 2).toLowerCase();
  return (n === 'it' || n === 'en') ? n : 'es';
})();
// Texto de interfaz por clave (con huecos {x}).
function t(key, vars) {
  const ui = (I18N[LANG] && I18N[LANG].ui) || {};
  let s = ui[key] != null ? ui[key] : (I18N.es.ui[key] != null ? I18N.es.ui[key] : key);
  if (vars) for (const k in vars) s = s.split('{' + k + '}').join(vars[k]);
  return s;
}
// Contenido del manual por clave estable; si no hay traducción, devuelve el español.
function tc(key, fallback) {
  if (LANG === 'es') return fallback;
  const c = (I18N[LANG] && I18N[LANG].c) || {};
  return c[key] != null ? c[key] : fallback;
}
const kDev = (d) => `${d.id}.label`;
const kProb = (d, p) => `${d.id}.${p.id}.label`;
const kIntro = (d, p) => `${d.id}.${p.id}.intro`;
const kStep = (d, p, i) => `${d.id}.${p.id}.s${i}`;
const kEsc = (d, p) => `${d.id}.${p.id}.esc`;

const chatEl = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('input');
const btnSoporte = document.getElementById('btn-soporte');
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const tiendaInfo = document.getElementById('tienda-info');

// Pantalla inicial (identificar tienda)
const setupEl = document.getElementById('setup');
const setupForm = document.getElementById('setup-form');
const setupNumero = document.getElementById('setup-numero');
const setupError = document.getElementById('setup-error');

let TIENDA = { numero: '' };

// Incidencia en curso, para registrar su resultado una sola vez.
let estado = null; // { label, origen, cerrado }

// Transcripción de la incidencia en curso (para verla en el panel).
let conversacion = [];
function anota(who, text, imagen) {
  const m = { who, text };
  if (imagen) m.imagen = imagen;
  conversacion.push(m);
}

iniciarSetup();

// ---------- Pantalla inicial ----------
function iniciarSetup() {
  aplicarTextosEstaticos();
  renderLang();
  const params = new URLSearchParams(location.search);
  const paramTienda = (params.get('tienda') || '').trim();

  // Modo embebido (widget en otra web): si llega la tienda por la URL,
  // entra directo sin mostrar la pantalla de número (la tienda la aporta la app anfitriona).
  if (params.get('embed') === '1' && paramTienda) {
    TIENDA = { numero: paramTienda };
    try { localStorage.setItem('tienda', JSON.stringify(TIENDA)); } catch (_) {}
    setupEl.hidden = true;
    tiendaInfo.textContent = t('store', { n: paramTienda });
    cargarSoluciones().finally(start);
    return;
  }

  // Prerrelleno: lo recordado en el dispositivo, o el ?tienda= de la URL.
  let recordada = null;
  try {
    recordada = JSON.parse(localStorage.getItem('tienda') || 'null');
  } catch (_) {}
  setupNumero.value = (recordada && recordada.numero) || paramTienda || '';

  setupForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const numero = setupNumero.value.trim();
    if (!numero) {
      setupError.hidden = false;
      return;
    }
    TIENDA = { numero };
    try {
      localStorage.setItem('tienda', JSON.stringify(TIENDA));
    } catch (_) {}
    setupEl.hidden = true;
    tiendaInfo.textContent = t('store', { n: numero });
    cargarSoluciones().finally(start);
  });

  setupNumero.focus();
}

// Trae las soluciones añadidas desde el panel y las fusiona en el manual del chat.
async function cargarSoluciones() {
  try {
    const res = await fetch('api/soluciones', { cache: 'no-store' });
    if (!res.ok) return;
    const soluciones = await res.json();
    for (const s of soluciones) {
      let dev = FLOWS.devices.find((d) => d.id === s.device_id);
      if (!dev) {
        dev = { id: s.device_id || 'otros', label: 'Otros', emoji: '❓', keywords: [], problems: [] };
        FLOWS.devices.push(dev);
      }
      dev.problems.push({
        id: 'sol_' + s.id,
        label: s.label,
        keywords: s.keywords || [],
        intro: s.intro || '',
        steps: s.steps || [],
        escalate_note: s.escalate_note || '',
      });
    }
  } catch (_) {
    /* si no hay servidor, el chat sigue con el manual base */
  }
}

// ---------- Chat ----------
function start() {
  addBot(t('greeting'));
  showDevices();
  input.focus();
}

// Bandera SVG (los emojis de bandera no se pintan en Windows, salen como "IT").
function flagSVG(code) {
  if (code === 'it') {
    return '<svg viewBox="0 0 3 2" width="20" height="14" aria-hidden="true">' +
      '<rect width="1" height="2" x="0" fill="#009246"/><rect width="1" height="2" x="1" fill="#fff"/>' +
      '<rect width="1" height="2" x="2" fill="#ce2b37"/></svg>';
  }
  return '';
}

function showDevices() {
  const opciones = FLOWS.devices.map((d) => {
    const lbl = tc(kDev(d), d.label);
    return d.flag
      ? { label: lbl, icon: flagSVG(d.flag), onClick: () => elegirDispositivo(d) }
      : { label: `${d.emoji}  ${lbl}`, onClick: () => elegirDispositivo(d) };
  });
  addChoices(opciones);
}

function elegirDispositivo(device) {
  addUser(tc(kDev(device), device.label));
  if (device.problems.length === 1) {
    elegirProblema(device, device.problems[0], 'menu');
    return;
  }
  addBot(t('whatWrong', { d: tc(kDev(device), device.label) }));
  const opciones = device.problems.map((p) => ({
    label: tc(kProb(device, p), p.label),
    onClick: () => elegirProblema(device, p, 'menu'),
  }));
  opciones.push({ label: t('otherDevice'), ghost: true, onClick: () => { addUser(t('uOtherDevice')); showDevices(); } });
  addChoices(opciones);
}

function elegirProblema(device, problem, origen) {
  addUser(tc(kProb(device, problem), problem.label));
  // Abre una incidencia nueva (el registro se guarda en español para la oficina)
  estado = { label: `${device.label} · ${problem.label}`, origen, cerrado: false };
  conversacion = [];
  anota('usuario', problem.label);
  if (problem.intro) { addBot(tc(kIntro(device, problem), problem.intro)); anota('bot', problem.intro); }
  mostrarPaso(device, problem, 0);
}

function mostrarPaso(device, problem, idx) {
  const total = problem.steps.length;
  const paso = problem.steps[idx];

  const frag = document.createDocumentFragment();
  const badge = document.createElement('span');
  badge.className = 'step-badge';
  badge.textContent = t('step', { n: idx + 1, t: total });
  frag.appendChild(badge);
  frag.appendChild(document.createElement('br'));
  frag.appendChild(document.createTextNode(tc(kStep(device, problem, idx), paso.text)));
  if (paso.image) {
    frag.appendChild(imagen(Object.assign({}, paso.image, {
      caption: tc(kStep(device, problem, idx) + '.cap', paso.image.caption),
    })));
  }
  addBotNode(frag);

  const imgPath = paso.image ? (paso.image.src ? paso.image.src : IMG_BASE + paso.image.file) : null;
  anota('bot', `Paso ${idx + 1}/${total}: ${paso.text}`, imgPath);

  const esUltimo = idx === total - 1;
  addChoices([
    { label: t('resolved'), ok: true, onClick: () => resuelto() },
    {
      label: esUltimo ? t('stillFails') : t('nextStep'),
      onClick: () => {
        const accionES = esUltimo ? 'Sigue sin funcionar' : 'Sigo igual';
        addUser(esUltimo ? t('uStillFails') : t('uStill'));
        anota('usuario', accionES);
        if (esUltimo) escalar(tc(kEsc(device, problem), problem.escalate_note));
        else mostrarPaso(device, problem, idx + 1);
      },
    },
  ]);
}

function resuelto() {
  addUser(t('uResolved'));
  anota('usuario', '¡Resuelto!');
  cerrarComo('resuelto');
  addBot(t('greatResolved'));
  addChoices([{ label: t('otherIssue'), primary: true, onClick: () => { addUser(t('uOtherIssue')); reiniciar(); } }]);
}

function escalar(nota) {
  anota('bot', 'Se muestran los contactos de soporte.' + (nota ? ' ' + nota : ''));
  cerrarComo('escalado');
  if (nota) addBot(nota);
  mostrarEscalado();
  addChoices([{ label: t('startOver'), onClick: () => { addUser(t('uStartOver')); reiniciar(); } }]);
}

function reiniciar() {
  estado = null;
  addBot(t('whichDevice'));
  showDevices();
}

// ---------- Búsqueda por texto (con desambiguación) ----------
form.addEventListener('submit', (e) => {
  e.preventDefault();
  const texto = input.value.trim();
  if (!texto) return;
  input.value = '';
  addUser(texto);
  buscar(texto);
});

function buscar(texto) {
  const q = normalizar(texto);
  let max = 0;
  const candidatos = [];
  for (const device of FLOWS.devices) {
    for (const problem of device.problems) {
      const p = puntuar(q, device, problem);
      if (p > 0 && p === max) candidatos.push({ device, problem });
      else if (p > 0 && p > max) { max = p; candidatos.length = 0; candidatos.push({ device, problem }); }
    }
  }

  if (candidatos.length === 0) {
    conversacion = [];
    anota('usuario', texto);
    anota('bot', 'No lo encontré en el manual.');
    registrar(texto, 'sin_respuesta', 'texto');
    addBot(t('notFound'));
    showDevices();
    return;
  }

  if (candidatos.length === 1) {
    const { device, problem } = candidatos[0];
    addBot(t('seemsLike', { d: tc(kDev(device), device.label) }));
    estado = { label: `${device.label} · ${problem.label}`, origen: 'texto', cerrado: false };
    conversacion = [];
    anota('usuario', texto);
    anota('bot', `Coincidencia: ${device.label} · ${problem.label}`);
    if (problem.intro) { addBot(tc(kIntro(device, problem), problem.intro)); anota('bot', problem.intro); }
    mostrarPaso(device, problem, 0);
    return;
  }

  // Varias coincidencias: si son demasiadas, mejor menú; si no, que elija.
  if (candidatos.length > 4) {
    addBot(t('several'));
    showDevices();
    return;
  }
  addBot(t('whichOne'));
  const opciones = candidatos.map(({ device, problem }) => {
    const dl = tc(kDev(device), device.label);
    const pl = tc(kProb(device, problem), problem.label);
    return device.flag
      ? { label: `${dl} · ${pl}`, icon: flagSVG(device.flag), onClick: () => elegirProblema(device, problem, 'texto') }
      : { label: `${device.emoji}  ${dl} · ${pl}`, onClick: () => elegirProblema(device, problem, 'texto') };
  });
  opciones.push({ label: t('allDevices'), ghost: true, onClick: () => { addUser(t('uAll')); showDevices(); } });
  addChoices(opciones);
}

// El dispositivo pesa mucho más que el síntoma: si el usuario nombra un dispositivo
// ("impresora"), los resultados salen de ese dispositivo, no de otro por coincidir el síntoma.
function puntuar(q, device, problem) {
  const dispositivo = sumarClaves(q, [
    ...(device.keywords || []),
    ...palabrasSignificativas(device.label),
    ...palabrasSignificativas(tc(kDev(device), device.label)),
  ]);
  const sintoma = sumarClaves(q, [
    ...(problem.keywords || []),
    ...palabrasSignificativas(problem.label),
    ...palabrasSignificativas(tc(kProb(device, problem), problem.label)),
  ]);
  return dispositivo * 10 + sintoma;
}

function sumarClaves(q, claves) {
  let p = 0;
  for (const k of claves) {
    const nk = normalizar(k);
    if (nk && q.includes(nk)) p += nk.includes(' ') ? 2 : 1;
  }
  return p;
}

function palabrasSignificativas(texto) {
  return normalizar(texto)
    .split(/[^a-z0-9]+/)
    .filter((w) => w.length >= 4);
}

function normalizar(s) {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, ''); // quita tildes/diacríticos
}

// ---------- Registro de la consulta en el servidor ----------
function cerrarComo(resultado) {
  if (estado && !estado.cerrado) {
    registrar(estado.label, resultado, estado.origen);
    estado.cerrado = true;
  } else if (resultado === 'escalado') {
    registrar('(contacto directo con soporte)', 'escalado', 'menu');
  }
}

function registrar(consulta, resultado, origen) {
  try {
    fetch('api/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        consulta,
        resultado,
        origen,
        tienda_numero: TIENDA.numero,
        conversacion,
      }),
      keepalive: true,
    }).catch(() => {});
  } catch (_) {
    /* sin servidor: se ignora */
  }
}

// ---------- Escalado a soporte ----------
btnSoporte.addEventListener('click', () => {
  addUser(t('uContact'));
  if (!estado || estado.cerrado) conversacion = [];
  anota('usuario', 'Contactar con soporte');
  anota('bot', 'Se muestran los contactos de soporte.');
  cerrarComo('escalado');
  mostrarEscalado();
});

function contactoHTML(c) {
  return `
    <div class="contacto">
      <div class="contacto-nombre">${c.nombre}</div>
      <a href="tel:${c.telefono.replace(/\s/g, '')}">📞 ${c.telefono}</a>
      <a href="mailto:${c.correo}">✉️ ${c.correo}</a>
    </div>`;
}

function mostrarEscalado() {
  if (chatEl.lastElementChild?.classList.contains('escalation')) return;
  const card = document.createElement('div');
  card.className = 'escalation';
  card.innerHTML = `
    <h3>${t('escTitle')}</h3>
    <p><strong>1.</strong> ${t('escFirst')}</p>
    ${contactoHTML(SOPORTE.primario)}
    <p class="contacto-sep"><strong>2.</strong> ${t('escSecond')}</p>
    ${contactoHTML(SOPORTE.secundario)}
  `;
  chatEl.appendChild(card);
  scroll();
}

// ---------- Render helpers ----------
function addUser(text) {
  chatEl.appendChild(bubble('user', document.createTextNode(text)));
  scroll();
}
function addBot(text) {
  chatEl.appendChild(bubble('bot', document.createTextNode(text)));
  scroll();
}
function addBotNode(node) {
  chatEl.appendChild(bubble('bot', node));
  scroll();
}

function bubble(role, content) {
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}`;
  const b = document.createElement('div');
  b.className = 'bubble';
  b.appendChild(content);
  wrap.appendChild(b);
  return wrap;
}

function addChoices(opciones) {
  const wrap = document.createElement('div');
  wrap.className = 'choices';
  for (const op of opciones) {
    const btn = document.createElement('button');
    btn.className = 'choice' + (op.primary ? ' primary' : '') + (op.ok ? ' ok' : '') + (op.ghost ? ' ghost' : '');
    if (op.icon) {
      const ic = document.createElement('span');
      ic.className = 'choice-ic';
      ic.innerHTML = op.icon; // icono estático (SVG); no proviene de entrada de usuario
      btn.appendChild(ic);
      btn.appendChild(document.createTextNode(op.label));
    } else {
      btn.textContent = op.label;
    }
    btn.addEventListener('click', () => {
      wrap.querySelectorAll('.choice').forEach((b) => (b.disabled = true));
      wrap.remove();
      op.onClick();
    });
    wrap.appendChild(btn);
  }
  chatEl.appendChild(wrap);
  scroll();
}

function imagen({ file, src, caption }) {
  const frag = document.createDocumentFragment();
  const img = document.createElement('img');
  img.className = 'manual-img';
  img.src = src ? src : IMG_BASE + file; // 'src' = imagen subida desde el panel; 'file' = imagen del manual
  img.alt = caption || '';
  img.title = 'Pulsa para ampliar';
  img.addEventListener('click', () => abrirLightbox(img.src, img.alt));
  frag.appendChild(img);
  if (caption) {
    const cap = document.createElement('div');
    cap.className = 'img-caption';
    cap.textContent = caption;
    frag.appendChild(cap);
  }
  return frag;
}

function abrirLightbox(src, alt) {
  lightboxImg.src = src;
  lightboxImg.alt = alt;
  lightbox.hidden = false;
}
lightbox.addEventListener('click', () => (lightbox.hidden = true));

function scroll() {
  chatEl.scrollTop = chatEl.scrollHeight;
}

// ---------- Idioma: textos estáticos + selector ----------
function aplicarTextosEstaticos() {
  const h1 = document.querySelector('.header-title h1');
  if (h1) h1.textContent = t('brand');
  if (TIENDA && TIENDA.numero) tiendaInfo.textContent = t('store', { n: TIENDA.numero });
  else tiendaInfo.textContent = t('subtitle');
  if (btnSoporte) btnSoporte.textContent = t('contact');
  if (input) input.placeholder = t('placeholder');
  const disc = document.querySelector('.disclaimer');
  if (disc) disc.textContent = t('disclaimer');
  // Pantalla inicial (identificar tienda)
  const h2 = document.querySelector('.setup-card h2');
  if (h2) h2.textContent = t('setupTitle');
  const sp = document.querySelector('.setup-card > p');
  if (sp) sp.textContent = t('setupDesc');
  const lab = setupNumero ? setupNumero.closest('label') : null;
  if (lab && lab.firstChild && lab.firstChild.nodeType === 3) lab.firstChild.nodeValue = t('setupNum') + ' ';
  const sBtn = document.querySelector('.setup-btn');
  if (sBtn) sBtn.textContent = t('setupEnter');
  if (setupError) setupError.textContent = t('setupErr');
}

function renderLang() {
  const cont = document.getElementById('lang');
  if (!cont) return;
  cont.innerHTML = '';
  ['es', 'it', 'en'].forEach((l) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'lang-btn' + (l === LANG ? ' active' : '');
    b.textContent = l.toUpperCase();
    b.setAttribute('aria-label', l);
    b.addEventListener('click', () => setLang(l));
    cont.appendChild(b);
  });
}

function setLang(l) {
  if (l === LANG) return;
  LANG = l;
  try { localStorage.setItem('lang', l); } catch (_) {}
  aplicarTextosEstaticos();
  renderLang();
  // Si el chat ya está activo (setup oculto), recárgalo en el nuevo idioma.
  if (setupEl && setupEl.hidden) reiniciarChat();
}

function reiniciarChat() {
  estado = null;
  conversacion = [];
  chatEl.innerHTML = '';
  start();
}
