"""Alles, was sich zwischen macOS und Windows unterscheidet, an einer Stelle.

Datei öffnen, Datei im Ordner zeigen, Konfigurationsordner, Pfade und Dateinamen.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
import webbrowser
from pathlib import Path

APP_NAME = "SOS-Dashboard"


def config_dir() -> Path:
    """Konfigurationsordner dieses Rechners (liegt nicht im Sync-Ordner)."""
    override = os.environ.get("SOS_DASHBOARD_CONFIG_DIR")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".config" / APP_NAME


def open_path(path) -> None:
    """Öffnet eine Datei oder einen Ordner im Standardprogramm."""
    if hasattr(os, "startfile"):
        os.startfile(str(path))  # Windows
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def reveal_path(path) -> None:
    """Zeigt den Ordner mit markierter Datei (Finder bzw. Explorer)."""
    path = Path(path)
    if sys.platform == "win32":
        subprocess.Popen(f'explorer /select,"{path}"')
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        open_path(path.parent)


def safe_url(raw: str) -> str | None:
    """Ergänzt https:// bei Links ohne Schema. Erlaubt sind nur http, https und mailto."""
    url = (raw or "").strip()
    if not url:
        return None
    if re.match(r"^(https?://|mailto:)", url, re.IGNORECASE):
        return url
    if "://" in url or re.match(r"^(javascript|data|file|vbscript):", url, re.IGNORECASE):
        return None
    return "https://" + url


def open_url(raw: str) -> bool:
    """Öffnet einen Link im Standardbrowser bzw. Mailprogramm. False, wenn der Link nicht erlaubt ist."""
    target = safe_url(raw)
    if not target:
        return False
    if hasattr(os, "startfile"):
        os.startfile(target)
    else:
        webbrowser.open(target)
    return True


def nfc(text: str) -> str:
    """Unicode-Form NFC. macOS liefert Dateinamen mit Umlauten als NFD, das macht beim Sync Doppelte."""
    return unicodedata.normalize("NFC", str(text))


def rel_path(path, base) -> str:
    """Pfad relativ zum Datenordner, immer mit / als Trenner und NFC (so steht er im JSON)."""
    return nfc(Path(path).relative_to(Path(base)).as_posix())


def same_name(a: str, b: str) -> bool:
    """Dateinamen vergleichen, ohne dass NFD und NFC einen Unterschied machen."""
    return nfc(a) == nfc(b)


def log_error(text: str) -> None:
    """Hängt einen Eintrag mit Zeitstempel an fehlerprotokoll.txt im Konfigurationsordner an."""
    from datetime import datetime

    try:
        folder = config_dir()
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / "fehlerprotokoll.txt", "a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat(timespec='seconds')}] {text}\n")
    except OSError:
        pass
