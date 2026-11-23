'use strict';

/* Modul Formulare: die Druckvorlagen (PDF) aus dem Datenordner als Kacheln. Öffnen, im Ordner zeigen, ersetzen.
   Hilfsfunktionen und Dialoge kommen aus web/shell.js. Ohne App zeigt die Vorschau Beispielkacheln. */

const FM = { root: null };
const FM_DEMO = ['Kundenbestellung', 'Reklamation', 'Rücklage', 'Lieferschein'].map((name) => ({
  datei: name + '.pdf', name, format: name === 'Lieferschein' ? 'A4 hoch' : 'A4 quer', bild: '../assets/formulare/vorschau/' + name.replace('ü', 'ue') + '.png', text: '',
}));

function fmCall(name, ...args) {
  if (api) return api['formulare_' + name](...args);
  if (name === 'liste') return Promise.resolve({ ok: true, formulare: FM_DEMO, ordner: '(Datenordner)/formulare' });
  return Promise.resolve({ ok: true, demo: true });
}

async function fmAction(promise, okText) {
  const res = await apiCall(promise);
  if (res.ok && res.demo) toast('In der Vorschau passiert hier nichts.');
  else if (res.ok && okText) toast(okText);
  return res;
}

function fmTile(f) {
  return h('div', { class: 'ftile' },
    f.bild ? h('img', { src: f.bild, alt: f.name }) : h('div', { class: 'noimg' }, 'Keine Vorschau'),
    h('h4', {}, f.name),
    h('p', {}, f.format + (f.text ? ' · ' + f.text : '')),
    h('div', { class: 'fbtns' },
      h('button', { class: 'btn primary', onclick: () => fmAction(fmCall('oeffnen', f.datei)) }, 'Öffnen / Drucken'),
      h('button', { class: 'btn', onclick: () => fmAction(fmCall('im_ordner_zeigen', f.datei)) }, 'Im Ordner zeigen'),
      h('button', { class: 'btn', onclick: async () => { const r = await fmAction(fmCall('ersetzen', f.datei), 'Ersetzt. Die alte Datei liegt in formulare/_alt/.'); if (r.ok && !r.demo) fmRender(); } }, 'Ersetzen')));
}

async function fmRender() {
  const res = await fmCall('liste');
  if (!FM.root) return;
  if (!res.ok) {
    FM.root.replaceChildren(h('div', { class: 'empty-start' }, h('div', { class: 'problem' }, h('h2', {}, 'Formulare nicht verfügbar'), h('p', {}, res.message || 'Der Datenordner ist nicht erreichbar.'))));
    return;
  }
  FM.root.replaceChildren(h('div', { class: 'forms' },
    h('div', { class: 'hint-bar' }, '🖨 Beim Drucken ', h('b', {}, '100 % / „Tatsächliche Größe“'), ' wählen. Bei A4 quer mit zwei Formularen pro Blatt danach an der gestrichelten Linie schneiden.'),
    h('div', { class: 'tiles-big' }, res.formulare.map(fmTile)),
    h('div', { class: 'row' },
      h('button', { class: 'btn', onclick: () => fmAction(fmCall('ordner_oeffnen')) }, 'Ordner öffnen'),
      h('span', { class: 'muted' }, 'Neue Vorlagen erscheinen automatisch, sobald eine PDF in diesem Ordner liegt.')),
    res.formulare.length ? null : h('p', { class: 'muted' }, 'Im Ordner liegt keine PDF-Datei.')));
}

registerModule({ id: 'formulare', title: 'Formulare', mount(root) { FM.root = root; return fmRender(); }, show() { if (FM.root) fmRender(); } });

registerSettingsSection({ id: 'formulare', title: 'Formulare', build() {
  return h('div', { class: 'row' }, h('button', { class: 'btn', onclick: () => fmAction(fmCall('ordner_oeffnen')) }, 'Ordner der Formulare öffnen'),
    h('span', { class: 'muted' }, 'Eine neue PDF in diesem Ordner erscheint im Modul Formulare als Kachel.'));
} });
