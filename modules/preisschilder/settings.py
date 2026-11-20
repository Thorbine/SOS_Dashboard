"""Schildtypen, Standardmasse und die Logo-Ordner. Keine Oberflaeche.

Die Logos liegen im Datenordner unter preisschilder/logos/<Produkt>/ (z. B. Helme); Logos direkt in
preisschilder/logos/ erscheinen bei allen Produkten. Namen werden auf NFC normalisiert (Schläger)."""
from __future__ import annotations

import os
from pathlib import Path

import platform_utils

# Typ -> (Anzeigename = Ordnername der Logos, Breite mm, Hoehe mm)
TYPEN = {
    "helme": ("Helme", 124, 60),
    "baelle": ("Tennisbälle", 100, 15),
    "schlaeger": ("Schläger", 91.8, 68.3),  # gemessen am Chrome-Ausdruck des HTML-Generators
    "ski": ("Ski", 70, 90),
    "snowboard": ("Snowboards", 70, 90),
}
DEFAULTS = {"rand": 10, "abstand": 0, **{k: {"breite": b, "hoehe": h} for k, (_, b, h) in TYPEN.items()}}
LOGO_ENDUNGEN = (".png", ".jpg", ".jpeg")


def logo_ordner(logo_dir, typ) -> Path:
    """Unterordner fuer die Logos eines Produkts, z. B. logos/Helme."""
    return Path(logo_dir) / platform_utils.nfc(TYPEN[typ][0])


def logo_ordner_anlegen(logo_dir) -> None:
    """Legt logos/ und je einen Unterordner pro Produkt an (damit man sie im Finder findet)."""
    try:
        for typ in TYPEN:
            logo_ordner(logo_dir, typ).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def _bilder(ordner, praefix=""):
    try:
        return sorted(platform_utils.nfc(praefix + f) for f in os.listdir(ordner) if f.lower().endswith(LOGO_ENDUNGEN))
    except OSError:
        return []


def logos(logo_dir, typ=None) -> list[str]:
    """Logos als Pfade relativ zu logos/. Mit typ: erst die des Produkts ("Helme/x.png"), dann die
    gemeinsamen direkt in logos/ ("x.png")."""
    gemeinsam = _bilder(logo_dir)
    if typ is None:
        return gemeinsam
    ordner = platform_utils.nfc(TYPEN[typ][0])
    return _bilder(logo_ordner(logo_dir, typ), ordner + "/") + gemeinsam
