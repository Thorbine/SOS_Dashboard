"""Programm-Update aus dem GitHub-Repository (Mac und Windows). Das Programm laeuft aus dem Quelltext.

Ablauf: neuesten Stand von "main" abfragen -> ZIP laden -> alles pruefen (Aufbau, Pflichtdateien, Python-Syntax)
-> Programmordner einschliesslich Unterordnern (modules/, web/, assets/ ...) ersetzen -> neu starten.
Schlaegt irgendetwas fehl, bleibt der alte Stand erhalten. Der Datenordner des Nutzers liegt ausserhalb des
Programmordners und wird nie angefasst; im Programmordner werden nur bekannte Programmdateien ersetzt."""

from __future__ import annotations

import io
import json
import os
import shutil
import ssl
import stat
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

DEFAULT_REPO = "Thorbine/SOS_Dashboard"
VERSION_FILE = "version.txt"
TIMEOUT = 20
MAX_SIZE = 300 * 1024 * 1024
MANAGED_DIRS = ("modules", "web", "assets", "tools", "SOS Dashboard.app")  # werden rekursiv ersetzt
ROOT_SUFFIXES = (".py",)
ROOT_FILES = {"requirements.txt", "README.md", "CLAUDE.md", "start.command", "start.bat", "beispiel-import.csv", "SOS-Dashboard-Spezifikation.md"}
SKIP_PARTS = {"__pycache__", ".DS_Store", ".git"}
REQUIRED = ("app.py", "storage.py", "updater.py", "modules/hersteller/module.json", "modules/hersteller/backend.py", "web/index.html", "web/shell.js")
EXECUTABLE = ("start.command",)


class UpdateError(Exception):
    """Das Update ist nicht moeglich oder fehlgeschlagen. Die Meldung ist fuer die Oberflaeche gedacht."""


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def current_version(base=None) -> str:
    """Version des laufenden Programms (kurze Commit-ID); "dev" ohne version.txt."""
    try:
        return (Path(base or app_dir()) / VERSION_FILE).read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


def repo() -> str:
    try:
        import config

        return str(config.load_config().get("updateRepo") or os.environ.get("SOS_DASHBOARD_REPO") or DEFAULT_REPO)
    except Exception:  # noqa: BLE001
        return DEFAULT_REPO


def can_update(base=None) -> bool:
    """Aus dem Quelltext (nicht aus einer gebauten App) und mit Schreibrecht im Programmordner."""
    return not getattr(sys, "frozen", False) and os.access(base or app_dir(), os.W_OK)


def _ssl_context():
    """Mac-Python von python.org bringt keine Zertifikate mit -> certifi nutzen."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "SOS-Dashboard-Update"})
    with urllib.request.urlopen(request, timeout=TIMEOUT, context=_ssl_context()) as response:
        return response.read(MAX_SIZE + 1)


def latest(repo_name: str | None = None) -> dict:
    """Neuester Commit auf main: {sha, kurz, notiz}."""
    name = repo_name or repo()
    try:
        data = json.loads(_get(f"https://api.github.com/repos/{name}/commits/main").decode("utf-8"))
        sha = data["sha"]
        note = data["commit"]["message"].splitlines()[0]
    except Exception as exc:  # noqa: BLE001
        raise UpdateError(f"Keine Verbindung zu GitHub oder noch keine Version veröffentlicht ({exc}).") from exc
    return {"sha": sha, "kurz": sha[:7], "notiz": note}


def check(data_dir=None, current: str | None = None, fetch=latest) -> dict:
    """{available, current, version, note, canUpdate}; der erste Parameter bleibt aus Kompatibilitaet zur Oberflaeche."""
    current = current if current is not None else current_version()
    if not can_update():
        return {"available": False, "current": current, "version": None, "canUpdate": False}
    info = fetch()
    return {"available": info["kurz"] != current, "current": current, "version": info["kurz"], "note": info["notiz"], "canUpdate": True}


# ----- ZIP pruefen und anwenden -----

def _managed(rel: str) -> bool:
    """Gehoert diese Datei (Pfad relativ zur Repo-Wurzel) zum Programm?"""
    parts = PurePosixPath(rel).parts
    if not parts or any(p in SKIP_PARTS or p.startswith(".") for p in parts):
        return False
    if len(parts) == 1:
        return rel in ROOT_FILES or rel.endswith(ROOT_SUFFIXES)
    return parts[0] in MANAGED_DIRS


def read_package(zip_bytes: bytes) -> dict[str, tuple[bytes, int]]:
    """Liest das ZIP und gibt {relativer Pfad: (Inhalt, Unix-Rechte)} der Programmdateien zurueck. Prueft alles."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
        if archive.testzip() is not None:
            raise UpdateError("Das heruntergeladene Update ist beschädigt.")
    except zipfile.BadZipFile as exc:
        raise UpdateError("Das heruntergeladene Update ist keine gültige ZIP-Datei.") from exc
    names = [n for n in archive.namelist() if n and not n.endswith("/")]
    if not names:
        raise UpdateError("Das heruntergeladene Update ist leer.")
    root = names[0].split("/")[0] + "/"
    files: dict[str, tuple[bytes, int]] = {}
    total = 0
    for info in archive.infolist():
        if info.is_dir() or not info.filename.startswith(root):
            continue
        rel = info.filename[len(root):]
        pure = PurePosixPath(rel)
        if pure.is_absolute() or ".." in pure.parts or "\\" in rel:
            raise UpdateError("Das Update enthält ungültige Dateipfade und wird nicht installiert.")
        if not _managed(rel):
            continue
        total += info.file_size
        if total > MAX_SIZE:
            raise UpdateError("Das Update ist ungewöhnlich groß und wird nicht installiert.")
        files[rel] = (archive.read(info), (info.external_attr >> 16) & 0o777)
    missing = [r for r in REQUIRED if r not in files]
    if missing:
        raise UpdateError("Das Update ist unvollständig, es fehlen: " + ", ".join(missing))
    for rel, (content, _) in files.items():
        try:
            if rel.endswith(".py"):
                compile(content, rel, "exec")
            elif rel.endswith("module.json"):
                json.loads(content.decode("utf-8"))
        except (SyntaxError, ValueError) as exc:
            raise UpdateError(f"Die Datei {rel} im Update ist fehlerhaft ({exc}); es wurde nichts geändert.") from exc
    return files


def apply_package(files: dict, target: Path, version: str) -> None:
    """Ersetzt die Programmdateien in `target`. Bei einem Fehler wird der alte Stand wiederhergestellt."""
    target = Path(target)
    backup = Path(tempfile.mkdtemp(prefix=".update-alt-", dir=target))
    staging = Path(tempfile.mkdtemp(prefix=".update-neu-", dir=target))
    replaced: list[str] = []   # Dateien, die es vorher gab (Kopie im Backup)
    created: list[str] = []    # Dateien, die neu hinzukamen
    removed: list[str] = []    # veraltete Dateien (Kopie im Backup)
    try:
        for rel, (content, mode) in files.items():  # erst alles in den Zwischenordner schreiben
            path = staging / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            if rel in EXECUTABLE or rel.endswith("/launcher") or (mode & 0o100):
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        for rel in files:
            dest = target / rel
            if dest.exists():
                (backup / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup / rel)
                replaced.append(rel)
            else:
                created.append(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging / rel, dest)
        for top in MANAGED_DIRS:  # veraltete Programmdateien in verwalteten Ordnern entfernen
            base = target / top
            if not base.is_dir():
                continue
            for old in sorted(p for p in base.rglob("*") if p.is_file()):
                rel = old.relative_to(target).as_posix()
                if rel not in files and _managed(rel):
                    (backup / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(old, backup / rel)
                    old.unlink()
                    removed.append(rel)
        tmp = target / (VERSION_FILE + ".neu")
        tmp.write_text(version, encoding="utf-8")
        os.replace(tmp, target / VERSION_FILE)
    except Exception as exc:  # noqa: BLE001 - alles zurueck, nichts halb lassen
        for rel in replaced + removed:
            try:
                (target / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup / rel, target / rel)
            except OSError:
                pass
        for rel in created:
            try:
                (target / rel).unlink()
            except OSError:
                pass
        raise UpdateError(f"Die Aktualisierung ist fehlgeschlagen, der alte Stand bleibt erhalten ({exc}).") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


def install(data_dir=None, bundle=None, current: str | None = None, fetch=latest, download=None, target=None) -> str:
    """Laedt das Update, prueft es und ersetzt die Programmdateien. Gibt die neue Version zurueck.

    Danach muss sich das Programm neu starten (siehe restart())."""
    target = Path(target or app_dir())
    if not can_update(target):
        raise UpdateError("Aktualisieren geht nur, wenn das Programm aus dem Quelltext läuft und der Programmordner beschreibbar ist.")
    info = fetch()
    if info["kurz"] == (current if current is not None else current_version(target)):
        raise UpdateError("Es liegt keine neuere Version vor.")
    try:
        zip_bytes = (download or (lambda: _get(f"https://github.com/{repo()}/archive/refs/heads/main.zip")))()
    except Exception as exc:  # noqa: BLE001
        raise UpdateError(f"Der Download ist fehlgeschlagen: {exc}") from exc
    if len(zip_bytes) > MAX_SIZE:
        raise UpdateError("Das Update ist ungewöhnlich groß und wird nicht installiert.")
    apply_package(read_package(zip_bytes), target, info["kurz"])
    return info["kurz"]


def restart() -> None:
    """Startet das Programm neu (derselbe Interpreter, dieselben Argumente)."""
    os.execv(sys.executable, [sys.executable] + sys.argv)
