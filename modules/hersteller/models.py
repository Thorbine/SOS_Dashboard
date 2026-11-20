"""Datenmodell: Block-Vorlagen, neue Hersteller, Auffüllen fehlender Felder."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime

SCHEMA_VERSION = 1

DEFAULT_BLOCK_TEMPLATE = [
    {"type": "fields", "title": "Infos", "defaults": [{"label": "Unsere Kundennr", "value": ""}]},
    {"type": "contacts", "title": "Ansprechpartner"},
    {"type": "addresses", "title": "Adressen",
     "defaults": [{"label": "Hauptadresse"}, {"label": "Retourenadresse"}, {"label": "Reklamationsadresse"}]},
    {"type": "links", "title": "Links", "defaults": [{"label": "B2B"}, {"label": "Reklamation"}, {"label": "Medien"}]},
    {"type": "notes", "title": "Notizen"},
]

DEFAULT_COMPANY = {
    "name": "SOS Sport GmbH", "street": "Rebenring 10", "zip": "38106", "city": "Braunschweig",
    "country": "Deutschland", "phone": "+49 (0) 531-347711", "email": "shop@sos-sport.de",
    "managingDirector": "Oliver Nieß", "register": "HRB 4881, Amtsgericht Braunschweig",
    "vatId": "DE 201646705", "showFooter": False,
}

_FIELD = {"label": "", "value": ""}
_CONTACT = {"name": "", "role": "", "phone": "", "mobile": "", "email": "", "note": ""}
_ADDRESS = {"label": "", "isDefault": False, "company": "", "addition": "", "street": "", "zip": "", "city": "",
            "country": "Deutschland", "contactName": "", "phone": "", "email": "", "note": ""}
_LINK = {"title": "", "url": ""}

# Schlüssel der Zeilenliste je Blocktyp und die Vorlage für eine Zeile.
_ROWS = {"fields": ("fields", _FIELD), "contacts": ("contacts", _CONTACT), "addresses": ("addresses", _ADDRESS)}


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _row(template: dict, **values) -> dict:
    return {"id": new_id(), **template, **values}


def new_field(label: str = "", value: str = "") -> dict:
    return _row(_FIELD, label=label, value=value)


def new_contact(**values) -> dict:
    return _row(_CONTACT, **values)


def new_address(**values) -> dict:
    return _row(_ADDRESS, **values)


def new_link(title: str = "", url: str = "") -> dict:
    return _row(_LINK, title=title, url=url)


def new_group(label: str = "", links: list | None = None) -> dict:
    return {"id": new_id(), "label": label, "links": links or []}


def new_block(block_type: str, title: str, defaults: list | None = None) -> dict:
    defaults = defaults or []
    block = {"id": new_id(), "type": block_type, "title": title, "visible": True}
    if block_type == "fields":
        block["fields"] = [new_field(d.get("label", ""), d.get("value", "")) for d in defaults]
    elif block_type == "contacts":
        block["contacts"] = []
    elif block_type == "addresses":
        block["addresses"] = [new_address(label=d.get("label", "")) for d in defaults]
        ensure_single_default(block["addresses"])
    elif block_type == "links":
        block["groups"] = [new_group(d.get("label", "")) for d in defaults]
    elif block_type == "notes":
        block["text"] = ""
    return block


def new_supplier(name: str, template: list | None = None) -> dict:
    """Neuer Hersteller aus der Vorlage. Spätere Änderungen an der Vorlage wirken nicht zurück."""
    template = DEFAULT_BLOCK_TEMPLATE if template is None else template
    now = now_iso()
    return {
        "id": new_id(), "name": name, "createdAt": now, "updatedAt": now,
        "blocks": [new_block(t["type"], t.get("title", ""), t.get("defaults")) for t in template],
    }


def new_data() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "revision": 0,
        "blockTemplate": copy.deepcopy(DEFAULT_BLOCK_TEMPLATE),
        "company": dict(DEFAULT_COMPANY),
        "counters": {"RS": {}, "RK": {}},
        "documents": [],
        "suppliers": [],
    }


def ensure_single_default(addresses: list) -> None:
    """Genau eine Standardadresse: die erste markierte gewinnt, sonst die erste Adresse."""
    if not addresses:
        return
    chosen = next((a for a in addresses if a.get("isDefault")), addresses[0])
    for a in addresses:
        a["isDefault"] = a is chosen


def _fill(item, template: dict) -> dict:
    item = item if isinstance(item, dict) else {}
    for key, default in template.items():
        if not isinstance(item.get(key), type(default)):
            item[key] = default
    item.setdefault("id", new_id())
    return item


def _list(value) -> list:
    return value if isinstance(value, list) else []


def normalize(data: dict) -> dict:
    """Füllt fehlende Felder auf, damit die Oberfläche sich auf die Struktur verlassen kann.

    Unbekannte Schlüssel und Blocktypen bleiben unverändert erhalten.
    """
    data.setdefault("schemaVersion", SCHEMA_VERSION)
    if not isinstance(data.get("revision"), int):
        data["revision"] = 0
    if not isinstance(data.get("blockTemplate"), list) or not data["blockTemplate"]:
        data["blockTemplate"] = copy.deepcopy(DEFAULT_BLOCK_TEMPLATE)
    company = data.get("company") if isinstance(data.get("company"), dict) else {}
    data["company"] = {**DEFAULT_COMPANY, **company}
    counters = data.get("counters") if isinstance(data.get("counters"), dict) else {}
    data["counters"] = {"RS": {}, "RK": {}, **counters}
    data["documents"] = _list(data.get("documents"))
    data["suppliers"] = [s for s in _list(data.get("suppliers")) if isinstance(s, dict)]

    for supplier in data["suppliers"]:
        supplier.setdefault("id", new_id())
        if not isinstance(supplier.get("name"), str):
            supplier["name"] = ""
        supplier.setdefault("createdAt", now_iso())
        supplier.setdefault("updatedAt", supplier["createdAt"])
        supplier["blocks"] = [b for b in _list(supplier.get("blocks")) if isinstance(b, dict)]
        for block in supplier["blocks"]:
            block.setdefault("id", new_id())
            if not isinstance(block.get("title"), str):
                block["title"] = ""
            if not isinstance(block.get("visible"), bool):
                block["visible"] = True
            block_type = block.get("type")
            if block_type in _ROWS:
                key, template = _ROWS[block_type]
                block[key] = [_fill(row, template) for row in _list(block.get(key))]
                if block_type == "addresses":
                    ensure_single_default(block[key])
            elif block_type == "links":
                groups = []
                for group in _list(block.get("groups")):
                    group = _fill(group, {"label": ""})
                    group["links"] = [_fill(link, _LINK) for link in _list(group.get("links"))]
                    groups.append(group)
                block["groups"] = groups
            elif block_type == "notes" and not isinstance(block.get("text"), str):
                block["text"] = ""
    return data
