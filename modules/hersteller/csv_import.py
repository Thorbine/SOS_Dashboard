"""CSV-Import von Herstellern: Datei lesen, Vorschau bilden, neue Hersteller erzeugen.

Bestehende Hersteller werden nie überschrieben; Duplikate (gleicher Name ohne Beachtung der
Groß-/Kleinschreibung) werden übersprungen.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from . import models

# Spaltenname in der Datei (klein geschrieben) -> interner Schlüssel
COLUMNS = {
    "name": "name", "hersteller": "name", "lieferant": "name",
    "kundennr": "kundennr", "kundennr.": "kundennr", "kundennummer": "kundennr", "unsere kundennr": "kundennr",
    "b2b": "B2B", "reklamation": "Reklamation", "medien": "Medien",
}
LINK_GROUPS = ("B2B", "Reklamation", "Medien")
CUSTOMER_LABEL = "Unsere Kundennr"


class CsvError(Exception):
    """Die Datei kann nicht importiert werden. Die Meldung ist für die Oberfläche gedacht."""


def read_text(path) -> str:
    """UTF-8 (auch mit BOM), bei Fehlern Windows-1252."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise CsvError(f"Die Datei konnte nicht gelesen werden: {exc}") from exc
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def detect_delimiter(text: str) -> str:
    """Semikolon oder Komma, je nachdem, was in der Kopfzeile häufiger vorkommt."""
    header = next((line for line in text.splitlines() if line.strip()), "")
    return "," if header.count(",") > header.count(";") else ";"


def parse(text: str) -> tuple[list[dict], list[dict]]:
    """Gibt (Zeilen, Fehler) zurück. Zeilen: {line, name, kundennr, B2B, Reklamation, Medien}."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=detect_delimiter(text))
    header = None
    keys: list = []
    rows, errors = [], []
    for record in reader:
        cells = [c.strip() for c in record]
        if not any(cells):
            continue
        if header is None:
            header = cells
            keys = [COLUMNS.get(c.lower()) for c in cells]
            if "name" not in keys:
                raise CsvError("In der ersten Zeile fehlt die Spalte „Name“.")
            continue
        row = {"line": reader.line_num, "name": "", "kundennr": "", "B2B": "", "Reklamation": "", "Medien": ""}
        for key, cell in zip(keys, cells):
            if key and not row[key]:
                row[key] = cell
        if not row["name"]:
            errors.append({"line": reader.line_num, "message": "Name fehlt"})
            continue
        rows.append(row)
    if header is None:
        raise CsvError("Die Datei ist leer.")
    return rows, errors


def split_new(rows: list[dict], existing_names) -> tuple[list[dict], list[dict]]:
    """Teilt in (neu, Duplikate). Auch doppelte Namen innerhalb der Datei gelten als Duplikat."""
    seen = {str(n).strip().casefold() for n in existing_names}
    new, duplicates = [], []
    for row in rows:
        key = row["name"].casefold()
        if key in seen:
            duplicates.append(row)
        else:
            seen.add(key)
            new.append(row)
    return new, duplicates


def build_supplier(row: dict, template: list) -> dict:
    """Neuer Hersteller aus der Vorlage; Kundennr und Links landen in den Standardfeldern."""
    supplier = models.new_supplier(row["name"], template)
    blocks = supplier["blocks"]

    if row["kundennr"]:
        fields_block = next((b for b in blocks if b["type"] == "fields"), None)
        if fields_block is None:
            fields_block = models.new_block("fields", "Infos")
            blocks.insert(0, fields_block)
        field = next((f for f in fields_block["fields"] if f["label"].strip().casefold() == CUSTOMER_LABEL.casefold()), None)
        if field is None:
            field = models.new_field(CUSTOMER_LABEL)
            fields_block["fields"].insert(0, field)
        field["value"] = row["kundennr"]

    for label in LINK_GROUPS:
        url = row[label]
        if not url:
            continue
        links_block = next((b for b in blocks if b["type"] == "links"), None)
        if links_block is None:
            links_block = models.new_block("links", "Links")
            notes_at = next((i for i, b in enumerate(blocks) if b["type"] == "notes"), len(blocks))
            blocks.insert(notes_at, links_block)
        group = next((g for g in links_block["groups"] if g["label"].strip().casefold() == label.casefold()), None)
        if group is None:
            group = models.new_group(label)
            links_block["groups"].append(group)
        group["links"].append(models.new_link(label, url))
    return supplier


def preview(path, data: dict) -> dict:
    """Vorschau vor dem Import: neue Hersteller, übersprungene Duplikate, Zeilen mit Fehlern."""
    rows, errors = parse(read_text(path))
    new, duplicates = split_new(rows, [s.get("name", "") for s in data.get("suppliers", [])])
    return {
        "file": Path(path).name,
        "new": [r["name"] for r in new],
        "duplicates": [r["name"] for r in duplicates],
        "errors": errors,
    }


def apply(path, data: dict) -> list[dict]:
    """Hängt die neuen Hersteller an `data` an und gibt sie zurück."""
    rows, _ = parse(read_text(path))
    new, _ = split_new(rows, [s.get("name", "") for s in data.get("suppliers", [])])
    created = [build_supplier(row, data.get("blockTemplate") or models.DEFAULT_BLOCK_TEMPLATE) for row in new]
    data.setdefault("suppliers", []).extend(created)
    return created
