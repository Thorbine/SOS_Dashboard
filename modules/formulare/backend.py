"""Python-Seite des Moduls Formulare: Druckvorlagen (PDF) im Datenordner oeffnen, ersetzen, im Ordner zeigen.

Die mitgelieferten Vorlagen (assets/formulare/) werden beim ersten Start nach <Datenordner>/formulare/ kopiert;
danach gilt der Ordner im Datenordner. Optional: formulare/beschreibung.json (Dateiname -> Kurzzeile)."""

from __future__ import annotations

import base64
import json
import shutil
from datetime import datetime
from pathlib import Path

import config
import platform_utils

SUBDIR = "formulare"
OLD_DIR = "_alt"
DESCRIPTIONS = "beschreibung.json"
NO_FOLDER = {"ok": False, "error": "no_folder", "message": "Es ist kein Datenordner gewählt."}


def _format_text(width_pt: float, height_pt: float) -> str:
    """'A4 quer', 'A4 hoch' oder die Masse in mm."""
    w, h = sorted((width_pt, height_pt))
    mm_w, mm_h = round(w / 72 * 25.4), round(h / 72 * 25.4)
    landscape = width_pt > height_pt
    if (mm_w, mm_h) == (210, 297):
        return "A4 quer" if landscape else "A4 hoch"
    return f"{mm_w} × {mm_h} mm"


class Backend:
    def __init__(self, ctx):
        self.ctx = ctx
        self._previews = {}

    def _folder(self) -> Path:
        return Path(config.get_data_dir()) / SUBDIR

    def _guard(self, action):
        if not config.get_data_dir():
            return NO_FOLDER
        try:
            return action()
        except ValueError as exc:
            return {"ok": False, "error": "value", "message": str(exc)}
        except OSError as exc:
            return {"ok": False, "error": "io", "message": f"Die Datei konnte nicht bearbeitet werden: {exc}"}

    def _prepare(self) -> None:
        folder = self._folder()
        folder.mkdir(parents=True, exist_ok=True)
        if not any(folder.glob("*.pdf")) and not (folder / OLD_DIR).exists():
            source = self.ctx.base_dir / "assets" / "formulare"
            for pdf in sorted(source.glob("*.pdf")) if source.is_dir() else []:
                shutil.copyfile(pdf, folder / platform_utils.nfc(pdf.name))

    def _file(self, name: str) -> Path:
        """Die PDF zu einem Dateinamen im Formulare-Ordner; nur Dateinamen, keine Pfade."""
        if not name or Path(name).name != name or not name.lower().endswith(".pdf"):
            raise ValueError("Ungültiger Dateiname.")
        for pdf in self._folder().glob("*.pdf"):
            if platform_utils.same_name(pdf.name, name):
                return pdf
        raise ValueError("Die Vorlage wurde nicht gefunden.")

    def _preview(self, pdf: Path):
        import pymupdf

        key = (str(pdf), pdf.stat().st_mtime)
        if key not in self._previews:
            with pymupdf.open(str(pdf)) as doc:
                page = doc[0]
                zoom = 300 / page.rect.width
                png = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
                self._previews[key] = ("data:image/png;base64," + base64.b64encode(png).decode(), _format_text(page.rect.width, page.rect.height))
        return self._previews[key]

    def liste(self) -> dict:
        """Eine Kachel pro PDF im Ordner, alphabetisch."""
        def action():
            self._prepare()
            try:
                texts = json.loads((self._folder() / DESCRIPTIONS).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                texts = {}
            tiles = []
            for pdf in sorted(self._folder().glob("*.pdf"), key=lambda p: platform_utils.nfc(p.name).lower()):
                try:
                    image, fmt = self._preview(pdf)
                except Exception:  # noqa: BLE001 - defekte PDF: Kachel ohne Vorschau
                    image, fmt = "", "?"
                name = platform_utils.nfc(pdf.name)
                tiles.append({"datei": name, "name": platform_utils.nfc(pdf.stem), "format": fmt, "bild": image,
                              "text": next((v for k, v in texts.items() if platform_utils.same_name(k, name)), "")})
            return {"ok": True, "formulare": tiles, "ordner": str(self._folder())}
        return self._guard(action)

    def oeffnen(self, name: str) -> dict:
        def action():
            platform_utils.open_path(self._file(name))
            return {"ok": True}
        return self._guard(action)

    def im_ordner_zeigen(self, name: str) -> dict:
        def action():
            platform_utils.reveal_path(self._file(name))
            return {"ok": True}
        return self._guard(action)

    def ordner_oeffnen(self) -> dict:
        def action():
            self._prepare()
            platform_utils.open_path(self._folder())
            return {"ok": True}
        return self._guard(action)

    def ersetzen(self, name: str) -> dict:
        """Dateiauswahl; die alte Datei wandert mit Datum im Namen nach formulare/_alt/, die neue bekommt den alten Namen."""
        def pick():
            return self.ctx.choose_file(("PDF-Dateien (*.pdf)",))
        old = self._guard(lambda: {"ok": True, "pdf": self._file(name)})
        if not old.get("ok"):
            return old
        chosen = pick()
        if not chosen:
            return {"ok": False, "error": "cancelled"}

        def action():
            source = Path(chosen)
            if source.suffix.lower() != ".pdf" or not source.is_file():
                raise ValueError("Bitte eine PDF-Datei wählen.")
            target = old["pdf"]
            archive = self._folder() / OLD_DIR
            archive.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            backup = archive / f"{target.stem}_{stamp}.pdf"
            shutil.move(str(target), str(backup))
            try:
                shutil.copyfile(source, target)
            except OSError:
                shutil.move(str(backup), str(target))  # nichts verlieren
                raise
            return {"ok": True, "alt": str(backup)}
        return self._guard(action)
