"""Python-Seite des Moduls Preisschilder. Die Methoden erscheinen in der Oberflaeche als preisschilder_<name>().

Daten im Datenordner unter preisschilder/: einstellungen.json, liste_<typ>.json, seiten_schlaeger.json,
logos/<Produkt>/. Jede JSON-Datei hat schemaVersion, revision und (Listen) items."""

from __future__ import annotations

import base64
import io
import json
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import config
import platform_utils
from storage import Storage, StorageError

from . import csv_import, settings, sheet
from .layouts import DRAW, schlaeger
from .layouts.helme import GROESSEN, anlegen_groessen

SUBDIR = "preisschilder"
LOGO_SUBDIR = "logos"
NO_FOLDER = {"ok": False, "error": "no_folder", "message": "Es ist kein Datenordner gewählt."}
FILE_TYPES = ("JSON-Dateien (*.json)", "Alle Dateien (*.*)")
_RENDER_LOCK = threading.Lock()  # sheet.LOGO_DIR ist ein gemeinsamer Wert


def _empty_list():
    return {"schemaVersion": 1, "revision": 0, "items": []}


def _clean(item: dict) -> dict:
    """Ohne Laufzeitfelder (_blatt) und ohne alte Felder."""
    return {k: v for k, v in item.items() if not str(k).startswith("_") and k not in ("anzahl", "druck")}


OLD_BRANDS = {"wilson": "Wilson", "head": "HEAD", "babolat": "Babolat", "yonex": "Yonex", "tecnifibre": "Tecnifibre"}


def convert_racket(card: dict) -> dict:
    """Ein Schild aus dem alten Schläger-Generator (brand, color) in das Format des Dashboards (marke, farbe)."""
    out = {k: v for k, v in card.items() if k not in ("brand", "color", "count")}
    if "marke" not in out and card.get("brand"):
        brand = str(card["brand"])
        out["marke"] = OLD_BRANDS.get(brand.lower(), brand[:1].upper() + brand[1:])
    if "farbe" not in out and card.get("color"):
        out["farbe"] = card["color"]
    return out


class Backend:
    def __init__(self, ctx):
        self.ctx = ctx
        self._stores = {}
        self._thumbs = {}

    # ----- intern -----

    def _data_dir(self):
        return config.get_data_dir()

    def _logo_dir(self) -> Path:
        return Path(self._data_dir()) / SUBDIR / LOGO_SUBDIR

    def _store(self, name: str, list_key="items", new=_empty_list) -> Storage:
        data_dir = self._data_dir()
        key = (str(data_dir), name)
        store = self._stores.get(key)
        if store is None:
            store = Storage(data_dir, filename=f"{SUBDIR}/{name}.json", list_key=list_key, new_data=new, normalize=lambda d: d)
            self._stores[key] = store
        return store

    def _error(self, exc: Exception) -> dict:
        return {"ok": False, "error": getattr(exc, "code", "io"), "message": str(exc)}

    def _guard(self, action):
        if not self._data_dir():
            return NO_FOLDER
        try:
            return action()
        except StorageError as exc:
            return self._error(exc)
        except ValueError as exc:
            return {"ok": False, "error": "value", "message": str(exc)}
        except OSError as exc:
            return {"ok": False, "error": "io", "message": f"Die Datei konnte nicht bearbeitet werden: {exc}"}

    def _settings(self) -> dict:
        """Gespeicherte Einstellungen ueber den Standardwerten."""
        store = self._store("einstellungen", list_key=None, new=lambda: {"schemaVersion": 1, "revision": 0})
        saved = store.load(create=True)
        out = {"rand": saved.get("rand", settings.DEFAULTS["rand"]), "abstand": saved.get("abstand", settings.DEFAULTS["abstand"]),
               "marken": saved.get("marken") or {name: {"farbe": color} for name, color in schlaeger.BRANDS.items()}}
        for typ in settings.TYPEN:
            out[typ] = {**settings.DEFAULTS[typ], **(saved.get(typ) or {})}
        return out

    def _prepare_folders(self) -> None:
        """Legt Logo-Ordner an und kopiert die mitgelieferten weissen Schlaeger-Logos, wenn sie fehlen."""
        logo_dir = self._logo_dir()
        settings.logo_ordner_anlegen(logo_dir)
        source = self.ctx.base_dir / "assets" / "preisschilder" / "logos" / "Schläger"
        target = settings.logo_ordner(logo_dir, "schlaeger")
        if source.is_dir():
            for file in source.glob("*.png"):
                if not (target / file.name).exists():
                    shutil.copyfile(file, target / file.name)

    # ----- Einstellungen und Listen -----

    def start(self) -> dict:
        """Beim Oeffnen des Moduls: Ordner anlegen, Einstellungen und Typen liefern."""
        def action():
            self._prepare_folders()
            return {"ok": True, "einstellungen": self._settings(),
                    "typen": {k: {"name": v[0]} for k, v in settings.TYPEN.items()},
                    "marken_standard": schlaeger.BRANDS, "farben": schlaeger.COLOR_PRESETS, "groessen": GROESSEN}
        return self._guard(action)

    def einstellungen_speichern(self, daten: dict) -> dict:
        def action():
            clean = {"rand": float(daten["rand"]), "abstand": float(daten["abstand"])}
            if clean["rand"] < 0 or clean["abstand"] < 0:
                raise ValueError("Rand und Abstand dürfen nicht negativ sein.")
            for typ in settings.TYPEN:
                w, h = float(daten[typ]["breite"]), float(daten[typ]["hoehe"])
                if w <= 0 or h <= 0:
                    raise ValueError("Die Schildmaße müssen größer als 0 sein.")
                clean[typ] = {"breite": w, "hoehe": h}
            clean["marken"] = {str(n).strip(): {"farbe": str(v.get("farbe", "#555555"))}
                               for n, v in (daten.get("marken") or {}).items() if str(n).strip()}
            store = self._store("einstellungen", list_key=None, new=lambda: {"schemaVersion": 1, "revision": 0})
            current = store.load(create=True)
            try:
                for typ in settings.TYPEN:  # pruefen, dass jedes Schild aufs Blatt passt
                    if typ == "schlaeger":
                        continue
                    sheet.grid(clean[typ]["breite"], clean[typ]["hoehe"], clean["rand"], clean["abstand"])
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            current.update(clean)
            return {"ok": True, "revision": store.save(current), "einstellungen": self._settings()}
        return self._guard(action)

    def liste_laden(self, typ: str) -> dict:
        def action():
            self._check_typ(typ)
            data = self._store(f"liste_{typ}").load(create=True)
            return {"ok": True, "items": data["items"], "revision": data["revision"]}
        return self._guard(action)

    def liste_speichern(self, typ: str, items: list) -> dict:
        def action():
            self._check_typ(typ)
            store = self._store(f"liste_{typ}")
            if store.revision == 0 and not store.path.exists():
                store.load(create=True)
            return {"ok": True, "revision": store.save({"items": [_clean(i) for i in items]})}
        return self._guard(action)

    def liste_kopie_speichern(self, typ: str, items: list) -> dict:
        """Bei einem Konflikt: die eigene Liste als Kopie neben die Datei legen."""
        def action():
            return {"ok": True, "file": str(self._store(f"liste_{typ}").save_copy({"items": [_clean(i) for i in items]}))}
        return self._guard(action)

    def _check_typ(self, typ):
        if typ not in settings.TYPEN:
            raise ValueError("Unbekannter Schildtyp.")

    # ----- Logos -----

    def logos(self, typ: str) -> dict:
        """Logos des Produkts (und die gemeinsamen) mit kleinem Vorschaubild."""
        def action():
            self._check_typ(typ)
            logo_dir = self._logo_dir()
            names = settings.logos(logo_dir, typ)
            out = []
            for n in names:
                entry = {"name": n, "bild": self._thumb(logo_dir / n, dark=(typ == "schlaeger"))}
                if typ == "schlaeger":  # die Karten in der Oberflaeche brauchen das weisse Logo auf der Markenfarbe
                    entry["roh"] = "data:image/png;base64," + base64.b64encode((logo_dir / n).read_bytes()).decode()
                out.append(entry)
            return {"ok": True, "logos": out}
        return self._guard(action)

    def _thumb(self, path: Path, dark: bool = False):
        from PIL import Image

        try:
            key = (str(path), path.stat().st_mtime, dark)
            if key not in self._thumbs:
                image = Image.open(path).convert("RGBA")
                image.thumbnail((92, 44))
                background = Image.new("RGBA", image.size, (90, 90, 90, 255) if dark else (255, 255, 255, 255))
                background.alpha_composite(image)
                buf = io.BytesIO()
                background.convert("RGB").save(buf, "PNG")
                self._thumbs[key] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
            return self._thumbs[key]
        except Exception:  # noqa: BLE001 - defekte Bilddatei ueberspringen
            return ""

    def logo_ordner_oeffnen(self, typ: str) -> dict:
        def action():
            self._check_typ(typ)
            settings.logo_ordner_anlegen(self._logo_dir())
            platform_utils.open_path(settings.logo_ordner(self._logo_dir(), typ))
            return {"ok": True}
        return self._guard(action)

    # ----- Vorschau und Druck -----

    def _render(self, typ: str, items: list, target) -> None:
        if not items:
            raise ValueError("Es sind keine Schilder auf dem Blatt.")
        cfg = self._settings()
        with _RENDER_LOCK:
            sheet.LOGO_DIR = str(self._logo_dir())
            if typ == "schlaeger":
                colors = {n: v.get("farbe") for n, v in cfg["marken"].items()}
                prepared = [dict(_clean(i), farbe=i.get("farbe") or colors.get(i.get("marke"), "#555555")) for i in items]
                schlaeger.render_pdf(target, prepared, cfg[typ]["breite"], cfg[typ]["hoehe"])
            else:
                sheet.render_pdf(target, cfg[typ]["breite"], cfg[typ]["hoehe"], [_clean(i) for i in items], DRAW[typ],
                                 cfg["rand"], cfg["abstand"])

    def vorschau(self, typ: str, items: list, seite: int = 0, breite: int = 540) -> dict:
        """Rendert das Blatt per pymupdf als PNG. Gibt Seitenzahl und Anzahl pro Blatt mit zurueck."""
        def action():
            import pymupdf

            self._check_typ(typ)
            if not items:
                return {"ok": True, "leer": True}
            buf = io.BytesIO()
            self._render(typ, items, buf)
            doc = pymupdf.open(stream=buf.getvalue(), filetype="pdf")
            page = doc[max(0, min(int(seite), len(doc) - 1))]
            zoom = max(breite, 100) / page.rect.width
            png = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
            return {"ok": True, "bild": "data:image/png;base64," + base64.b64encode(png).decode(), "seiten": len(doc),
                    "seite": page.number}
        return self._guard(action)

    def drucken(self, typ: str, items: list) -> dict:
        """Erzeugt ein A4-PDF im temporaeren Ordner und oeffnet es."""
        def action():
            self._check_typ(typ)
            path = Path(tempfile.gettempdir()) / f"preisschilder_{typ}.pdf"
            self._render(typ, items, str(path))
            platform_utils.open_path(path)
            return {"ok": True, "datei": str(path)}
        return self._guard(action)

    def blatt_info(self, typ: str) -> dict:
        """Schildmass und wie viele Schilder auf ein Blatt passen."""
        def action():
            cfg = self._settings()
            w, h = cfg[typ]["breite"], cfg[typ]["hoehe"]
            if typ == "schlaeger":
                per = schlaeger.PER_PAGE_COLS * schlaeger.grid_rows(h * 72 / 25.4)
            else:
                per = sheet.pro_blatt(w, h, cfg["rand"], cfg["abstand"])
            return {"ok": True, "breite": w, "hoehe": h, "pro_blatt": per}
        return self._guard(action)

    # ----- Helme -----

    def helme_csv_importieren(self) -> dict:
        """Fragt nach der Helm-CSV und haengt neue Modelle an die gespeicherte Liste an."""
        path = self.ctx.choose_file(("CSV (*.csv)", "Alle Dateien (*.*)"))
        if not path:
            return {"ok": False, "error": "cancelled"}

        def action():
            try:
                neu = csv_import.lese_helme(path, settings.logos(self._logo_dir(), "helme"))
            except (OSError, ValueError) as exc:
                raise ValueError(f"Die Datei konnte nicht gelesen werden: {exc}") from exc
            store = self._store("liste_helme")
            data = store.load(create=True)
            items = data["items"]
            dazu = csv_import.zusammenfuehren(items, neu)
            revision = store.save({"items": items}) if dazu else store.revision
            return {"ok": True, "items": items, "revision": revision, "neu": dazu, "schon_da": len(neu) - dazu,
                    "ohne_logo": sorted({i["modell"] for i in neu if not i["logo"]})}
        return self._guard(action)

    def helme_alle_groessen(self) -> dict:
        def action():
            store = self._store("liste_helme")
            items = store.load(create=True)["items"]
            neu = anlegen_groessen(items, GROESSEN)
            revision = store.save({"items": items}) if neu else store.revision
            return {"ok": True, "items": items, "revision": revision, "neu": neu}
        return self._guard(action)

    # ----- Gespeicherte Schlaeger-Seiten -----

    def seiten_laden(self) -> dict:
        def action():
            data = self._store("seiten_schlaeger").load(create=True)
            return {"ok": True, "items": data["items"], "revision": data["revision"]}
        return self._guard(action)

    def seiten_speichern(self, items: list) -> dict:
        def action():
            store = self._store("seiten_schlaeger")
            if store.revision == 0 and not store.path.exists():
                store.load(create=True)
            return {"ok": True, "revision": store.save({"items": items})}
        return self._guard(action)

    def seiten_exportieren(self) -> dict:
        target = self.ctx.save_file("gespeicherte-seiten-schlaeger.json", FILE_TYPES)
        if not target:
            return {"ok": False, "error": "cancelled"}

        def action():
            items = self._store("seiten_schlaeger").load(create=True)["items"]
            Path(target).write_text(json.dumps({"seiten": items}, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "datei": str(target), "anzahl": len(items)}
        return self._guard(action)

    def seiten_importieren(self) -> dict:
        path = self.ctx.choose_file(FILE_TYPES)
        if not path:
            return {"ok": False, "error": "cancelled"}

        def action():
            try:
                raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            except (OSError, ValueError) as exc:
                raise ValueError(f"Die Datei konnte nicht gelesen werden: {exc}") from exc
            pages = raw.get("seiten") if isinstance(raw, dict) else raw
            if not isinstance(pages, list) or not all(isinstance(p, dict) and isinstance(p.get("cards", p.get("schilder")), list) for p in pages):
                raise ValueError("Das ist keine Datei mit gespeicherten Seiten.")
            fixed = [{"name": str(p.get("name", ""))[:40], "date": p.get("date") or p.get("datum", ""),
                      "cards": [convert_racket(c) for c in p.get("cards", p.get("schilder")) if isinstance(c, dict)]} for p in pages]
            return {"ok": True, "seiten": fixed}
        return self._guard(action)

    # ----- Uebernahme aus dem Altprogramm -----

    def uebernahme_pruefen(self) -> dict:
        """Fragt nach dem alten Ordner "daten" und meldet, was uebernommen wuerde und was schon vorhanden ist."""
        folder = self.ctx.choose_folder()
        if not folder:
            return {"ok": False, "error": "cancelled"}

        def action():
            plan = self._migration_plan(Path(folder))
            if not plan["dateien"]:
                raise ValueError("In diesem Ordner liegen keine Daten des alten Preisschilder-Programms (erwartet: den Ordner „daten“).")
            return {"ok": True, "ordner": folder, **plan}
        return self._guard(action)

    def _migration_plan(self, old: Path) -> dict:
        base = Path(self._data_dir()) / SUBDIR
        files = []
        if (old / "einstellungen.json").is_file():
            files.append(("einstellungen.json", base / "einstellungen.json"))
        for typ in settings.TYPEN:
            if (old / f"liste_{typ}.json").is_file():
                files.append((f"liste_{typ}.json", base / f"liste_{typ}.json"))
        logos = old / "logos"
        if logos.is_dir():
            for file in sorted(logos.rglob("*")):
                rel = file.relative_to(logos)
                if file.is_file() and not rel.parts[0].startswith("_") and file.suffix.lower() in settings.LOGO_ENDUNGEN:
                    files.append(("logos/" + platform_utils.nfc(rel.as_posix()), base / LOGO_SUBDIR / platform_utils.nfc(rel.as_posix())))
        entries = [{"quelle": s, "vorhanden": d.exists() and (d.stat().st_size > 0 and not self._is_empty_data(d))} for s, d in files]
        return {"dateien": entries, "anzahl": len(entries), "vorhanden": sum(e["vorhanden"] for e in entries)}

    @staticmethod
    def _is_empty_data(path: Path) -> bool:
        if path.suffix != ".json":
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return isinstance(data, dict) and data.get("items") == [] and path.name.startswith("liste_")

    def uebernahme_ausfuehren(self, ordner: str, ueberschreiben: bool = False) -> dict:
        """Kopiert Einstellungen, Listen und Logos aus dem alten Ordner "daten". Vorhandenes bleibt, wenn nicht ueberschrieben wird."""
        def action():
            old = Path(ordner)
            base = Path(self._data_dir()) / SUBDIR
            self._prepare_folders()
            copied = skipped = 0
            old_settings = old / "einstellungen.json"
            if old_settings.is_file():
                target = base / "einstellungen.json"
                try:
                    raw = json.loads(old_settings.read_text(encoding="utf-8"))
                except ValueError as exc:
                    raise ValueError("Die alte Einstellungsdatei ist beschädigt.") from exc
                store = self._store("einstellungen", list_key=None, new=lambda: {"schemaVersion": 1, "revision": 0})
                current = store.load(create=True)
                have = any(k in current for k in ("rand", "abstand") + tuple(settings.TYPEN))
                if have and not ueberschreiben:
                    skipped += 1
                else:
                    for key in ("rand", "abstand"):
                        if key in raw:
                            current[key] = raw[key]
                    for typ in settings.TYPEN:
                        if typ != "schlaeger" and isinstance(raw.get(typ), dict):
                            current[typ] = raw[typ]
                    store.save(current)
                    copied += 1
                _ = target
            for typ in settings.TYPEN:
                src = old / f"liste_{typ}.json"
                if not src.is_file():
                    continue
                try:
                    items = json.loads(src.read_text(encoding="utf-8"))
                except ValueError as exc:
                    raise ValueError(f"Die alte Liste {src.name} ist beschädigt.") from exc
                if not isinstance(items, list):
                    items = items.get("items", []) if isinstance(items, dict) else []
                store = self._store(f"liste_{typ}")
                current = store.load(create=True)
                if current["items"] and not ueberschreiben:
                    skipped += 1
                    continue
                store.save({"items": [_clean(i) for i in items if isinstance(i, dict)]})
                copied += 1
            for entry in self._migration_plan(old)["dateien"]:
                if not entry["quelle"].startswith("logos/"):
                    continue
                rel = entry["quelle"][len("logos/"):]
                src = self._find_real(old / "logos", rel)
                dest = self._logo_dir() / rel
                if dest.exists() and not ueberschreiben:
                    skipped += 1
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
                copied += 1
            return {"ok": True, "kopiert": copied, "uebersprungen": skipped}
        return self._guard(action)

    @staticmethod
    def _find_real(root: Path, rel: str) -> Path:
        """Die Datei zu einem NFC-Pfad finden, auch wenn sie auf der Platte als NFD liegt."""
        direct = root / rel
        if direct.exists():
            return direct
        for file in root.rglob("*"):
            if platform_utils.nfc(file.relative_to(root).as_posix()) == rel:
                return file
        return direct
