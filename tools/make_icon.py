"""Erzeugt assets/sos-logo.ico aus assets/sos-logo.svg (für das Icon der .exe).

Aufruf: python tools/make_icon.py [svg] [ico]
Scheitert die Umwandlung, wird die .exe einfach ohne eigenes Icon gebaut.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = [16, 24, 32, 48, 64, 128, 256]


def make_icon(svg: Path, ico: Path) -> None:
    import pymupdf  # nur für den Build nötig (requirements-build.txt)
    from PIL import Image

    page = pymupdf.open(str(svg))[0]
    zoom = 512 / max(page.rect.width, page.rect.height)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")
    # Auf ein weißes Quadrat setzen, damit das Logo nicht verzerrt wird.
    square = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
    square.paste(image, ((512 - image.width) // 2, (512 - image.height) // 2))
    square.save(ico, format="ICO", sizes=[(s, s) for s in SIZES])


def main() -> int:
    svg = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "sos-logo.svg"
    ico = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "assets" / "sos-logo.ico"
    if ico.exists():
        print(f"Icon vorhanden: {ico}")
        return 0
    if not svg.exists():
        print(f"Kein Logo gefunden ({svg}). Die .exe wird ohne eigenes Icon gebaut.")
        return 0
    try:
        make_icon(svg, ico)
    except Exception as exc:  # fehlende Bibliothek oder ungewöhnliche SVG-Datei
        print(f"Das Icon konnte nicht erzeugt werden: {exc}")
        print("Die .exe wird ohne eigenes Icon gebaut. Alternativ eine fertige assets/sos-logo.ico ablegen.")
        return 0
    print(f"Icon erzeugt: {ico}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
