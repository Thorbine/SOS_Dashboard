"""Backend des Moduls Preisschilder ueber die JS-API (Api.preisschilder_*), ohne Fenster."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import platform_utils  # noqa: E402
from app import Api  # noqa: E402

OLD_DATA = ROOT / "referenz" / "Preisschilder" / "daten"
needs_old = pytest.mark.skipif(not OLD_DATA.is_dir(), reason="referenz/Preisschilder/daten fehlt (nicht im Repository)")


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("SOS_DASHBOARD_CONFIG_DIR", str(tmp_path / "config"))
    data = tmp_path / "Daten"
    data.mkdir()
    config.set_data_dir(str(data))
    instance = Api()
    instance.opened = []
    monkeypatch.setattr(platform_utils, "open_path", lambda p: instance.opened.append(Path(p)))
    instance.data = data
    return instance


def test_start_creates_folders_and_default_racket_logos(api):
    res = api.preisschilder_start()
    assert res["ok"] and res["einstellungen"]["helme"] == {"breite": 124, "hoehe": 60}
    base = api.data / "preisschilder" / "logos"
    assert {p.name for p in base.iterdir()} >= {"Helme", "Ski", "Snowboards"}
    racket = [p for p in base.iterdir() if p.name.startswith("Schl")][0]
    assert sorted(f.name for f in racket.iterdir()) == ["babolat.png", "head.png", "tecnifibre.png", "wilson.png", "yonex.png"]


def test_list_roundtrip_strips_runtime_fields_and_detects_conflict(api):
    items = [{"logo": "Helme/a.png", "modell": "Gems", "groesse1": "S-M", "mass1": "", "preis": "180", "statt": "", "_blatt": 3}]
    assert api.preisschilder_liste_laden("helme")["items"] == []
    assert api.preisschilder_liste_speichern("helme", items)["ok"]
    saved = json.loads((api.data / "preisschilder" / "liste_helme.json").read_text(encoding="utf-8"))
    assert saved["items"] == [{k: v for k, v in items[0].items() if k != "_blatt"}] and saved["schemaVersion"] == 1 and saved["revision"] >= 1
    other = Api()
    other.preisschilder_liste_laden("helme")
    assert other.preisschilder_liste_speichern("helme", items)["ok"]
    assert api.preisschilder_liste_speichern("helme", items)["error"] == "conflict"
    assert api.preisschilder_liste_kopie_speichern("helme", items)["ok"]
    assert api.preisschilder_liste_laden("gibtsnicht")["ok"] is False


def test_preview_and_print_for_all_types(api):
    api.preisschilder_start()
    samples = {
        "helme": {"logo": "", "modell": "Gems", "groesse1": "S-M", "mass1": "55", "preis": "180", "statt": "199"},
        "baelle": {"logo": "", "typ": "Dose", "name": "Fort", "inhalt": "4er", "preis": "8,95", "einzel": "2,24"},
        "schlaeger": {"marke": "Wilson", "name": "Blade", "kopfIn": "98", "kopfCm": "632", "gewicht": "305", "besaitung": "16/19", "balance": "320", "preis": "289,95", "uvp": "299"},
        "ski": {"logo": "", "kategorie": "Race", "modell": "GS", "preis1": "999"},
        "snowboard": {"logo": "", "kategorie": "Freeride", "modell": "Board", "preis1": "499"},
    }
    for typ, item in samples.items():
        res = api.preisschilder_vorschau(typ, [item] * 25, 1)
        assert res["ok"] and res["bild"].startswith("data:image/png;base64,") and res["seiten"] >= 2, (typ, res)
        assert api.preisschilder_drucken(typ, [item])["ok"]
        assert api.opened[-1].name == f"preisschilder_{typ}.pdf" and api.opened[-1].stat().st_size > 1000
    assert api.preisschilder_vorschau("helme", [])["leer"] is True
    assert api.preisschilder_drucken("helme", [])["ok"] is False


def test_blatt_info_and_settings_validation(api):
    api.preisschilder_start()
    assert api.preisschilder_blatt_info("schlaeger")["pro_blatt"] == 6
    assert api.preisschilder_blatt_info("helme")["pro_blatt"] == 6  # 124 x 60, gedreht
    cfg = api.preisschilder_start()["einstellungen"]
    cfg["helme"] = {"breite": 300, "hoehe": 300}
    assert api.preisschilder_einstellungen_speichern(cfg)["ok"] is False  # passt nicht auf A4
    cfg["helme"] = {"breite": 100, "hoehe": 50}
    cfg["marken"]["Lacoste"] = {"farbe": "#006241"}
    assert api.preisschilder_einstellungen_speichern(cfg)["ok"]
    again = api.preisschilder_start()["einstellungen"]
    assert again["helme"] == {"breite": 100.0, "hoehe": 50.0} and again["marken"]["Lacoste"]["farbe"] == "#006241"


@needs_old
def test_logo_tiles_have_thumbnails(api):
    api.preisschilder_start()
    shutil.copyfile(OLD_DATA / "logos" / "Helme" / "Alpina.png", api.data / "preisschilder" / "logos" / "Helme" / "Alpina.png")
    shutil.copyfile(OLD_DATA / "logos" / "Helme" / "POC.png", api.data / "preisschilder" / "logos" / "gemeinsam.png")
    names = [(l["name"], l["bild"][:22]) for l in api.preisschilder_logos("helme")["logos"]]
    assert names == [("Helme/Alpina.png", "data:image/png;base64,"), ("gemeinsam.png", "data:image/png;base64,")]
    assert [l["name"] for l in api.preisschilder_logos("ski")["logos"]] == ["gemeinsam.png"]
    assert len(api.preisschilder_logos("schlaeger")["logos"]) == 6  # 5 Marken + das gemeinsame Logo


@needs_old
def test_helm_csv_import_and_all_sizes(api, monkeypatch, tmp_path):
    api.preisschilder_start()
    csv_file = tmp_path / "h.csv"
    csv_file.write_text("Art.-Nr.;Herst.kurz;Bez.;H.-Art.-Nr.;Orig. Farbe;Saison;SVK-P;RVK-P\n1;POC;P;Obex MIPS;black;H/W 2026;210,00;149,00\n2;ZZZ;P;Neu Helm;x;H/W 2026;99,00;\n", encoding="cp1252")
    shutil.copyfile(OLD_DATA / "logos" / "Helme" / "POC.png", api.data / "preisschilder" / "logos" / "Helme" / "POC.png")
    monkeypatch.setattr(api._ctx, "choose_file", lambda file_types=(): str(csv_file))
    res = api.preisschilder_helme_csv_importieren()
    assert res["ok"] and res["neu"] == 2 and res["ohne_logo"] == ["Neu Helm"]
    assert api.preisschilder_helme_csv_importieren()["neu"] == 0  # nichts doppelt
    sizes = api.preisschilder_helme_alle_groessen()
    assert sizes["neu"] == 8 and len(sizes["items"]) == 10
    assert api.preisschilder_liste_laden("helme")["items"] == sizes["items"]


def test_saved_pages_export_import(api, monkeypatch, tmp_path):
    pages = [{"name": "Frühjahr", "date": "12.11.2026", "cards": [{"name": "Blade", "marke": "Wilson"}]}]
    assert api.preisschilder_seiten_speichern(pages)["ok"]
    assert api.preisschilder_seiten_laden()["items"] == pages
    target = tmp_path / "seiten.json"
    monkeypatch.setattr(api._ctx, "save_file", lambda name, file_types=(): str(target))
    assert api.preisschilder_seiten_exportieren()["anzahl"] == 1
    monkeypatch.setattr(api._ctx, "choose_file", lambda file_types=(): str(target))
    assert api.preisschilder_seiten_importieren()["seiten"] == pages
    target.write_text("[1,2]", encoding="utf-8")
    assert api.preisschilder_seiten_importieren()["ok"] is False


@pytest.mark.skipif(not OLD_DATA.is_dir(), reason="referenz/Preisschilder/daten fehlt")
def test_take_over_old_data_without_loss(api, monkeypatch):
    monkeypatch.setattr(api._ctx, "choose_folder", lambda: str(OLD_DATA))
    plan = api.preisschilder_uebernahme_pruefen()
    assert plan["ok"] and plan["vorhanden"] == 0 and plan["anzahl"] >= 11
    old = json.loads((OLD_DATA / "liste_helme.json").read_text(encoding="utf-8"))
    assert len(old) == 190
    res = api.preisschilder_uebernahme_ausfuehren(str(OLD_DATA))
    assert res["ok"] and res["kopiert"] >= 11
    new = api.preisschilder_liste_laden("helme")["items"]
    assert new == old  # alle 190, keine Aenderung
    base = api.data / "preisschilder" / "logos"
    assert (base / "Helme" / "Alpina.png").is_file() and (base / "Ski" / "Atomic.png").is_file()
    # zweiter Lauf ueberschreibt nichts ohne Rueckfrage
    again = api.preisschilder_uebernahme_ausfuehren(str(OLD_DATA))
    assert again["kopiert"] == 0 and again["uebersprungen"] >= 11
    assert api.preisschilder_uebernahme_pruefen()["vorhanden"] >= 11
    assert api.preisschilder_uebernahme_ausfuehren(str(OLD_DATA), True)["kopiert"] >= 11


def test_take_over_rejects_wrong_folder(api, monkeypatch, tmp_path):
    monkeypatch.setattr(api._ctx, "choose_folder", lambda: str(tmp_path))
    assert api.preisschilder_uebernahme_pruefen()["ok"] is False
