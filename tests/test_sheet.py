"""Rechenkern der Preisschilder (aus dem Altprogramm uebernommen) und die Logo-Ordner."""
import os
import re
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.preisschilder import csv_import, settings, sheet  # noqa: E402
from modules.preisschilder.layouts.helme import anlegen_groessen  # noqa: E402
from modules.preisschilder.layouts.ski import preis_text  # noqa: E402


def test_grid():
    # A4 210x297, Rand 10 -> nutzbar 190x277
    assert sheet.grid(95, 60, 10, 0) == (2, 4, False)  # 8 Stueck, gedreht nur 6
    assert sheet.grid(100, 60, 10, 0) == (3, 2, True)  # gedreht 6 statt 1*4
    assert sheet.pro_blatt(70, 40, 10, 0) == 12
    # Abstand zaehlt nur zwischen den Schildern: 3*60 + 2*5 = 190 passt genau
    assert sheet.grid(60, 50, 10, 5) == (3, 5, False)
    with pytest.raises(ValueError):
        sheet.grid(250, 250, 10, 0)


def test_euro():
    assert sheet.euro("199,9") == "199,90 €"
    assert sheet.euro("5") == "5,00 €"
    assert sheet.euro("289,95 €") == "289,95 €"
    assert sheet.euro("abc") == "abc"


def test_ski_price_text():
    assert preis_text("899") == "899,- €"
    assert preis_text("1100") == "1.100,- €"
    assert preis_text("199,90") == "199,90 €"
    assert preis_text("") == ""


def test_pdf_pages(tmp_path):
    p = tmp_path / "t.pdf"
    n = sheet.pro_blatt(100, 60, 10, 0)
    sheet.render_pdf(str(p), 100, 60, list(range(n + 1)), lambda c, w, h, it: None)
    assert len(re.findall(rb"/Type /Page(?!s)", p.read_bytes())) == 2  # n+1 Schilder -> 2 Seiten


def test_logos_with_common_folder(tmp_path):
    (tmp_path / "Helme").mkdir()
    for pfad in ("Helme/a.png", "Helme/b.txt", "gemeinsam.jpg"):
        (tmp_path / pfad).write_bytes(b"")
    assert settings.logos(tmp_path, "helme") == ["Helme/a.png", "gemeinsam.jpg"]
    assert settings.logos(tmp_path, "ski") == ["gemeinsam.jpg"]


def test_logo_folders_are_created_with_umlauts(tmp_path):
    settings.logo_ordner_anlegen(tmp_path)
    names = sorted(unicodedata.normalize("NFC", p.name) for p in tmp_path.iterdir())
    assert names == ["Helme", "Ski", "Snowboards", "Schläger", "Tennisbälle"] or set(names) == {"Helme", "Ski", "Snowboards", "Schläger", "Tennisbälle"}
    (tmp_path / unicodedata.normalize("NFD", "Schläger") / "x.png").write_bytes(b"")
    assert settings.logos(tmp_path, "schlaeger") == ["Schläger/x.png"]  # NFD auf der Platte, NFC im Ergebnis


def test_helm_csv_import(tmp_path):
    kopf = "Art.-Nr.;Herst.kurz;Bez.;H.-Art.-Nr.;Orig. Farbe;Saison;SVK-P;RVK-P"
    zeilen = ["1;SALOMO;L1;DRIVER PRIME;black;H/W 2025;360,00;", "2;SALOMO;L1;Driver Prime;white;H/W 2026;380,00;",
              "3;POC;P1;Obex MIPS;black;H/W 2026;210,00;149,00", "4;POC;P1;Obex MIPS;grey;H/W 2026;210,00;149,00", "5;SOSSPO;;RTL Helm;;;20,00;"]
    pfad = tmp_path / "h.csv"
    pfad.write_text("\n".join([kopf] + zeilen), encoding="cp1252")
    items = csv_import.lese_helme(str(pfad), ["Helme/Salomon Schriftzug.png", "Helme/Salomon.png", "Helme/POC.png"])
    assert [(i["logo"], i["modell"], i["preis"], i["statt"]) for i in items] == [
        ("Helme/Salomon.png", "Driver Prime", "380", ""), ("Helme/POC.png", "Obex MIPS", "149", "210")]
    assert csv_import.zusammenfuehren(items, [dict(items[0])]) == 0


def test_sizes_are_created_per_model():
    g = ["XS-S", "S-M", "M-L"]
    items = [dict(logo="a", modell="Gems", preis="1"), dict(logo="a", modell="Alto", groesse1="M-L", mass1="55"),
             dict(logo="b", modell="Gems", preis="3")]
    assert anlegen_groessen(items, g) == 6
    assert [(i["logo"], i["modell"], i["groesse1"]) for i in items] == [
        ("a", "Gems", "XS-S"), ("a", "Gems", "S-M"), ("a", "Gems", "M-L"),
        ("a", "Alto", "XS-S"), ("a", "Alto", "S-M"), ("a", "Alto", "M-L"),
        ("b", "Gems", "XS-S"), ("b", "Gems", "S-M"), ("b", "Gems", "M-L")]
    assert [i for i in items if i["modell"] == "Alto" and i["groesse1"] == "M-L"][0]["mass1"] == "55"
    assert anlegen_groessen(items, g) == 0
