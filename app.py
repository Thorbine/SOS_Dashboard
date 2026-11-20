"""SOS Dashboard: Grundgerüst. Fenster, Modullader und die JS-API für die Oberfläche.

Jedes Modul liegt in modules/<name>/ (module.json, backend.py, web/). Die öffentlichen Methoden der
Klasse Backend erscheinen in der Oberfläche als <name>_<methode>(), zum Beispiel hersteller_laden().
"""

from __future__ import annotations

import importlib
import json
import sys
import threading
import traceback
import types
from pathlib import Path

import config
import platform_utils
import updater

WINDOW_TITLE = "SOS Dashboard"


def base_dir() -> Path:
    """Projektordner bzw. der entpackte Ordner in der PyInstaller-App."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def discover_modules(root: Path | None = None) -> list[dict]:
    """Findet alle Module (Ordner mit module.json), sortiert nach `reihenfolge`."""
    root = root or base_dir() / "modules"
    found = []
    for info in sorted(root.glob("*/module.json")):
        try:
            meta = json.loads(info.read_text(encoding="utf-8"))
            mid = str(meta["id"])
            title = str(meta.get("titel", mid))
        except (OSError, ValueError, KeyError):
            continue
        web = info.parent / "web"
        found.append({
            "id": mid, "titel": title, "reihenfolge": meta.get("reihenfolge", 100), "dir": info.parent,
            "js": sorted(p.name for p in web.glob("*.js")), "css": sorted(p.name for p in web.glob("*.css")),
        })
    return sorted(found, key=lambda m: (m["reihenfolge"], m["id"]))


class Context:
    """Was ein Modul vom Grundgerüst braucht."""

    def __init__(self, api: "Api"):
        self._api = api
        self.base_dir = base_dir()

    @property
    def data_dir(self):
        return config.get_data_dir()

    def _dialog(self, kind: str, legacy: str, **kwargs):
        import webview

        dialog = getattr(getattr(webview, "FileDialog", None), kind, None) or getattr(webview, legacy)
        chosen = self._api._window.create_file_dialog(dialog, **kwargs)
        return (chosen[0] if isinstance(chosen, (list, tuple)) else chosen) if chosen else None

    def choose_file(self, file_types=()):
        return self._dialog("OPEN", "OPEN_DIALOG", file_types=file_types)

    def choose_folder(self):
        return self._dialog("FOLDER", "FOLDER_DIALOG")

    def save_file(self, name: str, file_types=()):
        return self._dialog("SAVE", "SAVE_DIALOG", save_filename=name, file_types=file_types)


def _guarded(name: str, func):
    """Fängt unerwartete Fehler ab, schreibt sie ins Fehlerprotokoll und gibt eine verständliche Meldung zurück."""
    def call(self, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:  # noqa: BLE001
            platform_utils.log_error(f"{name}\n{traceback.format_exc()}")
            return {"ok": False, "error": "unexpected",
                    "message": "Es ist ein unerwarteter Fehler aufgetreten. Die Einzelheiten stehen in "
                               f"{platform_utils.config_dir() / 'fehlerprotokoll.txt'}."}
    call.__name__ = name
    return call


class Api:
    """Alles, was die Oberfläche über window.pywebview.api aufruft. Rückgabe immer als dict mit 'ok'."""

    def __init__(self, module_dir: Path | None = None):
        self._window = None
        self.restart_requested = False
        self._modules = discover_modules(module_dir)
        self._ctx = Context(self)
        self._backends = {}
        for meta in self._modules:
            try:
                backend = importlib.import_module(f"modules.{meta['id']}.backend").Backend(self._ctx)
            except Exception:  # noqa: BLE001
                platform_utils.log_error(f"Modul {meta['id']} lässt sich nicht laden\n{traceback.format_exc()}")
                continue
            self._backends[meta["id"]] = backend
            for attr in dir(backend):
                if attr.startswith("_") or not callable(getattr(backend, attr)):
                    continue
                name = f"{meta['id']}_{attr}"
                setattr(self, name, types.MethodType(_guarded(name, getattr(backend, attr)), self))

    # ----- Grundgerüst -----

    def grundgeruest_status(self) -> dict:
        return {"ok": True, "dataDir": config.get_data_dir(), "version": updater.current_version(base_dir()),
                "canUpdate": updater.can_update(base_dir())}

    def grundgeruest_module(self) -> dict:
        """Die gefundenen Module samt ihren Oberflächen-Dateien (Pfade relativ zu web/index.html)."""
        return {"ok": True, "modules": [
            {"id": m["id"], "titel": m["titel"],
             "js": [f"../modules/{m['id']}/web/{f}" for f in m["js"]],
             "css": [f"../modules/{m['id']}/web/{f}" for f in m["css"]]}
            for m in self._modules if m["id"] in self._backends]}

    def grundgeruest_datenordner_waehlen(self) -> dict:
        """Ordnerauswahl; der gewählte Pfad wird für diesen Rechner gemerkt."""
        folder = self.ordner_waehlen()["pfad"]
        if not folder:
            return {"ok": False, "error": "cancelled"}
        config.set_data_dir(folder)
        return {"ok": True, "dataDir": folder}

    def grundgeruest_update_pruefen(self) -> dict:
        """Fragt bei GitHub nach einer neueren Programmversion."""
        try:
            return {"ok": True, **updater.check(current=updater.current_version(base_dir()))}
        except updater.UpdateError as exc:
            return {"ok": False, "error": "update", "message": str(exc)}

    def grundgeruest_update_installieren(self) -> dict:
        """Lädt und prüft die neue Version, ersetzt die Programmdateien; danach schließt sich das Fenster und das Programm startet neu."""
        try:
            version = updater.install(current=updater.current_version(base_dir()), target=base_dir())
        except updater.UpdateError as exc:
            return {"ok": False, "error": "update", "message": str(exc)}
        self.restart_requested = True
        threading.Timer(1.0, self._window.destroy).start()  # Zeit für die Antwort an die Oberfläche
        return {"ok": True, "version": version}

    # ----- Dienste für alle Module -----

    def ordner_waehlen(self) -> dict:
        folder = self._ctx.choose_folder()
        return {"ok": bool(folder), "pfad": folder}

    def datei_oeffnen(self, pfad: str) -> dict:
        try:
            platform_utils.open_path(pfad)
        except OSError as exc:
            return {"ok": False, "error": "io", "message": f"Das Öffnen ist fehlgeschlagen: {exc}"}
        return {"ok": True}

    def url_oeffnen(self, url: str) -> dict:
        if not platform_utils.open_url(url):
            return {"ok": False, "error": "bad_url", "message": "Dieser Link kann nicht geöffnet werden."}
        return {"ok": True}


def selftest() -> int:
    """Prüft ohne Fenster, ob im gebauten Programm alles Nötige enthalten ist (Aufruf mit --selftest)."""
    import tempfile

    import webview  # noqa: F401
    from modules.hersteller import csv_import, documents  # noqa: F401

    web = base_dir() / "web"
    missing = [name for name in ("index.html", "style.css", "shell.js") if not (web / name).is_file()]
    api = Api()
    names = [m["id"] for m in api._modules]
    if sorted(api._backends) != sorted(names) or "hersteller" not in names:
        missing.append("Module (" + ", ".join(sorted(set(names) - set(api._backends))) + ")")
    for meta in api._modules:
        missing += [f"{meta['id']}/web/{f}" for f in meta["js"] if not (meta["dir"] / "web" / f).is_file()]
        if not meta["js"]:
            missing.append(f"{meta['id']}/web/*.js")
    if missing:
        print("Selbsttest fehlgeschlagen, es fehlen:", ", ".join(missing))
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        pdfs = documents.write_samples(tmp)
        ok = all(p.stat().st_size > 1000 for p in pdfs)
        if ok:  # Preisschilder-Schilder und PDF-Vorschau (pymupdf)
            import io

            import pymupdf
            from modules.preisschilder import sheet
            from modules.preisschilder.layouts import DRAW, schlaeger

            sheet.LOGO_DIR = tmp
            sample = {"modell": "Test", "groesse1": "M", "preis": "99", "name": "Test", "marke": "Wilson", "preis1": "99"}
            buf = io.BytesIO()
            sheet.render_pdf(buf, 124, 60, [sample], DRAW["helme"])
            racket = Path(tmp) / "s.pdf"
            schlaeger.render_pdf(str(racket), [sample])
            ok = len(pymupdf.open(stream=buf.getvalue(), filetype="pdf")) == 1 and racket.stat().st_size > 1000
    if not ok:
        print("Selbsttest fehlgeschlagen: PDF leer")
        return 1
    print("Selbsttest in Ordnung, Version", updater.current_version(base_dir()) or "Entwicklung", "- Module:", ", ".join(names))
    return 0


def guitest() -> int:
    """Öffnet das Fenster kurz, prüft per JavaScript, ob alle Module eingehängt sind, und schließt es wieder."""
    import time

    import webview

    result = {"ok": False}
    api = Api()
    url = (base_dir() / "web" / "index.html").as_uri() + "?app=1"
    window = webview.create_window(WINDOW_TITLE, url, js_api=api, width=1280, height=820)
    api._window = window

    def check():
        for _ in range(60):
            time.sleep(0.5)
            try:
                found = window.evaluate_js("JSON.stringify({m: MODULES.map(x => x.id), nav: document.querySelectorAll('#nav button').length,"
                                           " roots: document.querySelectorAll('.module-root').length, side: !!document.querySelector('.sidebar')})")
            except Exception:  # noqa: BLE001
                continue
            if found:
                result.update(json.loads(found), ok=True)
                if len(result["m"]) >= len(api._modules) and result["side"]:
                    break  # alle Module sind eingehängt
        window.destroy()

    webview.start(check)
    print(json.dumps(result, ensure_ascii=False))
    ok = result["ok"] and result.get("m") == [m["id"] for m in api._modules] and result.get("side")
    return 0 if ok else 1


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--guitest" in sys.argv:
        sys.exit(guitest())

    import webview

    api = Api()
    url = (base_dir() / "web" / "index.html").as_uri() + "?app=1"
    api._window = webview.create_window(WINDOW_TITLE, url, js_api=api, width=1280, height=820, min_size=(1000, 650))
    # reportlab im Hintergrund vorladen, damit das erste PDF nicht mehrere Sekunden braucht.
    threading.Thread(target=lambda: importlib.import_module("modules.hersteller.documents"), daemon=True).start()
    webview.start()
    if api.restart_requested:  # nach einem Update: mit dem neuen Stand neu starten
        updater.restart()


if __name__ == "__main__":
    main()
