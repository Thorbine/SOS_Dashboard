"""Kontrolle: Die Schilder aus dem Dashboard muessen visuell identisch mit denen des Altprogramms sein.

Fuer jeden Typ mit denselben Beispieldaten ein PDF mit dem Altcode (referenz/Preisschilder) und eines mit dem
neuen Code erzeugen, beide per pymupdf rendern und die Pixel vergleichen."""
import ast
import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OLD = ROOT / "referenz" / "Preisschilder"

pymupdf = pytest.importorskip("pymupdf")
OLD_DATA_OK = (OLD / "daten" / "logos").is_dir()  # "daten" ist im Altprogramm nicht im Repository
needs_old = pytest.mark.skipif(not OLD_DATA_OK, reason="referenz/Preisschilder/daten fehlt")

from modules.preisschilder import sheet  # noqa: E402
from modules.preisschilder.layouts import DRAW  # noqa: E402

LOGOS = OLD / "daten" / "logos"


def load_old_sheet():
    spec = importlib.util.spec_from_file_location("alt_sheet", OLD / "sheet.py")
    sys.path.insert(0, str(OLD))  # der Altcode importiert "settings"
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(OLD))
    return mod


def load_old_draw(old_sheet, tab_file):
    """Holt draw() (und preis_text) aus dem Quelltext des Tabs, ohne tkinter zu importieren."""
    tree = ast.parse((OLD / tab_file).read_text(encoding="utf-8"))
    ns = {"sheet": old_sheet}
    from reportlab.lib.units import mm
    ns["mm"] = mm
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("preis_text", "draw"):
            code = ast.get_source_segment((OLD / tab_file).read_text(encoding="utf-8"), node)
            exec(textwrap.dedent(code).replace("@staticmethod\n", ""), ns)  # noqa: S102
    return ns["draw"]


def render(pdf_path, dpi=100):
    doc = pymupdf.open(str(pdf_path))
    return [page.get_pixmap(dpi=dpi).samples for page in doc], len(doc)


HELME = json.loads((OLD / "daten" / "liste_helme.json").read_text(encoding="utf-8")) if OLD_DATA_OK else [{}] * 60
SAMPLES = {
    "helme": ((124, 60), [dict(HELME[i], mass1="55-59 cm", statt="199" if i % 3 == 0 else "") for i in range(0, 60, 5)]
              + [{"logo": "", "modell": "Ein sehr langer Modellname Pro Max MIPS", "groesse1": "XL-XXL", "mass1": "59-63 cm", "preis": "1299,5", "statt": "1.499,00"}]),
    "baelle": ((100, 15), [
        {"logo": "", "typ": "DTB-Spielball", "name": "Fort Tournament", "inhalt": "4er Dose", "preis": "8,95", "einzel": "2,24"},
        {"logo": "", "typ": "", "name": "Head Tour", "inhalt": "3er Dose", "preis": "5,95", "einzel": ""},
        {"logo": "", "typ": "Trainingsball", "name": "", "inhalt": "", "preis": "49", "einzel": ""}] * 6),
    "ski": ((70, 90), [
        {"logo": "Ski/Atomic.png", "kategorie": "Allmountain", "modell": "Maverick 86 C", "zusatz1": "incl. Bindung", "zusatz2": "incl. Montage",
         "text1": "Setpreis bei uns", "statt1": "599", "preis1": "449", "text2": "Mit Wunschbindung", "statt2": "", "preis2": "519,5"},
        {"logo": "Ski/Salomon Schriftzug.png", "kategorie": "Race", "modell": "S/Race GS 12", "zusatz1": "", "zusatz2": "", "text1": "", "statt1": "", "preis1": "1100", "text2": "", "statt2": "", "preis2": ""}] * 7),
}
SAMPLES["snowboard"] = ((70, 90), SAMPLES["ski"][1])
OLD_TAB = {"helme": "tab_helme.py", "baelle": "tab_baelle.py", "ski": "tab_ski.py", "snowboard": "tab_ski.py"}


@needs_old
@pytest.mark.parametrize("typ", ["helme", "baelle", "ski", "snowboard"])
def test_new_layout_matches_old_program(typ, tmp_path):
    (w, h), items = SAMPLES[typ]
    old_sheet = load_old_sheet()
    old_sheet.settings.LOGO_DIR = str(LOGOS)
    sheet.LOGO_DIR = str(LOGOS)
    alt, neu = tmp_path / "alt.pdf", tmp_path / "neu.pdf"
    old_sheet.render_pdf(str(alt), w, h, items, load_old_draw(old_sheet, OLD_TAB[typ]), 10, 0)
    sheet.render_pdf(str(neu), w, h, items, DRAW[typ], 10, 0)
    (pix_alt, n_alt), (pix_neu, n_neu) = render(alt), render(neu)
    assert n_alt == n_neu >= 1
    assert pix_alt == pix_neu, f"{typ}: die Seiten unterscheiden sich"
    assert any(set(p) != {255} for p in pix_neu), "die Seiten sind leer"


# ----- Schlaeger: Vergleich mit dem Chrome-Ausdruck des HTML-Generators -----

from modules.preisschilder.layouts import schlaeger  # noqa: E402

BRAND_NAME = {"wilson": "Wilson", "head": "HEAD", "babolat": "Babolat", "yonex": "Yonex", "tecnifibre": "Tecnifibre"}


def racket_items():
    cards = json.loads((ROOT / "referenz" / "schlaeger-beispiel.json").read_text(encoding="utf-8"))
    return [dict(marke=BRAND_NAME[c["brand"]], farbe=c["color"], name=c["name"], kopfIn=c["kopfIn"], kopfCm=c["kopfCm"],
                 gewicht=c["gewicht"], besaitung=c["besaitung"], balance=c["balance"], preis=c["preis"], uvp=c["uvp"]) for c in cards]


def text_spans(page):
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            out += [(s["text"], s["origin"][0], s["origin"][1], s["size"]) for s in line["spans"]]
    return out


def test_racket_layout_matches_chrome_print(tmp_path):
    sheet.LOGO_DIR = str(ROOT / "assets" / "preisschilder" / "logos")
    pdf = tmp_path / "schlaeger.pdf"
    schlaeger.render_pdf(str(pdf), racket_items())
    neu, ref = pymupdf.open(str(pdf)), pymupdf.open(str(ROOT / "referenz" / "schlaeger-chrome-druck.pdf"))
    assert len(neu) == len(ref) == 2  # 7 Schilder: 6 auf der ersten Seite
    for page_new, page_ref in zip(neu, ref):
        new, old = text_spans(page_new), text_spans(page_ref)
        assert sorted(t for t, *_ in new) == sorted(t for t, *_ in old)
        for text in {t for t, *_ in old}:
            for a, b in zip(sorted(s for s in old if s[0] == text), sorted(s for s in new if s[0] == text)):
                assert abs(a[1] - b[1]) < 0.3 and abs(a[2] - b[2]) < 0.3 and abs(a[3] - b[3]) < 0.05, (text, a, b)


def test_racket_card_size_and_six_per_page():
    assert (schlaeger.CARD_W_MM, schlaeger.CARD_H_MM) == (91.8, 68.3)
    assert schlaeger.grid_rows(schlaeger.CARD_H_MM * 2.834645669) == 3  # 2 Spalten x 3 Zeilen = 6


def test_racket_head_cm2_table():
    assert schlaeger.cm2_from_in("98") == "632"
    assert schlaeger.cm2_from_in("106") == "684"  # nicht in der Tabelle: 106 x 6,4516
    assert schlaeger.cm2_from_in("") == "" and schlaeger.cm2_from_in("abc") == ""
    assert schlaeger.kopf_text({"kopfIn": "98", "kopfCm": "632"}) == "98 in² / 632 cm²"
    assert schlaeger.kopf_text({}) == "—"


def test_racket_missing_logo_still_prints(tmp_path):
    sheet.LOGO_DIR = str(tmp_path)  # leer
    schlaeger.render_pdf(str(tmp_path / "x.pdf"), [{"marke": "Unbekannt", "name": "Test", "preis": "1"}])
    assert (tmp_path / "x.pdf").stat().st_size > 1000
