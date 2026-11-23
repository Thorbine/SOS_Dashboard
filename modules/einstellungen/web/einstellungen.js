'use strict';

/* Modul Einstellungen: ein Tab in der Navigation. Jedes Modul trägt seine Abschnitte mit
   registerSettingsSection({ id, title, build }) ein; hier werden sie untereinander gezeigt. */

const EN = { root: null };

async function enRender() {
  if (!EN.root) return;
  const sections = SETTINGS_SECTIONS.slice();
  const nodes = [];
  for (const s of sections) {
    let body;
    try { body = await s.build(); } catch (e) { body = h('p', { class: 'muted' }, 'Dieser Abschnitt konnte nicht geladen werden: ' + (e.message || e)); }
    nodes.push(h('section', { class: 'set-section', id: 'set-' + s.id }, h('h2', {}, s.title), body));
  }
  const links = sections.map((s) => h('button', { class: 'mini-btn', onclick: () => enScroll(s.id) }, s.title));
  EN.root.replaceChildren(h('div', { class: 'set-page' },
    h('div', { class: 'set-head' }, h('h1', {}, 'Einstellungen'), h('span', { class: 'spacer' }), links),
    h('div', { class: 'notice' }, 'Bitte keine Passwörter speichern. Die Daten liegen unverschlüsselt im Datenordner. Änderungen werden automatisch gespeichert.'),
    nodes));
  if (EN.target) { enScroll(EN.target); EN.target = null; }
}

function enScroll(id) {
  const el = document.getElementById('set-' + id);
  if (el) el.scrollIntoView({ block: 'start' });
}

registerModule({
  id: 'einstellungen', title: 'Einstellungen',
  mount(root) { EN.root = root; },
  show() { enRender(); },
});
