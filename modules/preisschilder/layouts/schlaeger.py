"""Schild "Schlaeger" (reportlab), nachgebaut nach dem Druck von referenz/SOS_Tennis_Generator.html.

Alle Masse stehen in CSS-Pixeln wie im HTML (1 px = 0,75 pt = 0,2646 mm) und sind an den Ausdruck des HTML
in Chrome angelegt (Vergleichs-PDF: referenz/schlaeger-chrome-druck.pdf, siehe tests/test_layouts.py).

Karte: Rahmen 1 px #ccc mit Eckradius 4 px, Kopfband in der Markenfarbe (62 px hoch, weisses Logo 34 px hoch),
darunter Name, Datenraster 2 x 2 und die Preiszeile. Die Hoehe ist fest (258 px); sehr lange Namen werden
verkleinert statt umgebrochen."""
from __future__ import annotations

import os
import unicodedata

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .. import sheet

PX = 0.75  # pt je CSS-Pixel
CARD_W_PX, CARD_H_PX = 347.0, 258.0  # Schildmass wie im Chrome-Ausdruck (91,8 x 68,3 mm)
CARD_W_MM, CARD_H_MM = round(CARD_W_PX * PX / mm, 1), round(CARD_H_PX * PX / mm, 1)
GAP = 10 * PX  # Abstand zwischen den Schildern
MARGIN_X, MARGIN_Y = 12 * mm, 10 * mm  # Blattrand links/rechts und oben/unten
PER_PAGE_COLS = 2

BRANDS = {"Wilson": "#c00000", "HEAD": "#000000", "Babolat": "#1a5fa8", "Yonex": "#003087", "Tecnifibre": "#1a2b6b"}
COLOR_PRESETS = ["#c00000", "#000000", "#1a5fa8", "#003087", "#1a2b6b", "#2e7d32", "#e65100", "#6a1b9a", "#555555", "#333333"]

IN2_CM2 = {"85": "548", "90": "581", "93": "600", "95": "613", "97": "626", "98": "632", "99": "639", "100": "645",
           "101": "652", "102": "658", "103": "665", "104": "671", "105": "677", "107": "690", "108": "697",
           "110": "710", "115": "742", "116": "748"}

DASH = "—"
BOLD, REG = "Helvetica-Bold", "Helvetica"


def cm2_from_in(text: str) -> str:
    """Kopfgroesse in Quadratzoll -> cm² (Tabelle, sonst Wert x 6,4516 gerundet). Leer oder unlesbar -> ''."""
    value = (text or "").strip()
    if value in IN2_CM2:
        return IN2_CM2[value]
    try:
        return str(int(float(value.replace(",", ".")) * 6.4516 + 0.5)) if value else ""
    except ValueError:
        return ""


def kopf_text(it: dict) -> str:
    parts = []
    if it.get("kopfIn"):
        parts.append(f"{it['kopfIn']} in²")
    if it.get("kopfCm"):
        parts.append(f"{it['kopfCm']} cm²")
    return " / ".join(parts) or DASH


def _fmt(value, unit) -> str:
    return f"{value} {unit}" if value else DASH


def logo_file(marke: str) -> str:
    """Dateiname des weissen Markenlogos im Ordner logos/Schläger: wilson.png, head.png ..."""
    return unicodedata.normalize("NFC", (marke or "").strip().lower().replace(" ", "")) + ".png"


def _logo_path(marke):
    if not marke:
        return None
    folder = os.path.join(sheet.LOGO_DIR, unicodedata.normalize("NFC", "Schläger"))
    for base in (folder, unicodedata.normalize("NFD", folder)):
        path = os.path.join(base, logo_file(marke))
        if os.path.isfile(path):
            return path
    return None


def _fit(text, font, size_px, max_px, min_px=8):
    while size_px > min_px and stringWidth(text, font, size_px * PX) > max_px * PX:
        size_px -= 0.5
    return size_px


def draw(c, w, h, it):
    """Zeichnet ein Schild in die Box w x h (Punkt, Ursprung links unten)."""
    W = w / PX  # Breite in px; vertikal zaehlt der Abstand vom oberen Rand
    top = h  # PDF-y des oberen Randes
    pad = 18  # seitlicher Innenabstand
    left, right = 1 + pad, W - 1 - pad

    def y(px_from_top):
        return top - px_from_top * PX

    # Hintergrund und Zuschnitt auf den Rahmen (Eckradius 4 px)
    c.saveState()
    clip = c.beginPath()
    clip.roundRect(0, 0, w, h, 4 * PX)
    c.clipPath(clip, stroke=0, fill=0)
    c.setFillColor(HexColor("#ffffff"))
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColor(HexColor(it.get("farbe") or "#555555"))
    c.rect(0, y(1 + 62), w, 62 * PX, stroke=0, fill=1)
    c.restoreState()

    # Markenlogo (weiss) zentriert im Kopfband: 34 px hoch, hoechstens 180 px breit
    logo = _logo_path(it.get("marke"))
    if logo:
        try:
            iw, ih = ImageReader(logo).getSize()
            lw = min(34 * iw / ih, 180)
            lh = min(34, lw * ih / iw)
            c.drawImage(logo, (w - lw * PX) / 2, y(1 + 14 + 17 + lh / 2), lw * PX, lh * PX, mask="auto")
        except Exception:  # noqa: BLE001 - defektes Logo: Schild ohne Logo
            pass

    # Name
    name = it.get("name", "") or DASH
    c.setFillColor(HexColor("#111111"))
    size = _fit(name, BOLD, 17, right - left)
    c.setFont(BOLD, size * PX)
    c.drawString(left * PX, y(92), name)
    c.setFillColor(HexColor("#dddddd"))
    c.rect(left * PX, y(106), (right - left) * PX, 1 * PX, stroke=0, fill=1)

    # Datenraster 2 x 2
    col = (right - left - 16) / 2
    x2 = left + col + 16
    grid = [(left, 125, 145, "Kopf", kopf_text(it)), (x2, 125, 145, "Gewicht", _fmt(it.get("gewicht"), "g")),
            (left, 162, 182, "Besaitung", it.get("besaitung") or DASH), (x2, 162, 182, "Balance", _fmt(it.get("balance"), "mm"))]
    for x, y_label, y_value, label, value in grid:
        c.setFillColor(HexColor("#888888"))
        c.setFont(REG, 10 * PX)
        c.drawString(x * PX, y(y_label), label)
        c.setFillColor(HexColor("#111111"))
        c.setFont(BOLD, _fit(value, BOLD, 13, col) * PX)
        c.drawString(x * PX, y(y_value), value)

    # Preiszeile
    c.setFillColor(HexColor("#dddddd"))
    c.rect(left * PX, y(196), (right - left) * PX, 1 * PX, stroke=0, fill=1)
    c.setFillColor(HexColor("#555555"))
    t = c.beginText(left * PX, y(213))
    t.setFont(BOLD, 9 * PX)
    t.setCharSpace(1 * PX)
    t.textOut("UNSER PREIS")
    t.setCharSpace(0)  # der Zeichenabstand bleibt sonst im Grafikzustand und verbreitert alle folgenden Texte
    c.drawText(t)
    c.setFillColor(HexColor("#111111"))
    preis = sheet.euro(it.get("preis", "")) or DASH
    c.setFont(BOLD, _fit(preis, BOLD, 26, (right - left) * 0.6) * PX)
    c.drawString(left * PX, y(239), preis)
    if it.get("uvp"):
        uvp = sheet.euro(it["uvp"])
        c.setFillColor(HexColor("#888888"))
        c.setFont(REG, 9 * PX)
        c.drawRightString(right * PX, y(217), "UVP")
        c.setFillColor(HexColor("#cc0000"))
        c.setFont(BOLD, 13 * PX)
        c.drawRightString(right * PX, y(235), uvp)
        c.rect(right * PX - stringWidth(uvp, BOLD, 13 * PX), y(231), stringWidth(uvp, BOLD, 13 * PX), 1 * PX, stroke=0, fill=1)

    # Rahmen: 1 px #ccc, innen bei halber Strichstaerke
    c.setStrokeColor(HexColor("#cccccc"))
    c.setLineWidth(1 * PX)
    c.roundRect(0.5 * PX, 0.5 * PX, w - 1 * PX, h - 1 * PX, 3.5 * PX, stroke=1, fill=0)


def grid_rows(card_h_pt: float) -> int:
    """Wie viele Zeilen auf eine A4-Seite passen (Rand oben/unten 10 mm, Abstand 10 px)."""
    nutz = A4[1] - 2 * MARGIN_Y
    return max(1, int((nutz + GAP + 1e-6) // (card_h_pt + GAP)))


def render_pdf(path, items, w_mm: float = CARD_W_MM, h_mm: float = CARD_H_MM) -> None:
    """A4 hoch, 2 Spalten, Zeilen nach Platz (bei der Standardhoehe 3, also 6 Schilder pro Seite)."""
    if not items:
        raise ValueError("Keine Schilder zum Drucken.")
    w, h = w_mm * mm, h_mm * mm
    rows = grid_rows(h)
    per_page = PER_PAGE_COLS * rows
    x0 = (A4[0] - (PER_PAGE_COLS * w + (PER_PAGE_COLS - 1) * GAP)) / 2
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle("Preisschilder Schläger")
    for i, item in enumerate(items):
        pos = i % per_page
        if i and pos == 0:
            c.showPage()
        x = x0 + (pos % PER_PAGE_COLS) * (w + GAP)
        y_ = A4[1] - MARGIN_Y - (pos // PER_PAGE_COLS + 1) * h - (pos // PER_PAGE_COLS) * GAP
        c.saveState()
        c.translate(x, y_)
        draw(c, w, h, item)
        c.restoreState()
    c.save()
