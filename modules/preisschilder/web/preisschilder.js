'use strict';

/* Modul Preisschilder: Reiter je Schildtyp, Liste mit Blatt-Zähler, Formular, Logo-Kacheln, Vorschau, Drucken.
   Daten und PDF kommen aus Python (api.preisschilder_*). Ohne App (Browser-Vorschau) ersetzt DEMO die Python-Seite.
   Hilfsfunktionen und Dialoge kommen aus web/shell.js. */

const PS_TYPES = {
  helme: { title: 'Helme' },
  baelle: { title: 'Tennisbälle' },
  schlaeger: { title: 'Schläger' },
  ski: { title: 'Ski' },
  snowboard: { title: 'Snowboard' },
};
const PS_SKI_FIELDS = [['kategorie', 'Kategorie (z. B. Allmountain)', 2], ['modell', 'Modell', 2], ['zusatz1', 'Zusatz 1 (z. B. incl. Bindung)'],
  ['zusatz2', 'Zusatz 2 (z. B. incl. Montage)'], ['text1', 'Preis 1: Text (z. B. Setpreis bei uns)', 2], ['statt1', 'Preis 1: alter Preis (€)'],
  ['preis1', 'Preis 1 (€)'], ['text2', 'Preis 2: Text (optional)', 2], ['statt2', 'Preis 2: alter Preis (€)'], ['preis2', 'Preis 2 (€, optional)']];
const PS_FIELDS = {
  helme: [['modell', 'Modell', 2], ['groesse1', 'Größe', 1, 'sizes'], ['mass1', 'Maße (z. B. 51–55 cm)'], ['preis', 'Preis (€)'], ['statt', 'Statt-Preis (€, optional)']],
  baelle: [['typ', 'Bezeichnung (z. B. DTB-Spielball)', 2], ['name', 'Marke / Ball (z. B. Fort Tournament)', 2], ['inhalt', 'Inhalt (z. B. 4er Dose)'], ['preis', 'Preis (€)'], ['einzel', 'Preis pro Ball (€, optional)']],
  schlaeger: [['name', 'Modell (z. B. Blade 98 16x19 V10)', 2], ['kopfIn', 'Kopf (in²)'], ['kopfCm', 'Kopf (cm²)'], ['gewicht', 'Gewicht (g)'], ['balance', 'Balance (mm)'],
    ['besaitung', 'Besaitung (z. B. 16/19)', 2], ['preis', 'Unser Preis (€)'], ['uvp', 'UVP (€, optional)']],
  ski: PS_SKI_FIELDS,
  snowboard: PS_SKI_FIELDS,
};
const PS_LIST_COLS = {
  helme: [['logo', 'Logo'], ['modell', 'Modell'], ['groesse1', 'Größe'], ['mass1', 'Maße'], ['preis', 'Preis']],
  baelle: [['name', 'Name'], ['inhalt', 'Inhalt'], ['preis', 'Preis']],
  schlaeger: [['marke', 'Marke'], ['name', 'Name'], ['preis', 'Preis']],
  ski: [['logo', 'Logo'], ['modell', 'Modell'], ['preis1', 'Preis 1']],
  snowboard: [['logo', 'Logo'], ['modell', 'Modell'], ['preis1', 'Preis 1']],
};
const PS_COPY_CLEAR = { helme: ['groesse1', 'mass1'] };  // Kopie = gleicher Helm in anderer Größe
const PS_IN2_CM2 = { 85: 548, 90: 581, 93: 600, 95: 613, 97: 626, 98: 632, 99: 639, 100: 645, 101: 652, 102: 658, 103: 665, 104: 671, 105: 677, 107: 690, 108: 697, 110: 710, 115: 742, 116: 748 };

const PS = {
  root: null, tab: 'helme', cfg: null, meta: { groessen: [], farben: [], marken_standard: {} },
  lists: {},        // typ -> { items, loaded, sel, sort }
  forms: {},        // typ -> aktuelle Formularwerte
  logos: {},        // typ -> [{ name, bild, roh }]
  info: {},         // typ -> { breite, hoehe, pro_blatt }
  preview: { seite: 0, seiten: 1, bild: '', text: '' },
  pages: [], clip: [], search: '', searchOpen: false,
  saveTimers: {}, dirty: new Set(), previewTimer: null, edit: -1,
};
PS.ready = new Promise((resolve) => { PS.resolveReady = resolve; });

/* ---------- Schnittstelle: App oder Demo ---------- */

const DEMO = {
  items: {
    helme: [{ logo: 'Helme/Alpina.png', modell: 'Gran Tour', groesse1: 'M-L', mass1: '55-59 cm', preis: '89', statt: '119' }, { logo: 'Helme/POC.png', modell: 'Obex Pure', groesse1: 'L-XL', mass1: '59-63 cm', preis: '229', statt: '' }],
    baelle: [{ typ: 'DTB-Spielball', name: 'Fort Tournament', inhalt: '4er Dose', preis: '8,95', einzel: '2,24' }],
    schlaeger: [
      { marke: 'Wilson', farbe: '#c00000', name: 'Blade 98 16x19 V10', kopfIn: '98', kopfCm: '632', gewicht: '305', besaitung: '16/19', balance: '320', preis: '289,95', uvp: '299,00' },
      { marke: 'HEAD', farbe: '#000000', name: 'Speed MP 2024', kopfIn: '100', kopfCm: '645', gewicht: '300', besaitung: '16/19', balance: '', preis: '259,95', uvp: '' }],
    ski: [{ logo: 'Ski/Atomic.png', kategorie: 'Allmountain', modell: 'Maverick 86 C', zusatz1: 'incl. Bindung', zusatz2: '', text1: 'Setpreis', statt1: '599', preis1: '449', text2: '', statt2: '', preis2: '' }],
    snowboard: [],
  },
  logos: { helme: ['Helme/Alpina.png', 'Helme/Atomic.png', 'Helme/POC.png', 'Helme/Uvex.png'], ski: ['Ski/Atomic.png'], snowboard: [], baelle: [], schlaeger: ['Schläger/wilson.png'] },
  async call(name, ...args) {
    switch (name) {
      case 'start': return { ok: true, einstellungen: { rand: 10, abstand: 0, helme: { breite: 124, hoehe: 60 }, baelle: { breite: 100, hoehe: 15 }, schlaeger: { breite: 91.8, hoehe: 68.3 }, ski: { breite: 70, hoehe: 90 }, snowboard: { breite: 70, hoehe: 90 }, marken: { Wilson: { farbe: '#c00000' }, HEAD: { farbe: '#000000' }, Babolat: { farbe: '#1a5fa8' }, Yonex: { farbe: '#003087' }, Tecnifibre: { farbe: '#1a2b6b' } } }, farben: ['#c00000', '#000000', '#1a5fa8', '#003087', '#1a2b6b', '#2e7d32', '#e65100', '#6a1b9a', '#555555', '#333333'], groessen: ['XS-S', 'S-M', 'M-L', 'L-XL', 'XL-XXL'] };
      case 'liste_laden': return { ok: true, items: JSON.parse(JSON.stringify(DEMO.items[args[0]] || [])), revision: 1 };
      case 'liste_speichern': return { ok: true, revision: 2 };
      case 'logos': return { ok: true, logos: (DEMO.logos[args[0]] || []).map((name) => ({ name, bild: '', roh: '' })) };
      case 'blatt_info': return { ok: true, breite: 90, hoehe: 60, pro_blatt: args[0] === 'schlaeger' ? 6 : 6 };
      case 'vorschau': return args[1].length ? { ok: true, bild: 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="540" height="764"><rect width="540" height="764" fill="white"/><text x="270" y="380" text-anchor="middle" font-family="Arial" font-size="18" fill="#888">Vorschau gibt es nur in der App (' + args[1].length + ' Schilder)</text></svg>'), seiten: 1, seite: 0 } : { ok: true, leer: true };
      case 'seiten_laden': return { ok: true, items: [{ name: 'Frühjahr Schläger', date: '12.11.2026', cards: [] }], revision: 1 };
      default: return { ok: false, message: 'Das geht nur in der App.' };
    }
  },
};

function psCall(name, ...args) {
  return api ? api['preisschilder_' + name](...args) : DEMO.call(name, ...args);
}

function psStatus(text, isError) {
  const el = document.getElementById('save-status');
  if (!el) return;
  el.textContent = text;
  el.classList.toggle('error', !!isError);
}

/* ---------- Hilfen ---------- */

const psList = (typ = PS.tab) => PS.lists[typ] || (PS.lists[typ] = { items: [], loaded: false, sel: -1, sort: null });
const psForm = (typ = PS.tab) => PS.forms[typ] || (PS.forms[typ] = { logo: '' });
const psIsRacket = (typ = PS.tab) => typ === 'schlaeger';
const psEmptyForm = (typ) => { PS.forms[typ] = psIsRacket(typ) ? { marke: Object.keys(PS.cfg.marken)[0] || '', farbe: '' } : { logo: '' }; };

function psEur(v) {
  const raw = String(v || '').replace('€', '').replace('EUR', '').trim().replace(',', '.');
  const n = parseFloat(raw);
  return isNaN(n) ? String(v || '').trim() : n.toFixed(2).replace('.', ',') + ' €';
}

function psCm2(inch) {
  const v = String(inch || '').trim();
  if (PS_IN2_CM2[v]) return String(PS_IN2_CM2[v]);
  const n = parseFloat(v.replace(',', '.'));
  return v && !isNaN(n) ? String(Math.round(n * 6.4516)) : '';
}

function psPrice(item) {
  const raw = String(item.preis || item.preis1 || '').replace('€', '').replace(/\./g, '').replace(',', '.').trim();
  const n = parseFloat(raw);
  return isNaN(n) ? [1, 0, ''] : [0, n, ''];
}

function psSheetItems(typ) {
  const l = psList(typ);
  if (psIsRacket(typ)) return l.items;  // bei den Schlägern ist die Liste die Seite
  const items = [];
  l.items.forEach((it) => { for (let i = 0; i < (it._blatt || 0); i++) items.push(it); });
  if (!l.items.length) {
    const f = psForm(typ);
    if (Object.entries(f).some(([k, v]) => k !== 'logo' && v)) items.push({ ...f });
  }
  return items;
}

/* ---------- Laden und Speichern ---------- */

async function psEnsure(typ) {
  const l = psList(typ);
  if (l.loaded) return;
  const res = await psCall('liste_laden', typ);
  if (!res.ok) { errorDialog('Liste konnte nicht geladen werden', res.message || 'Unbekannter Fehler.'); return; }
  l.items = res.items.map((i) => ({ ...i, _blatt: 0 }));
  l.loaded = true;
  const logos = await psCall('logos', typ);
  PS.logos[typ] = logos.ok ? logos.logos : [];
  const info = await psCall('blatt_info', typ);
  PS.info[typ] = info.ok ? info : { pro_blatt: 0 };
  if (!PS.forms[typ]) psEmptyForm(typ);
}

function psChanged(typ = PS.tab) {
  PS.dirty.add(typ);
  psStatus('Änderungen …');
  clearTimeout(PS.saveTimers[typ]);
  PS.saveTimers[typ] = setTimeout(() => psSaveNow(typ), 500);
}

async function psSaveNow(typ) {
  clearTimeout(PS.saveTimers[typ]);
  if (!PS.dirty.has(typ)) return;
  PS.dirty.delete(typ);
  const res = await psCall('liste_speichern', typ, psList(typ).items);
  if (res.ok) { psStatus('Gespeichert'); return; }
  if (res.error === 'conflict') { psConflict(typ); return; }
  psStatus('Speichern fehlgeschlagen', true);
  errorDialog('Speichern fehlgeschlagen', res.message || 'Unbekannter Fehler.');
}

async function psSaveAll() { for (const typ of [...PS.dirty]) await psSaveNow(typ); }

function psConflict(typ) {
  showModal({
    title: 'Daten wurden woanders geändert', size: 'medium',
    body: h('p', {}, 'Die Liste „' + PS_TYPES[typ].title + '“ wurde auf einem anderen Rechner geändert. Neu laden (eigene Änderungen gehen verloren) oder meine Version als Kopie speichern?'),
    foot: [h('span', { class: 'spacer' }),
      h('button', { class: 'btn', onclick: async () => { closeModal(); psList(typ).loaded = false; await psEnsure(typ); psRender(); } }, 'Neu laden'),
      h('button', { class: 'btn primary', onclick: async () => {
        const res = await apiCall(psCall('liste_kopie_speichern', typ, psList(typ).items));
        closeModal();
        if (res.ok) { psList(typ).loaded = false; await psEnsure(typ); psRender(); toast('Kopie gespeichert: ' + res.file, 5000); }
      } }, 'Meine Version als Kopie speichern')],
  });
}

/* ---------- Vorschau ---------- */

function psPreviewSoon() {
  clearTimeout(PS.previewTimer);
  PS.previewTimer = setTimeout(psPreview, 250);
}

async function psPreview() {
  const typ = PS.tab;
  if (psIsRacket(typ)) return;  // die Karten stehen direkt rechts
  const items = psSheetItems(typ);
  const box = document.getElementById('ps-preview-box');
  if (!box) return;
  if (!items.length) {
    PS.preview = { seite: 0, seiten: 1, bild: '', text: psList(typ).items.length ? 'Das Blatt ist leer. In der Liste auf „+“ klicken, um Schilder aufs Blatt zu legen.' : 'Noch keine Schilder. Felder ausfüllen, dann erscheint hier die Vorschau.' };
  } else {
    const res = await psCall('vorschau', typ, items, PS.preview.seite, 560);
    if (typ !== PS.tab) return;
    PS.preview = res.ok && res.bild ? { seite: res.seite, seiten: res.seiten, bild: res.bild, text: '' } : { seite: 0, seiten: 1, bild: '', text: res.message || '' };
  }
  psPaintPreview();
}

function psPaintPreview() {
  const box = document.getElementById('ps-preview-box');
  if (!box) return;
  const p = PS.preview;
  box.replaceChildren(p.bild ? h('img', { class: 'ps-sheet-img', src: p.bild, alt: 'Vorschau' }) : h('p', { class: 'ps-empty' }, p.text));
  const nav = document.getElementById('ps-page-nav');
  if (nav) nav.textContent = p.bild ? 'Blatt ' + (p.seite + 1) + ' von ' + p.seiten : '';
}

function psPage(d) {
  PS.preview.seite = Math.max(0, Math.min(PS.preview.seiten - 1, PS.preview.seite + d));
  psPreview();
}

async function psPrint() {
  const items = psSheetItems(PS.tab);
  if (!items.length) { toast(psList().items.length ? 'Das Blatt ist leer: in der Liste auf „+“ klicken.' : 'Die Liste ist leer.'); return; }
  const res = await apiCall(psCall('drucken', PS.tab, items));
  if (res.ok && !api) toast('In der Vorschau wird kein PDF erzeugt.');
}

/* ---------- Liste ---------- */

function psCell(it, key) {
  const v = it[key] || '';
  if (key === 'logo') return v.split('/').pop().replace(/\.[^.]+$/, '');
  return /preis|statt|uvp/i.test(key) ? psEur(v) : v;
}

function psBlatt(i, d) {
  const l = psList();
  l.items[i]._blatt = Math.max(0, (l.items[i]._blatt || 0) + d);
  psRender(true);
  psPreviewSoon();
}

function psMove(d) {
  const l = psList(), i = l.sel;
  if (i < 0 || i + d < 0 || i + d >= l.items.length) return;
  [l.items[i], l.items[i + d]] = [l.items[i + d], l.items[i]];
  l.sel = i + d;
  psChanged(); psRender(true); psPreviewSoon();
}

function psSort(key) {
  const l = psList();
  const k = key === 'logo' && psIsRacket() ? 'marke' : key;
  l.items.sort((a, b) => {
    if (k === 'preis') { const x = psPrice(a), y = psPrice(b); return x[0] - y[0] || x[1] - y[1]; }
    return String(a[k] || '').toLowerCase().localeCompare(String(b[k] || '').toLowerCase(), 'de');
  });
  l.sel = -1;
  psChanged(); psRender(true); psPreviewSoon();
}

function psListBox(typ) {
  const l = psList(typ);
  const racket = psIsRacket(typ);
  const cols = PS_LIST_COLS[typ];
  const sortBtn = h('span', { class: 'menu-wrap' }, h('button', { class: 'mini-btn', onclick: (e) => { e.stopPropagation(); psSortMenu(e.currentTarget); } }, 'Sortieren ▾'));
  return h('div', { class: 'card-box' },
    h('h3', {}, (racket ? 'Seite' : 'Liste') + ' (' + l.items.length + ')', h('span', { class: 'spacer' }),
      racket ? null : h('button', { class: 'mini-btn', onclick: () => { l.items.forEach((i) => { i._blatt = 0; }); psRender(true); psPreviewSoon(); } }, 'Blatt leeren'),
      h('button', { class: 'mini-btn', title: 'nach oben', onclick: () => psMove(-1) }, '▲'),
      h('button', { class: 'mini-btn', title: 'nach unten', onclick: () => psMove(1) }, '▼'), sortBtn),
    l.items.length ? h('div', { class: 'ps-list-scroll' }, h('table', { class: 'ptable' },
      h('thead', {}, h('tr', {}, racket ? null : h('th', {}, 'Blatt'), cols.map(([, label]) => h('th', {}, label)), racket ? h('th', {}, '') : null)),
      h('tbody', {}, l.items.map((it, i) => {
        const n = it._blatt || 0;
        return h('tr', { class: (i === l.sel ? 'sel ' : '') + (n ? 'on' : ''), onclick: () => psSelect(i) },
          racket ? null : h('td', {}, h('span', { class: 'cnt' },
            h('button', { title: 'Ein Schild weniger aufs Blatt', onclick: (e) => { e.stopPropagation(); psBlatt(i, -1); } }, '−'), h('b', {}, n || ''),
            h('button', { title: 'Ein Schild aufs Blatt', onclick: (e) => { e.stopPropagation(); psBlatt(i, 1); } }, '+'))),
          cols.map(([key]) => h('td', {}, psCell(it, key))),
          racket ? h('td', {}, h('button', { class: 'mini-btn', title: 'Löschen', onclick: (e) => { e.stopPropagation(); psDelete(i); } }, '✕')) : null);
      })))) : h('p', { class: 'ps-empty small' }, 'Noch keine Schilder in dieser Liste.'));
}

function psSortMenu(anchor) {
  document.getElementById('ps-sort-menu')?.remove();
  const racket = psIsRacket();
  const entries = racket ? [['nach Marke', 'marke'], ['nach Modell', 'name'], ['nach Preis', 'preis']] : [['nach Logo / Marke', 'logo'], ['nach Modell', PS.tab === 'baelle' ? 'name' : 'modell'], ['nach Preis', 'preis']];
  const menu = h('div', { id: 'ps-sort-menu', class: 'menu ctx' }, entries.map(([label, key]) => h('button', { onclick: () => { menu.remove(); psSort(key); } }, label)));
  const r = anchor.getBoundingClientRect();
  menu.style.left = Math.max(8, r.right - 150) + 'px';
  menu.style.top = r.bottom + 4 + 'px';
  document.body.append(menu);
  setTimeout(() => document.addEventListener('click', () => menu.remove(), { once: true }), 0);
}

function psSelect(i) {
  const l = psList();
  l.sel = i;
  PS.edit = psIsRacket() ? i : -1;
  PS.forms[PS.tab] = { ...l.items[i] };
  delete PS.forms[PS.tab]._blatt;
  psRender(true);
  psPreviewSoon();
}

/* ---------- Formular ---------- */

function psField(key, label, span, kind) {
  const f = psForm();
  const attrs = { value: f[key] || '', oninput: (e) => psFormInput(key, e.target.value), onkeydown: (e) => { if (e.key === 'Enter') { e.preventDefault(); psAdd(); } } };
  if (kind === 'sizes') attrs.list = 'ps-sizes';
  const input = h('input', attrs);
  if (key === 'kopfIn') input.setAttribute('inputmode', 'decimal');
  return h('label', { class: span === 2 ? 'span2' : '' }, label, input);
}

function psFormInput(key, value) {
  const f = psForm();
  f[key] = value;
  if (key === 'kopfIn') {
    f.kopfCm = psCm2(value);
    const cm = document.querySelector('#ps-form input[data-key=kopfCm]');
    if (cm) cm.value = f.kopfCm;
  }
  if (!psList().items.length || psIsRacket()) psPreviewSoon();
  if (psIsRacket()) psPaintRackets();
}

function psFormBox(typ) {
  const f = psForm(typ);
  const racket = psIsRacket(typ);
  const editing = racket && PS.edit >= 0;
  const fields = PS_FIELDS[typ].map(([key, label, span, kind]) => {
    const node = psField(key, label, span, kind);
    node.querySelector('input').dataset.key = key;
    return node;
  });
  const brandRow = racket ? h('div', { class: 'form-grid', style: 'margin-bottom:8px' },
    h('label', {}, 'Marke', h('select', { onchange: (e) => { f.marke = e.target.value; f.farbe = (PS.cfg.marken[f.marke] || {}).farbe || ''; psRender(true); psPaintRackets(); } },
      Object.keys(PS.cfg.marken).map((b) => h('option', { value: b, selected: b === f.marke }, b)))),
    h('label', {}, 'Farbe', h('div', { class: 'swatches' }, PS.meta.farben.map((c) => h('span', { class: 'swatch' + (c === (f.farbe || (PS.cfg.marken[f.marke] || {}).farbe) ? ' sel' : ''), style: 'background:' + c, title: c, onclick: () => { f.farbe = c; psRender(true); psPaintRackets(); } })),
      h('input', { type: 'color', value: f.farbe || (PS.cfg.marken[f.marke] || {}).farbe || '#555555', style: 'width:28px;height:24px;padding:0;border:0', oninput: (e) => { f.farbe = e.target.value; psPaintRackets(); } })))) : null;
  return h('div', { class: 'card-box', id: 'ps-form' },
    h('h3', {}, editing ? 'Bearbeite: ' + (f.name || '') : psList(typ).sel >= 0 ? 'Schild bearbeiten' : 'Neues Schild',
      editing ? h('span', { class: 'spacer' }) : null, editing ? h('button', { class: 'mini-btn', onclick: psCancelEdit }, 'Abbrechen ✕') : null),
    brandRow, h('div', { class: 'form-grid' }, fields),
    typ === 'helme' ? h('datalist', { id: 'ps-sizes' }, PS.meta.groessen.map((g) => h('option', { value: g }))) : null,
    h('div', { class: 'btn-row' },
      h('button', { class: 'btn primary', onclick: psAdd }, racket && !editing ? '+ Hinzufügen (Enter)' : '+ Hinzufügen'),
      racket ? (editing ? h('button', { class: 'btn', onclick: psChange }, 'Speichern') : null) : h('button', { class: 'btn', onclick: psChange }, 'Ändern'),
      h('button', { class: 'btn', onclick: psCopy }, 'Kopieren'),
      racket ? null : h('button', { class: 'btn', onclick: () => psDelete(psList().sel) }, 'Löschen'),
      h('button', { class: 'btn', onclick: () => { psList().sel = -1; PS.edit = -1; psEmptyForm(PS.tab); psRender(true); psPreviewSoon(); } }, 'Leeren'),
      h('button', { class: 'btn', onclick: psClearAll }, 'Alle löschen')));
}

function psFormItem() {
  const f = { ...psForm() };
  Object.keys(f).forEach((k) => { if (typeof f[k] === 'string') f[k] = f[k].trim(); });
  if (psIsRacket()) f.farbe = f.farbe || (PS.cfg.marken[f.marke] || {}).farbe || '#555555';
  return f;
}

function psAdd() {
  const item = psFormItem();
  if (!Object.entries(item).some(([k, v]) => !['logo', 'marke', 'farbe'].includes(k) && v)) { toast('Bitte mindestens ein Feld ausfüllen.'); return; }
  const l = psList();
  l.items.push({ ...item, _blatt: 0 });
  if (psIsRacket()) { PS.edit = -1; const brand = item.marke; psEmptyForm(PS.tab); psForm().marke = brand; psForm().farbe = ''; }
  psChanged(); psRender(); psPreviewSoon();
}

function psChange() {
  const l = psList();
  if (l.sel < 0) { toast('Bitte erst ein Schild in der Liste auswählen.'); return; }
  const item = psFormItem();
  l.items[l.sel] = { ...item, _blatt: l.items[l.sel]._blatt || 0 };
  PS.edit = -1;
  psChanged(); psRender(); psPreviewSoon();
}

function psCancelEdit() { PS.edit = -1; psList().sel = -1; psEmptyForm(PS.tab); psRender(); }

function psCopy() {
  const l = psList();
  if (l.sel < 0) { toast('Bitte erst ein Schild in der Liste auswählen.'); return; }
  const copy = { ...l.items[l.sel], _blatt: 0 };
  (PS_COPY_CLEAR[PS.tab] || []).forEach((k) => { copy[k] = ''; });
  l.items.splice(l.sel + 1, 0, copy);
  l.sel += 1;
  psSelect(l.sel);
  psChanged(); psRender(); psPreviewSoon();
}

function psDelete(i) {
  const l = psList();
  if (i < 0 || i >= l.items.length) { toast('Bitte erst ein Schild in der Liste auswählen.'); return; }
  l.items.splice(i, 1);
  l.sel = -1; PS.edit = -1;
  psChanged(); psRender(); psPreviewSoon();
}

function psClearAll() {
  const l = psList();
  if (!l.items.length) return;
  confirmDialog('Liste leeren', 'Alle Schilder dieser Liste (' + PS_TYPES[PS.tab].title + ') löschen?', 'Alle löschen', () => {
    l.items = []; l.sel = -1; PS.edit = -1;
    psChanged(); psRender(); psPreviewSoon();
  });
}

/* ---------- Logos ---------- */

function psLogoBox(typ) {
  if (psIsRacket(typ)) return null;
  const f = psForm(typ);
  const logos = PS.logos[typ] || [];
  const tiles = [h('div', { class: 'tile none' + (!f.logo ? ' sel' : ''), onclick: () => { f.logo = ''; psRender(true); psPreviewSoon(); } }, 'kein Logo')]
    .concat(logos.map((l) => h('div', { class: 'tile' + (l.name === f.logo ? ' sel' : ''), title: l.name, onclick: () => { f.logo = l.name; psRender(true); psPreviewSoon(); } },
      l.bild ? h('img', { src: l.bild, alt: l.name }) : l.name.split('/').pop())));
  return h('div', { class: 'card-box' },
    h('h3', {}, 'Logo ' + (f.logo ? '· ' + f.logo : ''), h('span', { class: 'spacer' }),
      h('button', { class: 'mini-btn', onclick: () => psCall('logo_ordner_oeffnen', typ).then((r) => { if (!r.ok) errorDialog('Ordner', r.message || 'Der Ordner konnte nicht geöffnet werden.'); else if (!api) toast('Öffnet den Logo-Ordner'); }) }, 'Ordner öffnen'),
      h('button', { class: 'mini-btn', onclick: async () => { const r = await psCall('logos', typ); PS.logos[typ] = r.ok ? r.logos : []; psRender(true); } }, 'Neu laden')),
    h('div', { class: 'tiles' }, tiles),
    logos.length ? null : h('p', { class: 'ps-empty small' }, 'Keine Logos. PNG oder JPG in den Logo-Ordner legen (Ordner öffnen), dann „Neu laden“.'));
}

/* ---------- Helme ---------- */

async function psHelmeCsv() {
  await psSaveAll();
  const res = await apiCall(psCall('helme_csv_importieren'));
  if (!res.ok) return;
  psList('helme').items = res.items.map((i) => ({ ...i, _blatt: 0 }));
  psRender(); psPreviewSoon();
  showModal({ title: 'Helme importiert', size: 'medium', body: h('div', { class: 'stack' },
    h('p', {}, res.neu + ' neue Helme importiert, ' + res.schon_da + ' waren schon in der Liste. Die neuen haben noch keine Größe und sind nicht auf dem Blatt.'),
    res.ohne_logo.length ? h('p', {}, 'Ohne Logo (keine passende Datei im Ordner): ' + res.ohne_logo.join(', ')) : null),
  foot: [h('span', { class: 'spacer' }), h('button', { class: 'btn primary', 'data-focus': '1', onclick: closeModal }, 'Schließen')] });
}

async function psAllSizes() {
  await psSaveAll();
  const res = await apiCall(psCall('helme_alle_groessen'));
  if (!res.ok) return;
  psList('helme').items = res.items.map((i) => ({ ...i, _blatt: 0 }));
  psRender(); psPreviewSoon();
  toast(res.neu ? res.neu + ' Schilder angelegt. Jetzt nur noch die Maße ergänzen.' : 'Alle Modelle haben schon alle Größen.', 4000);
}

/* ---------- Schläger: Karten, Seiten, Zwischenablage, Suche ---------- */

function psRacketLogo(marke) {
  const name = 'Schläger/' + String(marke || '').trim().toLowerCase().replace(/ /g, '') + '.png';
  const hit = (PS.logos.schlaeger || []).find((l) => l.name.normalize('NFC') === name.normalize('NFC'));
  return hit && hit.roh ? hit.roh : '';
}

function psRacketCard(it) {
  const dash = '—';
  const kopf = [it.kopfIn ? it.kopfIn + ' in²' : '', it.kopfCm ? it.kopfCm + ' cm²' : ''].filter(Boolean).join(' / ') || dash;
  const color = it.farbe || (PS.cfg.marken[it.marke] || {}).farbe || '#555555';
  const logo = psRacketLogo(it.marke);
  return h('div', { class: 'rk' },
    h('div', { class: 'rk-head', style: 'background:' + color }, logo ? h('img', { src: logo, alt: it.marke || '' }) : h('div', { class: 'wm' }, (it.marke || '').toUpperCase())),
    h('div', { class: 'rk-body' },
      h('div', { class: 'rk-name' }, it.name || dash),
      h('div', { class: 'rk-grid' },
        h('div', {}, h('span', {}, 'Kopf'), h('b', {}, kopf)), h('div', {}, h('span', {}, 'Gewicht'), h('b', {}, it.gewicht ? it.gewicht + ' g' : dash)),
        h('div', {}, h('span', {}, 'Besaitung'), h('b', {}, it.besaitung || dash)), h('div', {}, h('span', {}, 'Balance'), h('b', {}, it.balance ? it.balance + ' mm' : dash))),
      h('div', { class: 'rk-price' },
        h('div', {}, h('div', { class: 'u' }, 'UNSER PREIS'), h('div', { class: 'p' }, psEur(it.preis) || dash)),
        it.uvp ? h('div', {}, h('div', { class: 'uvp-l' }, 'UVP'), h('div', { class: 'uvp' }, psEur(it.uvp))) : null)));
}

function psPaintRackets() {
  const box = document.getElementById('ps-racket-grid');
  if (!box) return;
  const l = psList('schlaeger');
  const nodes = l.items.map((it, i) => {
    const wrap = h('div', { class: 'rk-wrap' + (i === PS.edit ? ' editing' : ''), draggable: 'true' },
      psRacketCard(it),
      h('button', { class: 'rk-copy', title: 'In die Zwischenablage kopieren', onclick: (e) => { e.stopPropagation(); psClipAdd(it); } }, 'Kopieren'));
    wrap.addEventListener('click', () => psSelect(i));
    wrap.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/plain', String(i)); wrap.classList.add('dragging'); });
    wrap.addEventListener('dragend', () => wrap.classList.remove('dragging'));
    wrap.addEventListener('dragover', (e) => { e.preventDefault(); wrap.classList.add('drag-over'); });
    wrap.addEventListener('dragleave', () => wrap.classList.remove('drag-over'));
    wrap.addEventListener('drop', (e) => {
      e.preventDefault();
      const from = parseInt(e.dataTransfer.getData('text/plain'), 10);
      if (isNaN(from) || from === i) return;
      const [moved] = l.items.splice(from, 1);
      l.items.splice(i, 0, moved);
      l.sel = i; PS.edit = -1;
      psChanged(); psRender();
    });
    return wrap;
  });
  // Live-Vorschau des gerade eingetippten Schilds, solange es noch nicht in der Liste steht
  const f = psForm('schlaeger');
  if (PS.edit < 0 && Object.entries(f).some(([k, v]) => !['marke', 'farbe'].includes(k) && v)) nodes.push(h('div', { class: 'rk-wrap draft' }, psRacketCard(f)));
  box.replaceChildren(...(nodes.length ? nodes : [h('p', { class: 'ps-empty' }, 'Noch keine Schilder. Felder ausfüllen und „Hinzufügen“ (Enter).')]));
  const count = document.getElementById('ps-racket-count');
  if (count) count.textContent = l.items.length + ' Stück · ' + Math.ceil(l.items.length / 6 || 0) + ' Seite(n) à 6';
}

function psFillPage() {
  const l = psList('schlaeger');
  if (!l.items.length) { toast('Die Seite ist leer.'); return; }
  const per = (PS.info.schlaeger && PS.info.schlaeger.pro_blatt) || 6;
  const last = l.items[l.items.length - 1];
  let added = 0;
  while (l.items.length % per !== 0) { l.items.push({ ...last, _blatt: 0 }); added++; }
  if (!added) { toast('Die Seite ist schon voll.'); return; }
  psChanged(); psRender();
}

function psClipAdd(it) {
  PS.clip.unshift(JSON.parse(JSON.stringify({ ...it, _blatt: 0 })));
  if (PS.clip.length > 10) PS.clip.pop();
  toast('✓ „' + (it.name || 'Schild') + '“ kopiert');
  psRender(true);
}

function psPagesBox() {
  const nameIn = h('input', { id: 'ps-page-name', placeholder: 'Name der Seite …', maxlength: 40, onkeydown: (e) => { if (e.key === 'Enter') psSavePage(); } });
  const saved = PS.pages.length ? PS.pages.map((p, i) => h('div', { class: 'saved-row' },
    h('span', { class: 'grow' }, p.name, ' ', h('small', {}, p.date + ' · ' + p.cards.length + ' Schilder')),
    h('button', { class: 'mini-btn', title: 'Seite durch diese ersetzen', onclick: () => psLoadPage(i, false) }, 'Laden'),
    h('button', { class: 'mini-btn', title: 'An die Seite anhängen', onclick: () => psLoadPage(i, true) }, 'Hinzufügen'),
    h('button', { class: 'mini-btn', title: 'Mit der aktuellen Seite überschreiben', onclick: () => psSavePage(p.name) }, 'Überschreiben'),
    h('button', { class: 'mini-btn', title: 'Löschen', onclick: () => confirmDialog('Seite löschen', 'Die gespeicherte Seite „' + p.name + '“ löschen?', 'Löschen', () => { PS.pages.splice(i, 1); psPagesSave(); psRender(true); }) }, '✕')))
    : [h('p', { class: 'ps-empty small' }, 'Keine gespeicherten Seiten.')];
  const clip = PS.clip.length ? PS.clip.map((c, i) => h('div', { class: 'saved-row' }, h('span', { class: 'grow' }, c.name || 'Schild'),
    h('button', { class: 'mini-btn', onclick: () => { psList('schlaeger').items.push({ ...c }); psChanged('schlaeger'); psRender(); toast('✓ „' + c.name + '“ eingefügt'); } }, '↓ Einfügen'),
    h('button', { class: 'mini-btn', title: 'In eine gespeicherte Seite übernehmen', onclick: () => psClipToPage(i) }, 'In Seite …'),
    h('button', { class: 'mini-btn', onclick: () => { PS.clip.splice(i, 1); psRender(true); } }, '✕'))) : [h('p', { class: 'ps-empty small' }, 'Noch nichts kopiert. Bei einem Schild auf „Kopieren“ klicken.')];
  return h('div', { class: 'card-box' },
    h('h3', {}, 'Gespeicherte Seiten', h('span', { class: 'spacer' }),
      h('button', { class: 'mini-btn', onclick: psPagesExport }, '↓ Export'), h('button', { class: 'mini-btn', onclick: psPagesImport }, '↑ Import')),
    h('div', { class: 'btn-row', style: 'margin:0 0 8px' }, nameIn, h('button', { class: 'btn', onclick: () => psSavePage() }, 'Speichern')),
    saved, h('h3', { style: 'margin-top:12px' }, 'Zwischenablage (' + PS.clip.length + ')'), clip);
}

async function psPagesSave() {
  const res = await psCall('seiten_speichern', PS.pages);
  if (!res.ok) errorDialog('Speichern fehlgeschlagen', res.message || 'Die Seiten konnten nicht gespeichert werden.');
}

function psSavePage(overName) {
  const input = document.getElementById('ps-page-name');
  const name = (overName || (input ? input.value : '')).trim().slice(0, 40);
  const cards = psList('schlaeger').items.map((i) => { const c = { ...i }; delete c._blatt; return c; });
  if (!name) { toast('Bitte einen Namen eingeben.'); return; }
  if (!cards.length) { toast('Die Seite ist leer.'); return; }
  const date = new Date().toLocaleDateString('de-DE');
  const doSave = () => {
    const at = PS.pages.findIndex((p) => p.name.toLowerCase() === name.toLowerCase());
    const page = { name, date, cards };
    if (at >= 0) PS.pages[at] = page; else PS.pages.unshift(page);
    psPagesSave(); psRender(true); toast('✓ Seite „' + name + '“ gespeichert');
  };
  if (!overName && PS.pages.some((p) => p.name.toLowerCase() === name.toLowerCase())) confirmDialog('Seite überschreiben', 'Es gibt schon eine Seite „' + name + '“. Überschreiben?', 'Überschreiben', doSave);
  else doSave();
}

function psLoadPage(i, append) {
  const l = psList('schlaeger');
  const cards = PS.pages[i].cards.map((c) => ({ ...c, _blatt: 0 }));
  const run = () => { l.items = append ? l.items.concat(cards) : cards; l.sel = -1; PS.edit = -1; psChanged('schlaeger'); psRender(); };
  if (!append && l.items.length) confirmDialog('Seite laden', 'Die aktuelle Seite durch „' + PS.pages[i].name + '“ ersetzen?', 'Laden', run); else run();
}

function psClipToPage(ci) {
  if (!PS.pages.length) { toast('Es gibt noch keine gespeicherte Seite.'); return; }
  const sel = h('select', {}, PS.pages.map((p, i) => h('option', { value: i }, p.name)));
  showModal({ title: 'In gespeicherte Seite übernehmen', size: 'medium', body: h('div', { class: 'stack' }, h('p', {}, '„' + (PS.clip[ci].name || 'Schild') + '“ an diese Seite anhängen:'), sel),
    foot: [h('span', { class: 'spacer' }), h('button', { class: 'btn', onclick: closeModal }, 'Abbrechen'),
      h('button', { class: 'btn primary', onclick: () => { const c = { ...PS.clip[ci] }; delete c._blatt; PS.pages[+sel.value].cards.push(c); closeModal(); psPagesSave(); psRender(true); toast('✓ Übernommen'); } }, 'Übernehmen')] });
}

async function psPagesExport() {
  const res = await apiCall(psCall('seiten_exportieren'));
  if (res.ok) toast('Exportiert: ' + res.anzahl + ' Seiten → ' + res.datei, 5000);
}

async function psPagesImport() {
  const res = await apiCall(psCall('seiten_importieren'));
  if (!res.ok) return;
  let added = 0;
  res.seiten.forEach((p) => {
    const at = PS.pages.findIndex((x) => x.name.toLowerCase() === p.name.toLowerCase());
    if (at >= 0) PS.pages[at] = p; else { PS.pages.push(p); added++; }
  });
  await psPagesSave();
  psRender(true);
  toast(res.seiten.length + ' Seiten importiert (' + added + ' neu).');
}

function psSearchBox() {
  const q = PS.search.trim().toLowerCase();
  const hits = [];
  if (q.length >= 2) {
    PS.pages.forEach((p) => p.cards.forEach((c) => {
      if (String(c.name || '').toLowerCase().includes(q) || String(c.marke || '').toLowerCase().includes(q)) hits.push({ page: p.name, card: c });
    }));
  }
  const input = h('input', { value: PS.search, placeholder: 'Modellname oder Marke … (ab 2 Zeichen)', oninput: (e) => { PS.search = e.target.value; psPaintSearch(); } });
  return h('div', { class: 'card-box' }, h('h3', {}, 'Globale Suche', h('span', { class: 'spacer' }), h('small', { id: 'ps-search-count', class: 'muted' }, hits.length ? hits.length + ' Treffer' : '')),
    input, h('div', { id: 'ps-search-results', class: 'ps-search-results' }, psSearchRows(hits, q)));
}

function psSearchRows(hits, q) {
  if (q.length < 2) return [h('p', { class: 'ps-empty small' }, 'Mindestens 2 Zeichen eingeben …')];
  if (!hits.length) return [h('p', { class: 'ps-empty small' }, 'Keine Treffer.')];
  return hits.slice(0, 40).map((x) => h('div', { class: 'saved-row' }, h('span', { class: 'grow' }, x.card.name || '', ' ', h('small', {}, x.card.marke + ' · ' + x.page + ' · ' + psEur(x.card.preis))),
    h('button', { class: 'mini-btn', onclick: () => { psLoadCardsOf(x, false); } }, 'Laden'), h('button', { class: 'mini-btn', onclick: () => { psLoadCardsOf(x, true); } }, 'Hinzufügen')));
}

function psLoadCardsOf(hit, append) {
  const l = psList('schlaeger');
  const card = { ...hit.card, _blatt: 0 };
  l.items = append ? l.items.concat([card]) : [card];
  l.sel = -1; PS.edit = -1;
  psChanged('schlaeger'); psRender(); toast('✓ „' + (card.name || 'Schild') + '“ ' + (append ? 'hinzugefügt' : 'geladen'));
}

function psPaintSearch() {
  const q = PS.search.trim().toLowerCase();
  const hits = [];
  if (q.length >= 2) PS.pages.forEach((p) => p.cards.forEach((c) => { if (String(c.name || '').toLowerCase().includes(q) || String(c.marke || '').toLowerCase().includes(q)) hits.push({ page: p.name, card: c }); }));
  const box = document.getElementById('ps-search-results');
  if (box) box.replaceChildren(...psSearchRows(hits, q));
  const count = document.getElementById('ps-search-count');
  if (count) count.textContent = hits.length ? hits.length + ' Treffer' : '';
}

/* ---------- Einstellungen ---------- */

async function psSettingsSection() {
  await PS.ready;
  if (!PS.cfg) return h('p', { class: 'muted' }, 'Die Preisschilder sind nicht verfügbar (Datenordner nicht erreichbar).');
  const c = JSON.parse(JSON.stringify(PS.cfg));
  const num = (obj, key) => h('input', { type: 'text', value: String(obj[key]), style: 'width:80px', oninput: (e) => { obj[key] = e.target.value.replace(',', '.'); } });
  const rows = Object.entries(PS_TYPES).map(([typ, t]) => h('tr', {}, h('td', {}, t.title), h('td', {}, num(c[typ], 'breite')), h('td', {}, num(c[typ], 'hoehe'))));
  const brandBox = h('div', {});
  const newName = h('input', { placeholder: 'Neue Marke', style: 'width:140px' });
  const brandRows = () => Object.entries(c.marken).map(([name, v]) => h('div', { class: 'saved-row' }, h('b', { style: 'width:110px' }, name),
    h('input', { type: 'color', value: v.farbe, oninput: (e) => { v.farbe = e.target.value; }, style: 'width:36px;height:26px;padding:0;border:0' }),
    h('span', { class: 'grow muted' }, 'Logo: Schläger/' + name.toLowerCase().replace(/ /g, '') + '.png'),
    h('button', { class: 'mini-btn', onclick: () => { delete c.marken[name]; rebuild(); } }, '✕')));
  const rebuild = () => brandBox.replaceChildren(...brandRows());
  rebuild();
  const msg = h('span', { class: 'error' });
  const save = async () => {
    msg.className = 'error'; msg.textContent = '';
    const res = await psCall('einstellungen_speichern', c);
    if (!res.ok) { msg.textContent = res.message || 'Speichern fehlgeschlagen.'; return; }
    PS.cfg = res.einstellungen;
    Object.keys(PS.info).forEach((k) => delete PS.info[k]);
    for (const typ of Object.keys(PS_TYPES)) { const info = await psCall('blatt_info', typ); PS.info[typ] = info.ok ? info : { pro_blatt: 0 }; }
    msg.className = 'hint'; msg.textContent = 'Gespeichert.';
    toast('Gespeichert.');
  };
  return h('div', { class: 'stack' },
    h('div', { class: 'section-bar' }, 'Schildmaße (mm)'),
    h('table', { class: 'ptable', style: 'max-width:420px' }, h('thead', {}, h('tr', {}, h('th', {}, 'Typ'), h('th', {}, 'Breite'), h('th', {}, 'Höhe'))), h('tbody', {}, rows)),
    h('p', { class: 'muted small' }, 'Die Schläger-Schilder werden 2 Spalten breit gedruckt; ihre Höhe stammt aus dem Ausdruck des HTML-Generators (68,3 mm).'),
    h('div', { class: 'section-bar' }, 'Blatt (mm)'),
    h('div', { class: 'row' }, h('label', {}, 'Blattrand ', num(c, 'rand')), h('label', {}, 'Abstand ', num(c, 'abstand'))),
    h('p', { class: 'muted small' }, 'Abstand 0 = die Schilder grenzen aneinander, der Rahmen ist die Schnittlinie.'),
    h('div', { class: 'section-bar' }, 'Schläger-Marken und Standardfarben'), brandBox,
    h('div', { class: 'row' }, newName, h('button', { class: 'btn', onclick: () => { const n = newName.value.trim(); if (n) { c.marken[n] = { farbe: '#555555' }; newName.value = ''; rebuild(); } } }, '+ Marke')),
    h('p', { class: 'muted small' }, 'Eine neue Marke bekommt ihr weißes Logo, indem die PNG-Datei (z. B. lacoste.png) im Ordner logos/Schläger liegt.'),
    h('div', { class: 'row' }, h('button', { class: 'btn primary', onclick: save }, 'Speichern'), msg),
    h('div', { class: 'section-bar' }, 'Daten aus dem alten Programm'),
    h('div', { class: 'row' }, h('button', { class: 'btn', onclick: psTakeOver }, 'Daten aus dem alten Preisschilder-Programm übernehmen …')));
}

registerSettingsSection({ id: 'preisschilder', title: 'Preisschilder', build: psSettingsSection });

async function psTakeOver() {
  await psSaveAll();
  const plan = await apiCall(psCall('uebernahme_pruefen'));
  if (!plan.ok) return;
  const run = async (overwrite) => {
    closeModal();
    const res = await apiCall(psCall('uebernahme_ausfuehren', plan.ordner, overwrite));
    if (!res.ok) return;
    Object.keys(PS.lists).forEach((k) => delete PS.lists[k]);
    Object.keys(PS.logos).forEach((k) => delete PS.logos[k]);
    await psEnsure(PS.tab); psRender(); psPreviewSoon();
    if (activeModule === 'einstellungen') openSettings('preisschilder');
    toast(res.kopiert + ' Dateien übernommen, ' + res.uebersprungen + ' übersprungen.', 5000);
  };
  const buttons = [h('span', { class: 'spacer' }), h('button', { class: 'btn', onclick: closeModal }, 'Abbrechen')];
  if (plan.vorhanden) buttons.push(h('button', { class: 'btn', onclick: () => run(true) }, 'Vorhandenes überschreiben'));
  buttons.push(h('button', { class: 'btn primary', 'data-focus': '1', onclick: () => run(false) }, plan.vorhanden ? 'Nur Neues übernehmen' : 'Übernehmen'));
  showModal({ title: 'Daten übernehmen', size: 'medium', body: h('div', { class: 'stack' },
    h('p', {}, plan.anzahl + ' Dateien gefunden (Einstellungen, Listen, Logos) in:'), h('p', { class: 'path' }, plan.ordner),
    plan.vorhanden ? h('p', {}, plan.vorhanden + ' davon gibt es im Dashboard schon. Ohne Rückfrage wird nichts überschrieben.') : h('p', {}, 'Es ist noch nichts davon im Dashboard vorhanden.')), foot: buttons });
}

/* ---------- Aufbau ---------- */

function psTabs() {
  return h('div', { class: 'tabs' },
    Object.entries(PS_TYPES).map(([id, x]) => h('button', { class: id === PS.tab ? 'active' : '', onclick: async () => { await psSaveNow(PS.tab); PS.tab = id; PS.edit = -1; PS.preview.seite = 0; await psEnsure(id); psRender(); psPreviewSoon(); } }, x.title)),
    h('span', { class: 'spacer' }),
    h('button', { onclick: () => openSettings('preisschilder') }, 'Einstellungen'));
}

function psBuild() {
  const typ = PS.tab;
  const racket = psIsRacket(typ);
  const info = PS.info[typ] || {};
  const left = h('div', { class: 'ps-left' },
    h('div', { class: 'hint-bar' }, '🖨 Beim Drucken ', h('b', {}, '100 % / „Tatsächliche Größe“'), ' wählen, nicht „An Seite anpassen“, sonst stimmen die Maße nicht.'),
    psFormBox(typ), psLogoBox(typ), psListBox(typ),
    typ === 'helme' ? h('div', { class: 'card-box' }, h('h3', {}, 'Helme'), h('div', { class: 'btn-row', style: 'margin-top:0' },
      h('button', { class: 'btn', onclick: psHelmeCsv }, 'Helme aus CSV importieren …'), h('button', { class: 'btn', onclick: psAllSizes }, 'Alle Größen anlegen'))) : null,
    racket ? psPagesBox() : null, racket ? psSearchBox() : null);
  const total = psSheetItems(typ).length;
  const bar = h('div', { class: 'sheet-bar' }, h('b', {}, 'Vorschau'),
    h('span', { class: 'muted', id: 'ps-info' }, racket ? '' : (info.breite ? info.breite + ' × ' + info.hoehe + ' mm · ' + info.pro_blatt + ' pro Blatt · ' + total + ' auf dem Blatt' : '')),
    h('span', { class: 'grow' }),
    racket ? h('span', { class: 'muted', id: 'ps-racket-count' }) : h('span', { class: 'muted', id: 'ps-page-nav' }),
    racket ? h('button', { class: 'btn', title: 'Wiederholt das letzte Schild, bis die Seite voll ist', onclick: psFillPage }, 'Seite auffüllen')
      : [h('button', { class: 'btn', onclick: () => psPage(-1) }, '◀'), h('button', { class: 'btn', onclick: () => psPage(1) }, '▶')],
    h('button', { class: 'btn primary', onclick: psPrint }, 'Drucken (PDF)'));
  const right = h('div', { class: 'ps-right' }, h('div', { class: 'sheet-wrap' }, bar,
    racket ? h('div', { id: 'ps-racket-grid', class: 'rk-grid-wrap' }) : h('div', { id: 'ps-preview-box', class: 'ps-preview-box' })));
  return h('div', { class: 'ps' }, psTabs(), h('div', { class: 'ps-body' }, left, right));
}

// keepScroll: nur neu zeichnen, die Bildlaufposition der linken Spalte bleibt erhalten
function psRender(keepScroll) {
  const left = PS.root.querySelector('.ps-left');
  const top = left ? left.scrollTop : 0;
  const focus = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.key : null;
  const caret = document.activeElement && document.activeElement.selectionStart;
  PS.root.replaceChildren(psBuild());
  if (keepScroll) { const l = PS.root.querySelector('.ps-left'); if (l) l.scrollTop = top; }
  if (focus) { const el = PS.root.querySelector('#ps-form input[data-key=' + focus + ']'); if (el) { el.focus(); try { el.setSelectionRange(caret, caret); } catch (e) { /* kein Textfeld */ } } }
  if (psIsRacket()) psPaintRackets(); else psPaintPreview();
}

async function psMount(root) {
  PS.root = root;
  root.replaceChildren(h('p', { class: 'ps-empty' }, 'Lädt …'));
  const res = await psCall('start');
  if (!res.ok) {
    root.replaceChildren(h('div', { class: 'empty-start' }, h('div', { class: 'problem' }, h('h2', {}, 'Preisschilder nicht verfügbar'), h('p', {}, res.message || 'Der Datenordner ist nicht erreichbar.'))));
    PS.failed = true;
    PS.resolveReady();
    return;
  }
  PS.cfg = res.einstellungen;
  PS.meta = { groessen: res.groessen || [], farben: res.farben || [], marken_standard: res.marken_standard || {} };
  const pages = await psCall('seiten_laden');
  PS.pages = pages.ok ? pages.items : [];
  await psEnsure(PS.tab);
  psRender();
  psPreviewSoon();
  PS.resolveReady();
}

registerModule({
  id: 'preisschilder', title: 'Preisschilder', mount: psMount,
  show() { if (PS.cfg) { psEnsure(PS.tab).then(() => { psRender(); psPreviewSoon(); }); } else if (PS.failed) psMount(PS.root); },
});
window.addEventListener('blur', psSaveAll);
document.addEventListener('visibilitychange', () => { if (document.hidden) psSaveAll(); });
