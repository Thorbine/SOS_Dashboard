'use strict';

/* SOS Dashboard: gemeinsames Grundgerüst der Oberfläche.
   Kopfzeile mit Navigation, Hilfsfunktionen, Dialoge und Lader für die Module (modules/<name>/web/).
   In der App (pywebview) kommen Module und Daten über window.pywebview.api (Funktionen mit Modulpräfix,
   z. B. hersteller_laden). Direkt im Browser geöffnet läuft eine Vorschau mit Beispieldaten, die nichts speichert. */

let api = null;          // window.pywebview.api, in der Browser-Vorschau null
const modalCloseHooks = [];  // Module hängen hier an, was beim Schließen eines Dialogs aufzuräumen ist
const MODULES = [];      // hier tragen sich die Module ein: { id, title, mount(root), show?() }
const SETTINGS_SECTIONS = [];  // Abschnitte des Tabs Einstellungen: { id, title, build() }, von den Modulen eingetragen

/* ---------- Hilfsfunktionen ---------- */

function uid() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return 'id-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
}

function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  let value;
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'value') value = v;
    else if (k === 'checked') el.checked = true;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  if (value !== undefined) el.value = value;
  return el;
}

const ICONS = {
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/><path d="M3 3l18 18"/>',
  pencil: '<path d="M4 20h4L19 9l-4-4L4 16v4z"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  up: '<path d="M6 15l6-6 6 6"/>',
  down: '<path d="M6 9l6 6 6-6"/>',
  grip: '<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>',
  star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
  gear: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  ext: '<path d="M14 5h5v5M19 5l-8 8M11 7H6v11h11v-5"/>',
};

function icon(name, filled) {
  const s = h('span', { class: 'ico' + (filled ? ' filled' : '') });
  s.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + ICONS[name] + '</svg>';
  return s;
}

function tool(name, title, onclick, opts = {}) {
  return h('button', {
    class: 'tool' + (opts.cls ? ' ' + opts.cls : ''), type: 'button', title, 'aria-label': title,
    disabled: opts.disabled, onclick, tabindex: opts.tab === false ? '-1' : null,
  }, icon(name, opts.filled));
}

function todayIso() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function fmtDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return d + '.' + m + '.' + y;
}

function clone(o) { return JSON.parse(JSON.stringify(o)); }

let toastTimer;
function toast(text, ms) {
  const t = document.getElementById('toast');
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, ms || 2600);
}

function copyText(text) {
  const done = () => toast('Kopiert: ' + text.split('\n')[0] + (text.includes('\n') ? ' …' : ''));
  const fallback = () => {
    const ta = h('textarea', { style: 'position:fixed;opacity:0' });
    ta.value = text;
    document.body.append(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('Kopieren nicht möglich'); }
    ta.remove();
  };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback);
  else fallback();
}

function copyBtn(text) {
  return tool('copy', 'Kopieren', (e) => { e.preventDefault(); e.stopPropagation(); copyText(text); }, { cls: 'copy' });
}

// Links ohne Schema bekommen https://, erlaubt sind nur http, https und mailto.
function normalizeUrl(raw) {
  let u = (raw || '').trim();
  if (!u) return null;
  if (/^(https?:\/\/|mailto:)/i.test(u)) return u;
  if (u.includes('://') || /^(javascript|data|file|vbscript):/i.test(u)) return null;
  return 'https://' + u;
}

function openUrl(raw) {
  const u = normalizeUrl(raw);
  if (!u) { toast('Dieser Link kann nicht geöffnet werden.'); return; }
  if (api) api.url_oeffnen(u);
  else window.open(u, '_blank', 'noopener');
}

function addressLines(a) {
  return [a.company, a.addition, a.contactName ? 'z. Hd. ' + a.contactName : '', a.street,
    [a.zip, a.city].filter(Boolean).join(' '), a.country].filter(Boolean);
}

/* ---------- Dialoge allgemein ---------- */

function showModal({ title, body, foot, size }) {
  const root = document.getElementById('modal-root');
  root.replaceChildren(h('div', { class: 'overlay', onmousedown: (e) => { if (e.target === e.currentTarget) closeModal(); } },
    h('div', { class: 'modal' + (size ? ' ' + size : ''), role: 'dialog', 'aria-modal': 'true' },
      h('div', { class: 'modal-head' }, h('h3', {}, title), tool('x', 'Schließen', closeModal)),
      h('div', { class: 'modal-body' }, body),
      h('div', { class: 'modal-foot' }, foot))));
  const f = root.querySelector('[data-focus]');
  if (f) f.focus();
}

function closeModal() {
  document.getElementById('modal-root').replaceChildren();
  modalCloseHooks.forEach((f) => f());
}

function confirmDialog(title, text, okLabel, onOk) {
  showModal({
    title, body: h('p', {}, text),
    foot: [h('span', { class: 'spacer' }), h('button', { class: 'btn', onclick: closeModal }, 'Abbrechen'),
      h('button', { class: 'btn primary', 'data-focus': '1', onclick: () => { closeModal(); onOk(); } }, okLabel)],
  });
}

function field(label, control, opts = {}) {
  return h('label', { class: opts.cls }, h('span', { class: 'lab' }, label, opts.required && h('span', { class: 'req' }, ' *')), control);
}

// Ruft eine API-Methode auf und zeigt eine Fehlermeldung, falls sie scheitert.
async function apiCall(promise) {
  let res;
  try { res = await promise; } catch (e) { res = { ok: false, message: String(e) }; }
  if (!res.ok && res.error !== 'cancelled') errorDialog('Das hat nicht funktioniert', res.message || 'Unbekannter Fehler.');
  return res;
}

function errorDialog(title, message, extra) {
  showModal({
    title, size: 'medium', body: h('p', {}, message),
    foot: [h('span', { class: 'spacer' }), extra, h('button', { class: 'btn primary', 'data-focus': '1', onclick: closeModal }, 'Schließen')],
  });
}

/* ---------- Module und Navigation ---------- */

function registerModule(m) { MODULES.push(m); }
function registerSettingsSection(s) { SETTINGS_SECTIONS.push(s); }

// Wechselt in den Tab Einstellungen, auf Wunsch gleich zu einem Abschnitt.
function openSettings(sectionId) {
  if (typeof EN !== 'undefined') EN.target = sectionId || null;
  showModule('einstellungen');
}

// Ohne App (Vorschau im Browser) gibt es kein Python, das die Module nennt. Neue Module hier eintragen.
const DEMO_MODULES = ['hersteller', 'preisschilder', 'formulare', 'einstellungen'].map((id, i) => ({
  id, js: ['../modules/' + id + '/web/' + id + '.js'], css: ['../modules/' + id + '/web/' + id + '.css'],
}));

function loadCss(href) {
  return new Promise((resolve) => {
    const l = document.createElement('link');
    l.rel = 'stylesheet'; l.href = href; l.onload = l.onerror = resolve;
    document.head.append(l);
  });
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src; s.onload = resolve; s.onerror = () => reject(new Error('Datei fehlt: ' + src));
    document.body.append(s);
  });
}

let activeModule = null;

function showModule(id) {
  activeModule = id;
  document.querySelectorAll('#nav button[data-m]').forEach((b) => b.classList.toggle('active', b.dataset.m === id));
  document.querySelectorAll('.module-root').forEach((el) => { el.hidden = el.dataset.m !== id; });
  const m = MODULES.find((x) => x.id === id);
  if (m && m.show) m.show();
}

async function boot() {
  const isApp = new URLSearchParams(location.search).has('app');
  if (isApp) {
    if (!(window.pywebview && window.pywebview.api)) await new Promise((r) => window.addEventListener('pywebviewready', r, { once: true }));
    api = window.pywebview.api;
  }
  const res = api ? await api.grundgeruest_module() : { ok: true, modules: DEMO_MODULES };
  const list = res.ok ? res.modules : DEMO_MODULES;
  const stage = document.getElementById('modules');
  for (const mod of list) {
    for (const css of mod.css || []) await loadCss(css);
    for (const js of mod.js || []) {
      try { await loadScript(js); } catch (e) { toast(String(e.message || e), 6000); }
    }
  }
  const nav = document.getElementById('nav');
  for (const mod of list) {
    const m = MODULES.find((x) => x.id === mod.id);
    if (!m) continue;
    const root = h('div', { class: 'module-root', 'data-m': m.id, hidden: true });
    stage.append(root);
    nav.append(h('button', { 'data-m': m.id, onclick: () => showModule(m.id) }, m.title));
    await m.mount(root);
  }
  if (MODULES.length) showModule(MODULES[0].id);
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && document.getElementById('modal-root').firstChild) { closeModal(); e.preventDefault(); }
});

boot();
