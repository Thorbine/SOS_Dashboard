'use strict';

/* Modul Hersteller. Hilfsfunktionen, Dialoge und `api` kommen aus web/shell.js.
   In der App kommen die Daten über api.hersteller_laden() und api.hersteller_speichern().
   Ohne App läuft eine Vorschau mit Beispieldaten, die nichts speichert. */

// Einzige Stelle für den Begriff in der Seitenleiste ("Lieferanten" oder "Hersteller").
const SIDEBAR_TITLE = 'Lieferanten';

const DOC_TYPES = {
  RS: { name: 'Retourenschein', title: 'Retourenschein' },
  RK: { name: 'Reklamationsformular', title: 'Reklamation' },
};
const RETURN_REASONS = ['Reklamation', 'Retoure', 'Fehllieferung', 'Garantie', 'Sonstiges'];
const WANTED = ['Reparatur', 'Umtausch', 'Gutschrift', 'Geld zurück'];


/* ---------- Datenmodell ---------- */

const BLOCK_TEMPLATE = [
  { type: 'fields', title: 'Infos', defaults: [{ label: 'Unsere Kundennr', value: '' }] },
  { type: 'contacts', title: 'Ansprechpartner' },
  { type: 'addresses', title: 'Adressen', defaults: [{ label: 'Hauptadresse' }, { label: 'Retourenadresse' }, { label: 'Reklamationsadresse' }] },
  { type: 'links', title: 'Links', defaults: [{ label: 'B2B' }, { label: 'Reklamation' }, { label: 'Medien' }] },
  { type: 'notes', title: 'Notizen' },
];

const newField = (label = '', value = '') => ({ id: uid(), label, value });
const newContact = (c = {}) => ({ id: uid(), name: '', role: '', phone: '', mobile: '', email: '', note: '', ...c });
const newAddress = (a = {}) => ({ id: uid(), label: '', isDefault: false, company: '', addition: '', street: '', zip: '', city: '', country: 'Deutschland', contactName: '', phone: '', email: '', note: '', ...a });
const newLink = (title = '', url = '') => ({ id: uid(), title, url });
const newGroup = (label = '', links = []) => ({ id: uid(), label, links });

function newBlock(type, title, defaults) {
  const b = { id: uid(), type, title, visible: true };
  if (type === 'fields') b.fields = (defaults || []).map((d) => newField(d.label, d.value || ''));
  if (type === 'contacts') b.contacts = [];
  if (type === 'addresses') b.addresses = (defaults || []).map((d, i) => newAddress({ label: d.label, isDefault: i === 0 }));
  if (type === 'links') b.groups = (defaults || []).map((d) => newGroup(d.label));
  if (type === 'notes') b.text = '';
  return b;
}

function nowIso() {
  const d = new Date();
  return todayIso() + 'T' + [d.getHours(), d.getMinutes(), d.getSeconds()].map((n) => String(n).padStart(2, '0')).join(':');
}

// Neue Hersteller entstehen aus der Vorlage in den Daten (blockTemplate).
function newSupplier(name, template) {
  const now = nowIso();
  return { id: uid(), name, createdAt: now, updatedAt: now, blocks: (template || state.meta.blockTemplate).map((t) => newBlock(t.type, t.title, t.defaults)) };
}

// Kurzschreibweise für die Beispieldaten.
function sample(name, o) {
  const s = newSupplier(name, BLOCK_TEMPLATE);
  const [infos, contacts, addresses, links, notes] = s.blocks;
  infos.fields[0].value = o.kd || '';
  (o.fields || []).forEach(([l, v]) => infos.fields.push(newField(l, v)));
  contacts.contacts = (o.contacts || []).map(newContact);
  addresses.addresses = (o.addresses || []).map((a, i) => newAddress({ isDefault: i === (o.defaultAddress || 0), ...a }));
  links.groups = [newGroup('B2B', (o.b2b || []).map((l) => newLink(...l))), newGroup('Reklamation', (o.rekla || []).map((l) => newLink(...l))), newGroup('Medien', (o.medien || []).map((l) => newLink(...l)))];
  notes.text = o.notes || '';
  return s;
}

function demoSuppliers() {
  return [
    sample('HEAD Sport', {
      kd: '104711',
      fields: [['Zahlungsziel', '30 Tage netto'], ['Mindestbestellwert', '250 €']],
      contacts: [
        { name: 'Martina Beispiel', role: 'Außendienst Nord', phone: '0531 000000-11', mobile: '0170 0000011', email: 'm.beispiel@example.de', note: 'Dienstags am besten erreichbar' },
        { name: 'Service-Team', role: 'Reklamationen', phone: '089 000000-20', email: 'service@example.de' },
      ],
      addresses: [
        { label: 'Hauptadresse', company: 'HEAD Beispiel GmbH', street: 'Musterstraße 1', zip: '80000', city: 'München' },
        { label: 'Retourenadresse', company: 'HEAD Beispiel GmbH', addition: 'Retourenlager Halle 3', street: 'Logistikweg 12', zip: '85000', city: 'Musterhausen', contactName: 'Wareneingang', phone: '089 000000-30' },
        { label: 'Reklamationsadresse', company: 'HEAD Beispiel GmbH', addition: 'Service Center', street: 'Werkstraße 5', zip: '85000', city: 'Musterhausen', email: 'service@example.de' },
      ],
      defaultAddress: 1,
      b2b: [['B2B-Shop', 'b2b.example.de'], ['Vororder-Portal', 'https://vororder.example.de']],
      rekla: [['Reklamationsportal', 'https://service.example.de/reklamation']],
      medien: [['Bilddatenbank', 'https://media.example.de']],
      notes: 'Vororder Winter bis Ende Februar.\nRetouren nur mit RMA-Nummer aus dem Portal.',
    }),
    sample('Wilson', {
      kd: '20815',
      contacts: [{ name: 'Jonas Muster', role: 'Vertreter Tennis', mobile: '0171 0000022', email: 'j.muster@example.com' }],
      addresses: [
        { label: 'Hauptadresse', company: 'Wilson Beispiel Europe', street: 'Beispielallee 40', zip: '81000', city: 'München' },
        { label: 'Retourenadresse', company: 'Wilson Beispiel Europe', addition: 'c/o Musterlogistik', street: 'Hafenstraße 8', zip: '20000', city: 'Hamburg' },
      ],
      b2b: [['B2B', 'https://b2b.example.com']],
      medien: [['Media Center', 'https://media.example.com']],
      notes: 'Besaitungsmaterial getrennt bestellen.',
    }),
    sample('Völkl', {
      kd: '300123',
      fields: [['Händler-ID Portal', 'SOS-BS-01']],
      contacts: [
        { name: 'Sabine Vorlage', role: 'Innendienst', phone: '09421 000000', email: 's.vorlage@example.de' },
        { name: 'Peter Probe', role: 'Außendienst', mobile: '0172 0000033', email: 'p.probe@example.de', note: 'Kommt im März zur Order' },
      ],
      addresses: [
        { label: 'Hauptadresse', company: 'Völkl Beispiel GmbH', street: 'Skiweg 2', zip: '94000', city: 'Straubing' },
        { label: 'Reklamationsadresse', company: 'Völkl Beispiel GmbH', addition: 'Serviceabteilung', street: 'Skiweg 2', zip: '94000', city: 'Straubing', email: 'service@example.de' },
      ],
      b2b: [['Händlerportal', 'https://haendler.example.de']],
      rekla: [['Garantieantrag', 'https://haendler.example.de/garantie']],
      notes: 'Ski-Reklamationen immer mit Fotos von Belag und Kante.',
    }),
    sample('Ortovox', {
      kd: '55012',
      contacts: [{ name: 'Lena Platzhalter', role: 'Kundenservice', phone: '089 000000-55', email: 'haendler@example.de' }],
      addresses: [{ label: 'Hauptadresse', company: 'Ortovox Beispiel GmbH', street: 'Bergstraße 9', zip: '82000', city: 'Taufkirchen' }],
      b2b: [['B2B', 'https://b2b.example.org']],
      medien: [['Bilder und Texte', 'https://brand.example.org']],
      notes: 'LVS-Geräte: Rücksendung nur über Service-Formular.',
    }),
    sample('Scott', {
      kd: '77-4410',
      contacts: [{ name: 'Tim Beispielmann', role: 'Vertreter Wintersport', mobile: '0173 0000044', email: 't.beispielmann@example.com' }],
      addresses: [
        { label: 'Hauptadresse', company: 'Scott Beispiel Germany', street: 'Sportplatz 3', zip: '85000', city: 'Garching' },
        { label: 'Retourenadresse', company: 'Scott Beispiel Germany', addition: 'Warehouse', street: 'Lagerring 21', zip: '85000', city: 'Garching' },
      ],
      b2b: [['B2B', 'https://b2b.example.net']],
      rekla: [['Warranty Portal', 'https://warranty.example.net']],
    }),
    sample('Lacoste', {
      kd: '',
      contacts: [{ name: 'Claire Exemple', role: 'Showroom Hamburg', phone: '040 000000-66', email: 'c.exemple@example.fr' }],
      addresses: [{ label: 'Hauptadresse', company: 'Lacoste Beispiel Germany', street: 'Modeweg 7', zip: '40000', city: 'Düsseldorf' }],
      b2b: [['Orderportal', 'https://order.example.fr']],
      notes: 'Kundennummer noch erfragen.',
    }),
  ];
}

const state = {
  demo: true,          // Vorschau im Browser ohne Python
  ready: false,        // Daten geladen, Speichern erlaubt
  problem: null,       // Fehler beim Laden (kein Ordner, nicht erreichbar, Datei beschädigt)
  dataDir: '',
  meta: { schemaVersion: 1, revision: 0, blockTemplate: BLOCK_TEMPLATE },
  suppliers: [],
  company: { name: 'SOS Sport GmbH', street: 'Rebenring 10', zip: '38106', city: 'Braunschweig', country: 'Deutschland', phone: '+49 (0) 531-347711', email: 'shop@sos-sport.de', managingDirector: 'Oliver Nieß', register: 'HRB 4881, Amtsgericht Braunschweig', vatId: 'DE 201646705', showFooter: false },
  counters: { RS: {}, RK: {} },
  documents: [],
  activeId: null,
  editMode: false,
  search: '',
  menu: null,          // 'doc' | 'addBlock' | null
  renamingBlockId: null,
  docsPanel: false,
  draft: null,         // Entwurf im Dokument-Dialog
};

// Beispiel-Dokumente für den ersten Hersteller (nur Vorschau).
function seedDocuments() {
  const s = state.suppliers[0];
  const year = String(new Date().getFullYear());
  const addr = s.blocks[2].addresses;
  const add = (type, n, addrIdx, data) => {
    const number = type + '-' + year + '-' + String(n).padStart(4, '0');
    state.documents.push({
      id: uid(), supplierId: s.id, type, number, createdAt: year + '-0' + (n + 2) + '-1' + n + 'T10:00:00',
      file: 'dokumente/' + s.name + '/' + number + '_' + DOC_TYPES[type].name + '.pdf',
      addressSnapshot: clone(addr[addrIdx]), data,
    });
  };
  add('RS', 1, 1, { date: year + '-03-11', addressId: addr[1].id, customerNo: '104711', contactId: '', rma: 'RMA-88123', shipping: 'DPD', packages: 1, reasonGeneral: 'Retoure', remark: '', positions: [{ article: 'Tennisschläger Speed MP', articleNo: '233612', size: 'L3', color: 'schwarz/weiß', qty: 2, reason: 'Retoure' }] });
  add('RS', 2, 1, { date: year + '-04-12', addressId: addr[1].id, customerNo: '104711', contactId: '', rma: '', shipping: 'DPD', packages: 2, reasonGeneral: 'Fehllieferung', remark: 'Falsche Größe geliefert', positions: [{ article: 'Skischuh Formula 110', articleNo: '601150', size: '27,5', color: 'anthrazit', qty: 1, reason: 'Fehllieferung' }, { article: 'Skihelm Radar', articleNo: '323410', size: 'M/L', color: 'weiß', qty: 3, reason: 'Fehllieferung' }] });
  add('RK', 1, 2, { date: year + '-03-11', addressId: addr[2].id, customerNo: '104711', contactId: '', reference: '', articles: [{ article: 'Ski Supershape e-Magnum', articleNo: '313303', size: '170 cm', color: '', purchaseDate: year + '-01-15', receiptNo: 'R-10442' }], description: 'Kante löst sich im Schaufelbereich nach drei Skitagen.', wanted: ['Umtausch'], accessories: 'Bindung montiert', printProcessing: false });
  state.counters.RS[year] = 2;
  state.counters.RK[year] = 1;
}

const activeSupplier = () => state.suppliers.find((s) => s.id === state.activeId) || null;
const blockOf = (s, type) => s.blocks.find((b) => b.type === type);
const docsOf = (id) => state.documents.filter((d) => d.supplierId === id);

function customerNoOf(s) {
  for (const b of s.blocks) {
    if (b.type !== 'fields') continue;
    const f = b.fields.find((x) => x.label.trim().toLowerCase() === 'unsere kundennr');
    if (f) return f.value;
  }
  return '';
}

/* ---------- Seitenleiste und Suche ---------- */

function contentHit(s, q) {
  const inc = (v) => v && String(v).toLowerCase().includes(q);
  for (const b of s.blocks) {
    if (b.type === 'fields') {
      for (const f of b.fields) if (inc(f.value)) return f.label + ': ' + f.value;
    } else if (b.type === 'contacts') {
      for (const c of b.contacts) {
        for (const k of ['name', 'role', 'phone', 'mobile', 'email', 'note']) {
          if (inc(c[k])) return b.title + ': ' + (k === 'name' ? c.name : (c.name ? c.name + ', ' : '') + c[k]);
        }
      }
    } else if (b.type === 'addresses') {
      for (const a of b.addresses) {
        for (const k of ['company', 'addition', 'street', 'zip', 'city', 'contactName', 'phone', 'email', 'note']) {
          if (inc(a[k])) return (a.label || b.title) + ': ' + a[k];
        }
      }
    } else if (b.type === 'links') {
      for (const g of b.groups) for (const l of g.links) if (inc(l.title) || inc(l.url)) return (g.label || b.title) + ': ' + (l.title || l.url);
    } else if (b.type === 'notes' && inc(b.text)) {
      const i = b.text.toLowerCase().indexOf(q);
      const start = Math.max(0, i - 18);
      return b.title + ': ' + (start > 0 ? '…' : '') + b.text.slice(start, i + q.length + 30).replace(/\s+/g, ' ');
    }
  }
  return null;
}

function renderList() {
  const q = state.search.trim().toLowerCase();
  const ul = document.getElementById('supplier-list');
  const rows = [];
  for (const s of state.suppliers) {
    if (!q || s.name.toLowerCase().includes(q)) rows.push({ s, hit: null });
    else {
      const hit = contentHit(s, q);
      if (hit) rows.push({ s, hit });
    }
  }
  rows.sort((a, b) => a.s.name.localeCompare(b.s.name, 'de', { sensitivity: 'base' }));
  ul.replaceChildren(...rows.map(({ s, hit }) =>
    h('li', { class: s.id === state.activeId ? 'active' : '', onclick: () => selectSupplier(s.id), oncontextmenu: (e) => supplierContextMenu(e, s) },
      s.name || '(ohne Namen)', hit && h('span', { class: 'hit', title: hit }, hit))));
  if (!rows.length) ul.append(h('li', { class: 'none' }, 'Keine Treffer'));
}

// Rechtsklick auf einen Hersteller in der Liste: Bearbeiten und Löschen.
function closeContextMenu() { document.getElementById('ctx-menu')?.remove(); }

function supplierContextMenu(e, s) {
  e.preventDefault();
  closeContextMenu();
  if (!state.ready) return;
  const item = (label, danger, fn) => h('button', { class: danger ? 'danger' : '', onclick: () => { closeContextMenu(); fn(); } }, label);
  const menu = h('div', { id: 'ctx-menu', class: 'menu ctx', onclick: (ev) => ev.stopPropagation(), oncontextmenu: (ev) => ev.preventDefault() },
    item('Bearbeiten', false, () => {
      selectSupplier(s.id);
      state.editMode = true;
      renderMain();
      document.querySelector('.name-input')?.focus();
    }),
    item('Löschen', true, () => deleteSupplier(s)));
  document.body.append(menu);
  const r = menu.getBoundingClientRect();
  menu.style.left = Math.max(4, Math.min(e.clientX, innerWidth - r.width - 4)) + 'px';
  menu.style.top = Math.max(4, Math.min(e.clientY, innerHeight - r.height - 4)) + 'px';
}

function selectSupplier(id) {
  state.activeId = id;
  state.editMode = false;
  state.menu = null;
  state.renamingBlockId = null;
  state.docsPanel = false;
  render();
}

/* ---------- Hauptbereich ---------- */

function render() {
  renderList();
  renderMain();
  renderPanel();
}

// Eingabefeld, das direkt in das Datenobjekt schreibt (ohne Neuzeichnen).
function bind(obj, key, placeholder, opts = {}) {
  const tag = opts.multiline ? 'textarea' : 'input';
  return h(tag, {
    type: opts.multiline ? null : (opts.type || 'text'), class: opts.cls, placeholder, value: obj[key] ?? '',
    rows: opts.rows, min: opts.min, spellcheck: 'false', 'data-focus': opts.focus,
    oninput: (e) => { obj[key] = opts.type === 'number' ? Number(e.target.value) : e.target.value; if (opts.oninput) opts.oninput(e); },
    onkeydown: opts.onkeydown,
  });
}

function move(arr, i, dir) {
  const j = i + dir;
  if (j < 0 || j >= arr.length) return;
  [arr[i], arr[j]] = [arr[j], arr[i]];
  renderMain();
}

function rowTools(arr, i, what, after) {
  return h('span', { class: 'tools' },
    tool('up', 'Nach oben', () => move(arr, i, -1), { disabled: i === 0 }),
    tool('down', 'Nach unten', () => move(arr, i, 1), { disabled: i === arr.length - 1 }),
    tool('trash', what + ' löschen', () => { arr.splice(i, 1); if (after) after(); renderMain(); }, { cls: 'danger' }));
}

function renderMain() {
  const main = document.getElementById('main');
  if (state.problem) { main.replaceChildren(problemScreen(state.problem)); return; }
  if (!state.ready) { main.replaceChildren(h('div', { class: 'empty-start' }, 'Daten werden geladen …')); return; }
  const s = activeSupplier();
  if (!s) {
    main.replaceChildren(h('div', { class: 'empty-start' }, 'Hersteller links auswählen oder neu anlegen'));
    return;
  }
  const scroll = main.scrollTop;
  const edit = state.editMode;
  const n = docsOf(s.id).length;

  const head = h('div', { class: 'main-head' },
    edit ? bind(s, 'name', 'Name des Herstellers', { cls: 'name-input', oninput: renderList }) : h('h2', {}, s.name),
    h('div', { class: 'menu-wrap' },
      h('button', { class: 'btn', onclick: (e) => toggleMenu('doc', e) }, 'Dokument erstellen ▾'),
      state.menu === 'doc' && h('div', { class: 'menu' },
        h('button', { onclick: () => openDocDialog('RS') }, 'Retourenschein'),
        h('button', { onclick: () => openDocDialog('RK') }, 'Reklamationsformular'))),
    h('button', { class: 'btn', onclick: () => { state.docsPanel = true; renderPanel(); } }, 'Dokumente (' + n + ')'),
    h('button', { class: 'btn' + (edit ? ' active' : ''), onclick: () => { state.editMode = !edit; state.menu = null; state.renamingBlockId = null; renderMain(); } },
      icon('pencil'), edit ? 'Bearbeiten beenden' : 'Bearbeiten'));

  const blocks = s.blocks.filter((b) => edit || b.visible).map((b) => renderBlock(s, b)).filter(Boolean);
  const nodes = [head, ...blocks];

  if (edit) {
    const addTypes = [
      ['Infos-Felder', () => newBlock('fields', 'Infos', [{ label: '' }])],
      ['Ansprechpartner', () => newBlock('contacts', 'Ansprechpartner')],
      ['Adressen', () => newBlock('addresses', 'Adressen', [{ label: 'Adresse' }])],
      ['Linkgruppe', () => newBlock('links', 'Links', [{ label: '' }])],
      ['Notiz', () => newBlock('notes', 'Notiz')],
      ['Freitext', () => newBlock('notes', 'Freitext')],
    ];
    nodes.push(h('div', { class: 'edit-foot' },
      h('div', { class: 'menu-wrap' },
        h('button', { class: 'btn primary', onclick: (e) => toggleMenu('addBlock', e) }, '+ Block hinzufügen'),
        state.menu === 'addBlock' && h('div', { class: 'menu left', style: 'top:auto;bottom:calc(100% + 4px)' },
          addTypes.map(([label, make]) => h('button', { onclick: () => addBlock(s, make()) }, label)))),
      h('span', { class: 'spacer' }),
      h('button', { class: 'btn danger', onclick: () => deleteSupplier(s) }, icon('trash'), 'Hersteller löschen')));
  }

  main.replaceChildren(...nodes);
  main.scrollTop = scroll;
  main.querySelectorAll('textarea.notes-area').forEach(autoGrow);
  const f = main.querySelector('[data-focus]');
  if (f) { f.focus(); if (f.select) f.select(); }
}

function toggleMenu(name, e) {
  e.stopPropagation();
  state.menu = state.menu === name ? null : name;
  renderMain();
}

function autoGrow(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.max(130, ta.scrollHeight + 2) + 'px';
}

// Neue Blöcke landen vor dem Notizen-Block am Ende, damit Notizen ganz unten bleiben.
function addBlock(s, block) {
  const last = s.blocks[s.blocks.length - 1];
  const at = last && last.type === 'notes' && last.title === 'Notizen' ? s.blocks.length - 1 : s.blocks.length;
  s.blocks.splice(at, 0, block);
  state.menu = null;
  state.renamingBlockId = block.id;
  renderMain();
}

function deleteSupplier(s) {
  confirmDialog('Hersteller löschen', '„' + s.name + '“ wirklich löschen? Dokumente bleiben im Archiv erhalten.', 'Löschen', () => {
    state.suppliers = state.suppliers.filter((x) => x.id !== s.id);
    state.activeId = null;
    state.editMode = false;
    render();
  });
}

/* ---------- Blöcke ---------- */

let dragBlockId = null;

function renderBlock(s, b) {
  const edit = state.editMode;
  if (!VIEWS[b.type]) return null; // unbekannter Blocktyp aus einer neueren Version: nicht anzeigen, aber behalten
  const body = edit ? EDITORS[b.type](b) : VIEWS[b.type](b);
  if (!edit && !body) return null; // leere Blöcke stören im Ansichtsmodus nicht

  const i = s.blocks.indexOf(b);
  const renaming = edit && state.renamingBlockId === b.id;
  const el = h('section', { class: 'block' + (b.visible ? '' : ' hidden-block') });

  const head = h('div', { class: 'block-head' });
  if (edit) {
    const grip = tool('grip', 'Ziehen zum Verschieben', null, { cls: 'grip', filled: true });
    grip.draggable = true;
    grip.addEventListener('dragstart', (e) => {
      dragBlockId = b.id;
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', b.id);
      e.dataTransfer.setDragImage(el, 20, 20);
      setTimeout(() => el.classList.add('dragging'), 0);
    });
    grip.addEventListener('dragend', () => { dragBlockId = null; renderMain(); });
    el.addEventListener('dragover', (e) => { if (dragBlockId && dragBlockId !== b.id) { e.preventDefault(); el.classList.add('drag-over'); } });
    el.addEventListener('dragleave', (e) => { if (!el.contains(e.relatedTarget)) el.classList.remove('drag-over'); });
    el.addEventListener('drop', (e) => {
      e.preventDefault();
      const from = s.blocks.findIndex((x) => x.id === dragBlockId);
      if (from < 0) return;
      const [moved] = s.blocks.splice(from, 1);
      s.blocks.splice(s.blocks.indexOf(b) + (from < i ? 1 : 0), 0, moved);
      dragBlockId = null;
      renderMain();
    });
    head.append(grip);
  }
  if (renaming) {
    head.append(bind(b, 'title', 'Titel des Blocks', {
      cls: 'title-input', focus: '1',
      onkeydown: (e) => { if (e.key === 'Enter' || e.key === 'Escape') { state.renamingBlockId = null; renderMain(); } },
    }));
  } else {
    head.append(h('h3', {}, b.title || '(ohne Titel)'));
  }
  if (edit) {
    if (!b.visible) head.append(h('span', { class: 'badge' }, 'ausgeblendet'));
    head.append(h('span', { class: 'tools' },
      tool('up', 'Block nach oben', () => move(s.blocks, i, -1), { disabled: i === 0 }),
      tool('down', 'Block nach unten', () => move(s.blocks, i, 1), { disabled: i === s.blocks.length - 1 }),
      tool(b.visible ? 'eye' : 'eyeOff', b.visible ? 'Block ausblenden' : 'Block einblenden', () => { b.visible = !b.visible; renderMain(); }),
      tool('pencil', 'Block umbenennen', () => { state.renamingBlockId = renaming ? null : b.id; renderMain(); }),
      tool('trash', 'Block löschen', () => confirmDialog('Block löschen', 'Block „' + b.title + '“ mit allen Inhalten löschen?', 'Löschen', () => {
        s.blocks.splice(s.blocks.indexOf(b), 1);
        renderMain();
      }), { cls: 'danger' })));
  }
  el.append(head, h('div', { class: 'block-body' }, body));
  return el;
}

function valueWithCopy(text, href) {
  const link = href && h('a', { href, onclick: (e) => { e.preventDefault(); openUrl(href); } }, text);
  return h('span', { class: 'val' }, link || text, copyBtn(text));
}

const VIEWS = {
  fields(b) {
    const rows = b.fields.filter((f) => f.value.trim());
    if (!rows.length) return null;
    return h('div', { class: 'kv' }, rows.map((f) => [h('div', { class: 'k' }, f.label), h('div', {}, valueWithCopy(f.value))]));
  },

  contacts(b) {
    const list = b.contacts.filter((c) => ['name', 'role', 'phone', 'mobile', 'email', 'note'].some((k) => c[k].trim()));
    if (!list.length) return null;
    const line = (lbl, v, href) => v.trim() && h('div', { class: 'line' }, h('span', { class: 'lbl' }, lbl), valueWithCopy(v, href));
    return h('div', { class: 'cards' }, list.map((c) => h('div', { class: 'card' },
      c.name.trim() && h('div', { class: 'card-head' }, h('strong', {}, c.name)),
      c.role.trim() && h('div', { class: 'role' }, c.role),
      line('Telefon', c.phone), line('Mobil', c.mobile), line('E-Mail', c.email, 'mailto:' + c.email.trim()),
      c.note.trim() && h('div', { class: 'note' }, c.note))));
  },

  addresses(b) {
    const list = b.addresses.filter((a) => addressLines({ ...a, country: '' }).length || a.phone.trim() || a.email.trim() || a.note.trim());
    if (!list.length) return null;
    const line = (lbl, v, href) => v.trim() && h('div', { class: 'line' }, h('span', { class: 'lbl' }, lbl), valueWithCopy(v, href));
    return h('div', { class: 'cards' }, list.map((a) => h('div', { class: 'card' },
      h('div', { class: 'card-head' },
        a.isDefault && h('span', { class: 'star', title: 'Standardadresse' }, icon('star', true)),
        h('strong', {}, a.label || 'Adresse'),
        tool('copy', 'Adresse kopieren', () => copyText(addressLines(a).join('\n')), { cls: 'copy' })),
      h('div', { class: 'addr-text' }, addressLines(a).join('\n')),
      line('Telefon', a.phone), line('E-Mail', a.email, 'mailto:' + a.email.trim()),
      a.note.trim() && h('div', { class: 'note' }, a.note))));
  },

  links(b) {
    const groups = b.groups.map((g) => ({ g, links: g.links.filter((l) => l.url.trim()) })).filter((x) => x.links.length);
    if (!groups.length) return null;
    return groups.map(({ g, links }) => h('div', { class: 'link-group' },
      g.label.trim() && h('h4', {}, g.label),
      h('div', { class: 'link-list' }, links.map((l) => h('a', {
        class: 'link-chip', href: normalizeUrl(l.url) || '#', title: l.url,
        onclick: (e) => { e.preventDefault(); openUrl(l.url); },
      }, l.title.trim() || l.url, icon('ext'))))));
  },

  // Notizen sind immer direkt editierbar und werden auch leer angezeigt.
  notes(b) {
    return h('textarea', {
      class: 'notes-area', placeholder: 'Notizen …', value: b.text,
      oninput: (e) => { b.text = e.target.value; autoGrow(e.target); },
    });
  },
};

const EDITORS = {
  fields(b) {
    return [
      b.fields.map((f, i) => h('div', { class: 'edit-row' },
        bind(f, 'label', 'Bezeichnung', { cls: 'w-label' }), bind(f, 'value', 'Wert'), rowTools(b.fields, i, 'Feld'))),
      h('button', { class: 'btn small add-row', onclick: () => { b.fields.push(newField()); renderMain(); } }, '+ Feld hinzufügen'),
    ];
  },

  contacts(b) {
    return [
      h('div', { class: 'cards' }, b.contacts.map((c, i) => h('div', { class: 'card edit' },
        h('div', { class: 'card-head' }, h('strong', {}, 'Kontakt ' + (i + 1)), rowTools(b.contacts, i, 'Ansprechpartner')),
        h('div', { class: 'form-grid' },
          bind(c, 'name', 'Name'), bind(c, 'role', 'Funktion'),
          bind(c, 'phone', 'Telefon'), bind(c, 'mobile', 'Mobil'),
          bind(c, 'email', 'E-Mail', { cls: 'full' }), bind(c, 'note', 'Notiz', { cls: 'full' }))))),
      h('button', { class: 'btn small add-row', onclick: () => { b.contacts.push(newContact()); renderMain(); } }, '+ Ansprechpartner hinzufügen'),
    ];
  },

  addresses(b) {
    // Genau eine Standardadresse: bei nur einer Adresse automatisch, sonst die erste, falls keine markiert ist.
    const fixDefault = () => { if (b.addresses.length && !b.addresses.some((a) => a.isDefault)) b.addresses[0].isDefault = true; };
    fixDefault();
    return [
      h('div', { class: 'cards' }, b.addresses.map((a, i) => h('div', { class: 'card edit' },
        h('div', { class: 'card-head' },
          tool('star', a.isDefault ? 'Standardadresse' : 'Als Standard markieren', () => {
            b.addresses.forEach((x) => { x.isDefault = x === a; });
            renderMain();
          }, { cls: a.isDefault ? 'on' : '', filled: a.isDefault }),
          bind(a, 'label', 'Bezeichnung, z. B. Retourenadresse'),
          rowTools(b.addresses, i, 'Adresse', fixDefault)),
        h('div', { class: 'form-grid' },
          bind(a, 'company', 'Firma', { cls: 'full' }), bind(a, 'addition', 'Zusatz', { cls: 'full' }),
          bind(a, 'street', 'Straße und Hausnummer', { cls: 'full' }),
          h('div', { class: 'full zip-city' }, bind(a, 'zip', 'PLZ'), bind(a, 'city', 'Ort')),
          bind(a, 'country', 'Land'), bind(a, 'contactName', 'Ansprechpartner'),
          bind(a, 'phone', 'Telefon'), bind(a, 'email', 'E-Mail'),
          bind(a, 'note', 'Notiz', { cls: 'full' }))))),
      h('button', { class: 'btn small add-row', onclick: () => { b.addresses.push(newAddress({ isDefault: !b.addresses.length })); renderMain(); } }, '+ Adresse hinzufügen'),
    ];
  },

  links(b) {
    return [
      b.groups.map((g, gi) => h('div', { class: 'link-group edit' },
        h('div', { class: 'edit-row' }, bind(g, 'label', 'Beschriftung der Gruppe, z. B. B2B'), rowTools(b.groups, gi, 'Gruppe')),
        g.links.map((l, li) => h('div', { class: 'edit-row' },
          bind(l, 'title', 'Beschriftung', { cls: 'w-label' }), bind(l, 'url', 'Adresse, z. B. portal.example.de'), rowTools(g.links, li, 'Link'))),
        h('button', { class: 'btn small', onclick: () => { g.links.push(newLink()); renderMain(); } }, '+ Link'))),
      h('button', { class: 'btn small add-row', onclick: () => { b.groups.push(newGroup()); renderMain(); } }, '+ Linkgruppe hinzufügen'),
    ];
  },

  notes(b) { return VIEWS.notes(b); },
};


function addSupplierDialog() {
  if (!state.ready) return;
  const d = { name: '' };
  const err = h('span', { class: 'error' });
  const create = () => {
    const name = d.name.trim();
    if (!name) { err.textContent = 'Bitte einen Namen eingeben.'; return; }
    if (state.suppliers.some((s) => s.name.trim().toLowerCase() === name.toLowerCase())) { err.textContent = 'Diesen Hersteller gibt es schon.'; return; }
    const s = newSupplier(name);
    state.suppliers.push(s);
    closeModal();
    state.activeId = s.id;
    state.editMode = true;
    state.docsPanel = false;
    render();
  };
  showModal({
    title: 'Hersteller anlegen',
    body: field('Name', bind(d, 'name', 'z. B. Beispiel GmbH', { focus: '1', onkeydown: (e) => { if (e.key === 'Enter') create(); } }), { required: true }),
    foot: [err, h('button', { class: 'btn', onclick: closeModal }, 'Abbrechen'), h('button', { class: 'btn primary', onclick: create }, 'Anlegen')],
  });
}

// Abschnitte im Tab Einstellungen: Allgemeines (Datenordner, Programm) und die Einstellungen der Hersteller.
const settingsMock = (t) => () => toast('In der Vorschau ohne Funktion: ' + t);

async function settingsGeneral() {
  const status = api ? await api.grundgeruest_status() : null;
  return h('div', { class: 'stack' },
    h('div', { class: 'section-bar' }, 'Datenordner'),
    h('div', { class: 'row' }, h('span', { class: 'path grow' }, api ? (status.dataDir || '') : 'C:\\Users\\Thorben\\OneDrive\\SOS-Dashboard'),
      h('button', { class: 'btn small', onclick: api ? async () => { await saveNow(); await chooseFolder(); openSettings('allgemein'); } : settingsMock('Ordner wählen') }, 'Anderen Ordner wählen')),
    h('div', { class: 'section-bar' }, 'Programm'),
    h('div', { class: 'row' },
      h('button', { class: 'btn', onclick: api ? checkUpdate : settingsMock('Nach Aktualisierung suchen') }, 'Nach Aktualisierung suchen'),
      h('span', { class: 'lab', style: 'margin:0' }, 'Version: ' + (api ? (status.version || 'Entwicklung') : 'Vorschau'))));
}

async function settingsSuppliers() {
  if (!state.ready) return h('p', { class: 'muted' }, 'Die Herstellerdaten sind noch nicht geladen.');
  const c = state.company;
  const status = api ? await api.hersteller_status() : null;
  const restore = () => confirmDialog('Backup zurückspielen', 'Das Backup vom ' + fmtDate(status.lastBackup) + ' laden? Der jetzige Stand wird als Datei „…-ersetzt-…“ im Datenordner aufbewahrt.', 'Backup laden',
    async () => { await saveNow(); applyLoadResult(await api.hersteller_backup_laden()); openSettings('hersteller'); });
  return h('div', { class: 'stack' },
    h('div', { class: 'section-bar' }, 'Import und Backup'),
    h('div', { class: 'row' },
      h('button', { class: 'btn', onclick: importCsv }, 'Hersteller aus CSV importieren'),
      h('button', { class: 'btn', disabled: api && !status.lastBackup, onclick: api ? restore : settingsMock('Backup zurückspielen') }, 'Backup zurückspielen'),
      h('span', { class: 'lab', style: 'margin:0' }, 'Letztes Backup: ' + (api ? (status.lastBackup ? fmtDate(status.lastBackup) : 'noch keines') : 'heute'))),
    h('div', { class: 'section-bar' }, 'Absenderdaten für Dokumente'),
    h('div', { class: 'frm' },
      field('Firma', bind(c, 'name'), { cls: 'span2' }), field('Straße', bind(c, 'street'), { cls: 'span2' }),
      field('PLZ', bind(c, 'zip')), field('Ort', bind(c, 'city')), field('Land', bind(c, 'country'), { cls: 'span2' }),
      field('Telefon', bind(c, 'phone'), { cls: 'span2' }), field('E-Mail', bind(c, 'email'), { cls: 'span2' }),
      field('Geschäftsführer', bind(c, 'managingDirector'), { cls: 'span2' }), field('USt-IdNr.', bind(c, 'vatId'), { cls: 'span2' }),
      field('Handelsregister', bind(c, 'register'), { cls: 'span4' }),
      h('label', { class: 'check span4' }, h('input', { type: 'checkbox', checked: c.showFooter, onchange: (e) => { c.showFooter = e.target.checked; } }), 'Firmendaten im Fuß anzeigen')));
}

registerSettingsSection({ id: 'allgemein', title: 'Allgemein', build: settingsGeneral });
registerSettingsSection({ id: 'hersteller', title: 'Hersteller', build: settingsSuppliers });

// CSV-Import: Datei wählen, Vorschau zeigen, erst nach Bestätigung importieren.
async function importCsv() {
  if (!api) {
    csvPreviewDialog({ file: 'beispiel-import.csv', new: ['Muster Ski GmbH', 'Beispiel Outdoor AG', 'Tennis Vorlage KG'], duplicates: ['Wilson'], errors: [] });
    return;
  }
  await saveNow();
  if (contentJson() !== lastSaved) { errorDialog('Import nicht möglich', 'Die Daten konnten nicht gespeichert werden. Bitte zuerst das Speicherproblem lösen.'); return; }
  const res = await apiCall(api.hersteller_csv_importieren());
  if (res.ok) csvPreviewDialog(res);
}

function csvPreviewDialog(p) {
  const names = (list) => list.slice(0, 12).join(', ') + (list.length > 12 ? ' … und ' + (list.length - 12) + ' weitere' : '');
  const line = (n, one, many, detail) => h('div', {}, h('strong', {}, n), ' ' + (n === 1 ? one : many) + (detail ? ': ' + detail : ''));
  const doImport = async () => {
    if (!api) { closeModal(); toast('In der Vorschau wird nichts importiert.'); return; }
    const res = await apiCall(api.hersteller_csv_bestaetigen());
    if (!res.ok) { if (res.error === 'conflict') conflictDialog(); return; }
    state.suppliers.push(...res.suppliers);
    state.meta.revision = res.revision;
    lastSaved = contentJson();
    lastSuppliers = supplierSnapshot();
    closeModal();
    render();
    toast(res.suppliers.length === 1 ? '1 Hersteller importiert.' : res.suppliers.length + ' Hersteller importiert.');
  };
  showModal({
    title: 'Hersteller aus CSV importieren', size: 'medium',
    body: h('div', { class: 'stack' },
      h('div', { class: 'row' }, h('span', { class: 'path grow' }, p.file), h('button', { class: 'btn small', onclick: importCsv }, 'Andere Datei wählen')),
      h('div', { class: 'preview-box' },
        line(p.new.length, 'neuer Hersteller', 'neue Hersteller', names(p.new)),
        line(p.duplicates.length, 'Duplikat wird übersprungen', 'Duplikate werden übersprungen', names(p.duplicates)),
        line(p.errors.length, 'Zeile mit Fehler', 'Zeilen mit Fehlern', names(p.errors.map((e) => 'Zeile ' + e.line + ' (' + e.message + ')')))),
      h('p', { class: 'lab' }, 'Pflichtspalte: Name. Optional: Kundennr, B2B, Reklamation, Medien. Bestehende Hersteller werden nie überschrieben.')),
    foot: [h('span', { class: 'spacer' }), h('button', { class: 'btn', onclick: closeModal }, 'Abbrechen'),
      h('button', { class: 'btn primary', disabled: !p.new.length, onclick: doImport },
        p.new.length === 1 ? '1 Hersteller importieren' : p.new.length + ' Hersteller importieren')],
  });
}

/* ---------- Dokument-Dialoge ---------- */

const newPosition = (reason) => ({ article: '', articleNo: '', size: '', color: '', qty: 1, reason: reason || 'Retoure' });
const newArticle = () => ({ article: '', articleNo: '', size: '', color: '', purchaseDate: '', receiptNo: '' });

function openDocDialog(type, copyFrom) {
  const s = activeSupplier();
  if (!s) return;
  state.menu = null;
  renderMain();
  const addrs = s.blocks.filter((b) => b.type === 'addresses').flatMap((b) => b.addresses);
  let data;
  if (copyFrom) {
    data = clone(copyFrom.data);
    data.date = todayIso();
    if (data.addressId !== '__custom__' && !addrs.some((a) => a.id === data.addressId)) data.addressId = '';
  } else {
    data = { date: todayIso(), addressId: '', customerNo: customerNoOf(s), contactId: '' };
    if (type === 'RS') Object.assign(data, { rma: '', shipping: '', packages: 1, reasonGeneral: 'Retoure', remark: '', positions: [newPosition()] });
    else Object.assign(data, { reference: '', articles: [newArticle()], description: '', wanted: [], accessories: '', printProcessing: false });
  }
  if (!data.addressId) {
    // Standardadresse vorauswählen.
    const def = addrs.find((a) => a.isDefault) || addrs[0];
    data.addressId = def ? def.id : '';
  }
  state.draft = { type, supplierId: s.id, data, error: '', copyOf: copyFrom ? copyFrom.number : null };
  renderDocDialog();
}

function renderDocDialog(focusSel) {
  const draft = state.draft;
  const s = state.suppliers.find((x) => x.id === draft.supplierId);
  const d = draft.data;
  const isRS = draft.type === 'RS';
  const addrs = s.blocks.filter((b) => b.type === 'addresses').flatMap((b) => b.addresses);
  const contacts = s.blocks.filter((b) => b.type === 'contacts').flatMap((b) => b.contacts).filter((c) => c.name.trim());
  const sel = (obj, key, options, onPick) => h('select', { value: obj[key], onchange: (e) => { obj[key] = e.target.value; if (onPick) onPick(); } },
    options.map(([v, t]) => h('option', { value: v }, t)));
  const CUSTOM = '__custom__';
  const customAddr = d.addressId === CUSTOM ? (d.customAddress = d.customAddress || { company: '', addition: '', street: '', zip: '', city: '', country: 'Deutschland' }) : null;
  const saveCheck = (key, text) => h('label', { class: 'check span2' },
    h('input', { type: 'checkbox', checked: !!d[key], onchange: (e) => { d[key] = e.target.checked; } }), text);
  const again = (focus) => { const sc = document.querySelector('#modal-root .modal-body').scrollTop; renderDocDialog(focus); document.querySelector('#modal-root .modal-body').scrollTop = sc; };

  const common = h('div', { class: 'frm' },
    field('Empfängeradresse', sel(d, 'addressId', [
      ...(addrs.length
        ? addrs.map((a) => [a.id, (a.label || 'Adresse') + (a.isDefault ? ' ★' : '') + (a.city ? ' – ' + a.city : '')])
        : [['', 'Keine Adresse hinterlegt']]),
      [CUSTOM, 'Andere Adresse eingeben …']], () => again()), { cls: 'span2', required: true }),
    customAddr ? [
      field('Firma', bind(customAddr, 'company', ''), { cls: 'span2', required: true }),
      field('Zusatz', bind(customAddr, 'addition', 'optional'), { cls: 'span2' }),
      field('Straße', bind(customAddr, 'street', ''), { cls: 'span2', required: true }),
      field('PLZ', bind(customAddr, 'zip', '')), field('Ort', bind(customAddr, 'city', ''), { required: true }),
      field('Land', bind(customAddr, 'country', ''), { cls: 'span2' }),
      saveCheck('saveCustomAddress', 'Diese Adresse auch beim Hersteller speichern'),
    ] : null,
    field('Ansprechpartner', sel(d, 'contactId', [['', 'keiner'], ...contacts.map((c) => [c.id, c.name]), [CUSTOM, 'Anderen Ansprechpartner eingeben …']], () => again()), { cls: 'span2' }),
    d.contactId === CUSTOM ? [
      field('Name', bind(d, 'customContactName', ''), { cls: 'span2', required: true }),
      saveCheck('saveCustomContact', 'Diesen Ansprechpartner auch beim Hersteller speichern'),
    ] : null,
    field('Datum', bind(d, 'date', '', { type: 'date' })),
    field('Unsere Kundennr', bind(d, 'customerNo', '')),
    isRS ? field('RMA-/Retourennr. des Herstellers', bind(d, 'rma', 'optional'), { cls: 'span2' })
      : field('Referenz/RMA-Nr', bind(d, 'reference', 'optional'), { cls: 'span2' }));

  let body;
  if (isRS) {
    const lastCellTab = (e, i) => {
      if (e.key === 'Tab' && !e.shiftKey && i === d.positions.length - 1) {
        e.preventDefault();
        d.positions.push(newPosition(d.reasonGeneral));
        again('tr[data-row="' + (i + 1) + '"] input');
      }
    };
    body = [
      h('div', { class: 'section-bar' }, 'Empfänger und Referenz'), common,
      h('div', { class: 'frm', style: 'margin-top:10px' },
        field('Versandart', bind(d, 'shipping', 'optional, z. B. DPD'), { cls: 'span2' }),
        field('Anzahl Pakete', bind(d, 'packages', '', { type: 'number', min: '1' })),
        field('Grund allgemein', sel(d, 'reasonGeneral', RETURN_REASONS.map((r) => [r, r])))),
      h('div', { class: 'section-bar' }, 'Positionen'),
      h('table', { class: 'pos-table' },
        h('thead', {}, h('tr', {}, ['Pos.', 'Artikel *', 'Artikelnr.', 'Größe', 'Farbe', 'Menge', 'Grund', ''].map((t) => h('th', {}, t)))),
        h('tbody', {}, d.positions.map((p, i) => h('tr', { 'data-row': i },
          h('td', { class: 'num' }, i + 1),
          h('td', {}, bind(p, 'article', 'Artikel')),
          h('td', {}, bind(p, 'articleNo', '')), h('td', {}, bind(p, 'size', '')), h('td', {}, bind(p, 'color', '')),
          h('td', { class: 'qty' }, bind(p, 'qty', '', { type: 'number', min: '1' })),
          h('td', {}, (() => { const x = sel(p, 'reason', RETURN_REASONS.map((r) => [r, r])); x.addEventListener('keydown', (e) => lastCellTab(e, i)); return x; })()),
          h('td', { class: 'del' }, tool('trash', 'Position löschen', () => { d.positions.splice(i, 1); again(); }, { cls: 'danger', disabled: d.positions.length === 1, tab: false })))))),
      h('button', { class: 'btn small add-row', onclick: () => { d.positions.push(newPosition(d.reasonGeneral)); again('tr[data-row="' + (d.positions.length - 1) + '"] input'); } }, '+ Position hinzufügen'),
      h('div', { class: 'section-bar' }, 'Bemerkung'),
      bind(d, 'remark', 'optional', { multiline: true, rows: '2' }),
    ];
  } else {
    body = [
      h('div', { class: 'section-bar' }, 'Hersteller'), common,
      d.articles.map((a, i) => [
        h('div', { class: 'section-bar' + (i ? ' sub' : '') }, i
          ? [h('span', {}, 'Artikel ' + (i + 1)), tool('trash', 'Artikel entfernen', () => { d.articles.splice(i, 1); again(); }, { cls: 'danger' })]
          : 'Artikel'),
        h('div', { class: 'frm', 'data-art': i },
          field('Artikel', bind(a, 'article', ''), { cls: 'span2', required: true }),
          field('Artikelnr.', bind(a, 'articleNo', 'optional')), field('Größe', bind(a, 'size', '')),
          field('Farbe', bind(a, 'color', '')), field('Kaufdatum', bind(a, 'purchaseDate', '', { type: 'date' })),
          field('Beleg-Nr.', bind(a, 'receiptNo', ''), { cls: 'span2' })),
      ]),
      h('button', { class: 'btn small add-row', onclick: () => { d.articles.push(newArticle()); again('[data-art="' + (d.articles.length - 1) + '"] input'); } }, '+ Weiteren Artikel hinzufügen'),
      h('div', { class: 'section-bar' }, 'Reklamation'),
      h('div', { class: 'stack' },
        field('Fehlerbeschreibung', bind(d, 'description', '', { multiline: true, rows: '4' }), { required: true }),
        h('div', {}, h('span', { class: 'lab' }, 'Gewünscht'), h('div', { class: 'checks' }, WANTED.map((w) => h('label', { class: 'check' },
          h('input', { type: 'checkbox', checked: d.wanted.includes(w), onchange: (e) => { d.wanted = e.target.checked ? [...d.wanted, w] : d.wanted.filter((x) => x !== w); } }), w)))),
        field('Zubehör dabei', bind(d, 'accessories', 'z. B. Bindung, Karton, Ladekabel')),
        h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: d.printProcessing, onchange: (e) => { d.printProcessing = e.target.checked; } }),
          'Bearbeitungsfelder mit ausdrucken (Gesendet am, Rückmeldung, Ergebnis)')),
    ];
  }

  showModal({
    title: DOC_TYPES[draft.type].name + ' für ' + s.name + (draft.copyOf ? ' (Kopie von ' + draft.copyOf + ')' : ''),
    size: 'wide', body,
    foot: [draft.error ? h('span', { class: 'error' }, draft.error)
      : h('span', { class: 'hint' }, draft.busy ? 'PDF wird erzeugt …' : 'Die Nummer wird erst beim Erzeugen vergeben.'),
      h('button', { class: 'btn', onclick: closeModal }, 'Abbrechen'),
      h('button', { class: 'btn primary', disabled: draft.busy, onclick: createDocument }, 'PDF erzeugen')],
  });
  if (focusSel) { const f = document.querySelector('#modal-root ' + focusSel); if (f) f.focus(); }
}

async function createDocument() {
  const draft = state.draft;
  if (!draft || draft.busy) return;
  const d = draft.data;
  const s = state.suppliers.find((x) => x.id === draft.supplierId);
  const CUSTOM = '__custom__';
  const custom = d.addressId === CUSTOM ? d.customAddress || {} : null;
  const addr = custom ? ((custom.company || '').trim() && (custom.street || '').trim() && (custom.city || '').trim() ? custom : null)
    : s.blocks.filter((b) => b.type === 'addresses').flatMap((b) => b.addresses).find((a) => a.id === d.addressId);
  const missing = [];
  if (!addr) missing.push(custom ? 'Firma, Straße und Ort der anderen Adresse' : 'Empfängeradresse');
  if (d.contactId === CUSTOM && !(d.customContactName || '').trim()) missing.push('Name des Ansprechpartners');
  if (draft.type === 'RS') {
    d.positions = d.positions.filter((p, i) => p.article.trim() || i === 0);
    if (!d.positions.some((p) => p.article.trim())) missing.push('mindestens eine Position mit Artikel');
  } else {
    if (!d.articles.some((a) => a.article.trim())) missing.push('Artikel');
    if (!d.description.trim()) missing.push('Fehlerbeschreibung');
  }
  if (missing.length) { draft.error = 'Bitte ausfüllen: ' + missing.join(', ') + '.'; renderDocDialog(); return; }

  // Auf Wunsch die einmalige Adresse oder Person dauerhaft beim Hersteller ablegen.
  if (custom && d.saveCustomAddress) {
    let blk = s.blocks.find((b) => b.type === 'addresses');
    if (!blk) { blk = newBlock('addresses', 'Adressen'); s.blocks.push(blk); }
    const na = newAddress({ label: 'Weitere Adresse', isDefault: !blk.addresses.length, ...Object.fromEntries(['company', 'addition', 'street', 'zip', 'city', 'country'].map((k) => [k, (custom[k] || '').trim()])) });
    blk.addresses.push(na);
    d.addressId = na.id; delete d.customAddress;
  }
  if (d.contactId === CUSTOM && d.saveCustomContact) {
    let blk = s.blocks.find((b) => b.type === 'contacts');
    if (!blk) { blk = newBlock('contacts', 'Ansprechpartner'); s.blocks.push(blk); }
    const nc = newContact({ name: d.customContactName.trim() });
    blk.contacts.push(nc);
    d.contactId = nc.id; delete d.customContactName;
  }
  delete d.saveCustomAddress; delete d.saveCustomContact;

  if (api) {
    // Erst den eigenen Stand sichern, dann vergibt Python die Nummer, schreibt das PDF und speichert den Eintrag.
    draft.busy = true;
    draft.error = '';
    renderDocDialog();
    const fail = (msg) => { draft.busy = false; draft.error = msg; if (state.draft === draft) renderDocDialog(); };
    await saveNow();
    if (contentJson() !== lastSaved) { fail('Die Daten konnten nicht gespeichert werden. Bitte zuerst das Speicherproblem lösen.'); return; }
    let res;
    try { res = await api.hersteller_dokument_erzeugen(draft.type, { supplierId: s.id, data: d }); } catch (e) { res = { ok: false, message: String(e) }; }
    if (!res.ok) {
      if (res.error === 'conflict') { draft.busy = false; conflictDialog(); } else fail(res.message || 'Das PDF konnte nicht erzeugt werden.');
      return;
    }
    state.documents.push(res.document);
    state.counters = res.counters;
    state.meta.revision = res.revision;
    lastSaved = contentJson();
    lastSuppliers = supplierSnapshot();
    closeModal();
    render();
    createdDialog(res.document, res.opened);
    return;
  }

  const year = (d.date || todayIso()).slice(0, 4);
  const n = (state.counters[draft.type][year] || 0) + 1;
  state.counters[draft.type][year] = n;
  const number = draft.type + '-' + year + '-' + String(n).padStart(4, '0');
  const safe = (t) => t.replace(/[^\wäöüÄÖÜß .-]/g, '').trim();
  state.documents.push({
    id: uid(), supplierId: s.id, type: draft.type, number, createdAt: new Date().toISOString().slice(0, 19),
    file: 'dokumente/' + safe(s.name) + '/' + number + '_' + DOC_TYPES[draft.type].name + '.pdf',
    addressSnapshot: clone(addr), data: clone(d),
  });
  closeModal();
  state.docsPanel = true;
  render();
  toast(number + ' angelegt. In der Vorschau wird kein PDF erzeugt.');
}

// Ruft eine API-Methode auf und zeigt eine Fehlermeldung, falls sie scheitert.
// Aktualisierung: Der Build legt die neue Version in den Datenordner, das Programm holt sie sich von dort.
async function checkUpdate() {
  const res = await apiCall(api.grundgeruest_update_pruefen());
  if (!res.ok) return;
  if (res.canUpdate === false) {
    errorDialog('Aktualisieren nicht möglich', 'Aktualisieren geht nur, wenn das Programm über start.command (Mac) bzw. start.bat (Windows) aus dem Quelltext läuft und der Programmordner beschreibbar ist.');
    return;
  }
  if (!res.available) {
    errorDialog('Keine Aktualisierung', 'Das Programm ist aktuell (Version ' + res.current + ').');
    return;
  }
  confirmDialog('Aktualisierung installieren', 'Neue Version ' + res.version + (res.note ? ' („' + res.note + '“)' : '') + ' ist verfügbar (installiert: ' + res.current + '). Das Programm schließt sich kurz und startet dann neu.', 'Jetzt aktualisieren', installUpdate);
}

async function installUpdate() {
  await saveNow();
  showModal({ title: 'Aktualisierung', body: h('p', {}, 'Die neue Version wird geladen, geprüft und installiert …'), foot: [] });
  const res = await apiCall(api.grundgeruest_update_installieren());
  if (res.ok) showModal({ title: 'Aktualisierung', body: h('p', {}, 'Version ' + res.version + ' ist installiert. Das Programm startet jetzt neu.'), foot: [] });
  else closeModal();
}

// Beim Start einmal still nachsehen und nur einen Hinweis zeigen.
async function hintUpdate() {
  try {
    const res = await api.grundgeruest_update_pruefen();
    if (res.ok && res.available) toast('Neue Version verfügbar: Einstellungen → „Nach Aktualisierung suchen“', 8000);
  } catch (e) { /* kein Hinweis */ }
}


function createdDialog(doc, opened) {
  showModal({
    title: doc.number + ' wurde erzeugt', size: 'medium',
    body: h('div', { class: 'stack' },
      h('p', {}, opened ? 'Das PDF wurde im Archiv gespeichert und geöffnet.' : 'Das PDF wurde im Archiv gespeichert, konnte aber nicht automatisch geöffnet werden.'),
      h('p', { class: 'path' }, doc.file)),
    foot: [h('span', { class: 'spacer' }),
      h('button', { class: 'btn', onclick: () => apiCall(api.hersteller_dokument_oeffnen(doc.id)) }, 'PDF öffnen'),
      h('button', { class: 'btn', onclick: () => apiCall(api.hersteller_dokumente_ordner_oeffnen(doc.supplierId, doc.id)) }, 'Ordner öffnen'),
      h('button', { class: 'btn primary', 'data-focus': '1', onclick: closeModal }, 'Schließen')],
  });
}

/* ---------- Dokumente-Panel ---------- */

function renderPanel() {
  const root = document.getElementById('panel-root');
  const s = activeSupplier();
  if (!state.docsPanel || !s) { root.replaceChildren(); return; }
  const close = () => { state.docsPanel = false; renderPanel(); };
  const docs = docsOf(s.id).slice().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  root.replaceChildren(
    h('div', { class: 'panel-backdrop', onclick: close }),
    h('aside', { class: 'panel' },
      h('div', { class: 'panel-head' }, h('h3', {}, 'Dokumente – ' + s.name), tool('x', 'Schließen', close)),
      h('div', { class: 'panel-body' }, docs.length ? docs.map((doc) => h('div', { class: 'doc-item' },
        h('div', { class: 'no' }, doc.number),
        h('div', { class: 'meta' }, DOC_TYPES[doc.type].name + ' · ' + fmtDate(doc.createdAt) + ' · an ' + (doc.addressSnapshot.label || 'Adresse')),
        h('div', { class: 'row' },
          h('button', { class: 'btn small', onclick: () => (api ? apiCall(api.hersteller_dokument_oeffnen(doc.id)) : toast('In der Vorschau ohne Funktion: ' + doc.file)) }, 'Öffnen'),
          h('button', { class: 'btn small', title: 'Ordner mit markierter Datei zeigen', onclick: () => (api ? apiCall(api.hersteller_dokumente_ordner_oeffnen(s.id, doc.id)) : toast('In der Vorschau ohne Funktion: Ordner öffnen')) }, 'Ordner'),
          h('button', { class: 'btn small', onclick: () => { state.docsPanel = false; renderPanel(); openDocDialog(doc.type, doc); } }, 'Als Kopie weiterverwenden'))))
        : h('p', { class: 'block-empty' }, 'Für diesen Hersteller wurden noch keine Dokumente erzeugt.')),
      h('div', { class: 'panel-foot' }, h('button', { class: 'btn', onclick: () => (api ? apiCall(api.hersteller_dokumente_ordner_oeffnen(s.id)) : toast('In der Vorschau ohne Funktion: Ordner öffnen')) }, 'Ordner öffnen'))));
}

/* ---------- Laden, Speichern, Fehlerfälle ---------- */

let saveTimer = null;
let saving = false;
let lastSaved = '';
let lastSuppliers = new Map();
let saveErrorShown = false;

function setStatus(text, isError, detail) {
  const el = document.getElementById('save-status');
  el.textContent = text;
  el.title = detail || '';
  el.classList.toggle('error', !!isError);
}

function buildData() {
  return {
    schemaVersion: state.meta.schemaVersion, revision: state.meta.revision, blockTemplate: state.meta.blockTemplate,
    company: state.company, counters: state.counters, documents: state.documents, suppliers: state.suppliers,
  };
}

function contentJson() {
  return JSON.stringify({ ...buildData(), revision: 0 });
}

const supplierSnapshot = () => new Map(state.suppliers.map((s) => [s.id, JSON.stringify(s)]));

// Automatisches Speichern: 500 ms nach der letzten Änderung, nur wenn sich wirklich etwas geändert hat.
function scheduleSave() {
  if (!api || !state.ready) return;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 500);
}

// Speichervorgänge laufen nacheinander: Wer saveNow() abwartet, hat danach den aktuellen Stand auf der Platte.
let saveQueue = Promise.resolve();
function saveNow() {
  saveQueue = saveQueue.then(doSave, doSave);
  return saveQueue;
}

async function doSave() {
  clearTimeout(saveTimer);
  if (!api || !state.ready) return;
  if (contentJson() === lastSaved) return;
  const now = nowIso();
  for (const s of state.suppliers) if (lastSuppliers.get(s.id) !== JSON.stringify(s)) s.updatedAt = now;
  const json = contentJson();
  const suppliers = supplierSnapshot();
  saving = true;
  let res;
  try { res = await api.hersteller_speichern(buildData()); } catch (e) { res = { ok: false, error: 'io', message: String(e) }; }
  saving = false;
  if (res.ok) {
    state.meta.revision = res.revision;
    lastSaved = json;
    lastSuppliers = suppliers;
    setStatus('Gespeichert');
    saveErrorShown = false;
    if (contentJson() !== lastSaved) scheduleSave();
  } else if (res.error === 'conflict') {
    setStatus('Nicht gespeichert: Konflikt', true, res.message);
    conflictDialog();
  } else {
    setStatus('Speichern fehlgeschlagen', true, res.message);
    setTimeout(scheduleSave, 5000); // später noch einmal versuchen
    // Einmal deutlich melden, aber keinen offenen Dialog verdrängen.
    if (!saveErrorShown && !document.getElementById('modal-root').firstChild) {
      saveErrorShown = true;
      errorDialog('Speichern fehlgeschlagen', (res.message || 'Die Daten konnten nicht gespeichert werden.') + ' Deine Änderungen bleiben im Fenster erhalten; es wird automatisch erneut versucht.',
        h('button', { class: 'btn', onclick: () => { closeModal(); chooseFolder(); } }, 'Anderen Ordner wählen'));
    }
  }
}

function applyLoadResult(res) {
  if (!res || res.error === 'cancelled') return;
  closeModal();
  state.editMode = false;
  state.docsPanel = false;
  state.menu = null;
  if (res.ok) {
    const d = res.data;
    state.meta = { schemaVersion: d.schemaVersion, revision: d.revision, blockTemplate: d.blockTemplate };
    state.suppliers = d.suppliers;
    state.company = d.company;
    state.counters = d.counters;
    state.documents = d.documents;
    state.dataDir = res.dataDir;
    if (!activeSupplier()) state.activeId = null;
    state.problem = null;
    state.ready = true;
    lastSaved = contentJson();
    lastSuppliers = supplierSnapshot();
    setStatus('Gespeichert');
  } else {
    state.ready = false;
    state.problem = res;
    state.suppliers = [];
    state.activeId = null;
    setStatus(res.error === 'no_folder' ? '' : 'Daten nicht geladen', res.error !== 'no_folder');
  }
  render();
}

async function chooseFolder() {
  const res = await api.grundgeruest_datenordner_waehlen();
  if (res.ok) applyLoadResult(await api.hersteller_datei_anlegen());  // in einem frisch gewählten Ordner darf eine Datei entstehen
}
async function reload() { applyLoadResult(await api.hersteller_laden()); }

function problemScreen(p) {
  const btn = (label, fn, primary) => h('button', { class: 'btn' + (primary ? ' primary' : ''), onclick: fn }, label);
  const retry = btn('Erneut versuchen', reload);
  const other = (primary) => btn('Anderen Ordner wählen', chooseFolder, primary);
  const path = p.dataDir && h('p', { class: 'path' }, p.dataDir);
  let title, text, buttons;
  if (p.error === 'no_folder') {
    title = 'Willkommen im SOS Dashboard';
    text = 'Bitte wähle den Ordner, in dem die Daten liegen sollen. Liegt er in einem Cloud-Ordner (z. B. OneDrive), sind die Daten auf allen deinen Rechnern gleich. Gibt es dort schon eine Datendatei, wird sie geladen.';
    buttons = [btn('Datenordner wählen', chooseFolder, true)];
  } else if (p.error === 'folder_unreachable') {
    title = 'Der Datenordner ist nicht erreichbar';
    text = 'Der Ordner wurde nicht gefunden. Vielleicht ist das Laufwerk oder der Cloud-Ordner gerade nicht verbunden. Es wurde nichts verändert.';
    buttons = [other(true), retry];
  } else if (p.error === 'file_missing') {
    title = 'Im Datenordner liegt keine Datendatei';
    text = 'Wird der Ordner per Cloud synchronisiert, ist die Datei vielleicht noch nicht angekommen. Dann bitte kurz warten und erneut versuchen. Eine neue leere Datei nur anlegen, wenn du wirklich neu anfangen möchtest.';
    buttons = [retry, other(false), btn('Neue leere Datei anlegen', async () => applyLoadResult(await api.hersteller_datei_anlegen()))];
  } else {
    title = p.error === 'corrupt' ? 'Die Datendatei ist beschädigt' : 'Die Daten konnten nicht geladen werden';
    text = (p.message || '') + ' Die Datei wurde nicht verändert.';
    buttons = [p.backup && btn('Neuestes Backup laden (' + fmtDate(p.backup) + ')', async () => applyLoadResult(await api.hersteller_backup_laden()), true), retry, other(false)];
  }
  return h('div', { class: 'empty-start' }, h('div', { class: 'problem' }, h('h2', {}, title), h('p', {}, text), path, h('div', { class: 'row' }, buttons)));
}

function conflictDialog() {
  showModal({
    title: 'Daten wurden woanders geändert', size: 'medium',
    body: h('p', {}, 'Die Daten wurden auf einem anderen Rechner geändert. Neu laden (eigene Änderungen gehen verloren) oder meine Version als Kopie speichern?'),
    foot: [h('span', { class: 'spacer' }),
      h('button', { class: 'btn', onclick: reload }, 'Neu laden'),
      h('button', { class: 'btn primary', onclick: async () => {
        const res = await api.hersteller_kopie_speichern(buildData());
        if (!res.ok) { toast(res.message || 'Die Kopie konnte nicht gespeichert werden.'); return; }
        await reload();
        toast('Kopie gespeichert: ' + res.file);
      } }, 'Meine Version als Kopie speichern')],
  });
}

/* ---------- Start ---------- */

function startDemo() {
  state.demo = true;
  state.suppliers = demoSuppliers();
  seedDocuments();
  state.ready = true;
  setStatus('Vorschau im Browser – es wird nichts gespeichert');
  render();
}

async function startApp() {
  state.demo = false;
  state.documents = [];
  state.counters = { RS: {}, RK: {} };
  state.ready = false;
  await reload();
  hintUpdate();
}

modalCloseHooks.push(() => { state.draft = null; });

// Baut die Oberfläche des Moduls in den Container, den das Grundgerüst vorgibt.
function mountHersteller(root) {
  root.append(
    h('div', { class: 'layout' },
      h('aside', { class: 'sidebar' },
        h('div', { class: 'sidebar-top' },
          h('input', { id: 'search', type: 'search', placeholder: 'Suchen …', autocomplete: 'off', spellcheck: 'false' }),
          h('h2', { id: 'sidebar-title' }, SIDEBAR_TITLE)),
        h('ul', { id: 'supplier-list', class: 'supplier-list' }),
        h('div', { class: 'sidebar-bottom' },
          h('button', { id: 'btn-add-supplier', class: 'btn primary grow', onclick: addSupplierDialog }, '+ Hersteller anlegen'),
          h('button', { id: 'btn-settings', class: 'btn icon-btn', title: 'Einstellungen', 'aria-label': 'Einstellungen', onclick: () => openSettings() }, icon('gear')))),
      h('main', { id: 'main', class: 'main' })));
  document.getElementById('search').addEventListener('input', (e) => { state.search = e.target.value; renderList(); });
  if (api) startApp(); else startDemo();
}

document.addEventListener('click', () => { if (state.menu) { state.menu = null; renderMain(); } });
document.addEventListener('click', closeContextMenu);
document.addEventListener('contextmenu', (e) => { if (!e.target.closest('#supplier-list li')) closeContextMenu(); });
window.addEventListener('blur', closeContextMenu);
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || e.defaultPrevented) return;
  if (document.getElementById('ctx-menu')) { closeContextMenu(); return; }
  if (state.docsPanel) { state.docsPanel = false; renderPanel(); }
});

// Jede Eingabe und jeder Klick kann Daten geändert haben; gespeichert wird nur bei echtem Unterschied.
for (const type of ['input', 'change', 'click', 'drop']) document.addEventListener(type, scheduleSave);
window.addEventListener('blur', saveNow);
document.addEventListener('visibilitychange', () => { if (document.hidden) saveNow(); });

registerModule({ id: 'hersteller', title: 'Hersteller', mount: mountHersteller });
