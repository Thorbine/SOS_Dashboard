import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from modules.hersteller import models  # noqa: E402
import storage  # noqa: E402
from storage import (ConflictError, CorruptDataError, DataFileMissingError,  # noqa: E402
                     DataFolderError, Storage, StorageError)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ----- Laden -----

def test_missing_folder_is_an_error_and_creates_nothing(tmp_path):
    target = tmp_path / "gibt-es-nicht"
    with pytest.raises(DataFolderError):
        Storage(target).load(create=True)
    assert not target.exists()


def test_missing_file_is_not_created_silently(tmp_path):
    with pytest.raises(DataFileMissingError):
        Storage(tmp_path).load()
    assert list(tmp_path.iterdir()) == []


def test_create_writes_new_file_with_template(tmp_path):
    data = Storage(tmp_path).load(create=True)
    assert data["suppliers"] == []
    assert [b["title"] for b in data["blockTemplate"]] == ["Infos", "Ansprechpartner", "Adressen", "Links", "Notizen"]
    assert data["company"]["managingDirector"] == "Oliver Nieß"
    assert read(tmp_path / storage.DATA_FILE)["revision"] == 0


def test_existing_file_is_loaded_not_replaced(tmp_path):
    first = Storage(tmp_path)
    data = first.load(create=True)
    data["suppliers"].append(models.new_supplier("Völkl"))
    first.save(data)
    again = Storage(tmp_path).load(create=True)
    assert [s["name"] for s in again["suppliers"]] == ["Völkl"]


def test_corrupt_json_raises_and_is_not_overwritten(tmp_path):
    path = tmp_path / storage.DATA_FILE
    path.write_text('{"suppliers": [', encoding="utf-8")
    st = Storage(tmp_path)
    with pytest.raises(CorruptDataError):
        st.load(create=True)
    with pytest.raises(ConflictError):
        st.save(models.new_data())
    assert path.read_text(encoding="utf-8") == '{"suppliers": ['


def test_load_fills_missing_fields(tmp_path):
    (tmp_path / storage.DATA_FILE).write_text(json.dumps({
        "revision": 7,
        "suppliers": [{"name": "Alt", "blocks": [
            {"type": "contacts", "contacts": [{"name": "Jana"}]},
            {"type": "addresses", "addresses": [{"label": "A"}, {"label": "B"}]},
            {"type": "zukunft", "x": 1},
        ]}],
    }), encoding="utf-8")
    st = Storage(tmp_path)
    data = st.load()
    blocks = data["suppliers"][0]["blocks"]
    assert st.revision == 7
    assert blocks[0]["contacts"][0]["email"] == "" and blocks[0]["visible"] is True
    assert [a["isDefault"] for a in blocks[1]["addresses"]] == [True, False]
    assert blocks[2]["x"] == 1  # unbekannte Blocktypen bleiben erhalten
    assert data["company"]["name"] == "SOS Sport GmbH"


# ----- Speichern -----

def test_roundtrip_keeps_umlauts_and_euro(tmp_path):
    st = Storage(tmp_path)
    data = st.load(create=True)
    supplier = models.new_supplier("Größe & Maß GmbH")
    supplier["blocks"][-1]["text"] = "Mindestbestellwert 250 € – Rückfrage bei Jürgen"
    data["suppliers"].append(supplier)
    st.save(data)
    raw = (tmp_path / storage.DATA_FILE).read_text(encoding="utf-8")
    assert "Größe & Maß GmbH" in raw and "250 €" in raw  # echte Zeichen, keine \\u-Folgen
    loaded = Storage(tmp_path).load()
    assert loaded["suppliers"][0] == supplier


def test_revision_increases_with_every_save(tmp_path):
    st = Storage(tmp_path)
    data = st.load(create=True)
    assert st.save(data) == 1
    assert st.save(data) == 2
    assert read(tmp_path / storage.DATA_FILE)["revision"] == 2
    assert Storage(tmp_path).load()["revision"] == 2


def test_no_tmp_file_left_after_save(tmp_path):
    st = Storage(tmp_path)
    st.save(st.load(create=True))
    assert not list(tmp_path.glob("*.tmp"))


def test_failed_write_keeps_old_file_intact(tmp_path, monkeypatch):
    st = Storage(tmp_path)
    data = st.load(create=True)
    data["suppliers"].append(models.new_supplier("Vorher"))
    st.save(data)
    before = (tmp_path / storage.DATA_FILE).read_bytes()

    def boom(src, dst):
        raise OSError("Platte voll")

    monkeypatch.setattr(os, "replace", boom)
    data["suppliers"].append(models.new_supplier("Nachher"))
    with pytest.raises(StorageError):
        st.save(data)
    monkeypatch.undo()

    assert (tmp_path / storage.DATA_FILE).read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))
    assert st.revision == 1  # fehlgeschlagenes Speichern verbraucht keine Revision
    assert st.save(data) == 2


def test_save_into_vanished_folder_fails(tmp_path):
    folder = tmp_path / "daten"
    folder.mkdir()
    st = Storage(folder)
    data = st.load(create=True)
    (folder / storage.DATA_FILE).unlink()
    folder.rmdir()
    with pytest.raises(DataFolderError):
        st.save(data)
    assert not folder.exists()


# ----- Sync-Schutz -----

def test_conflict_when_other_machine_saved_in_between(tmp_path):
    work, home = Storage(tmp_path), Storage(tmp_path)
    data_work = work.load(create=True)
    data_home = home.load()

    data_home["suppliers"].append(models.new_supplier("Von zuhause"))
    home.save(data_home)

    data_work["suppliers"].append(models.new_supplier("Von der Arbeit"))
    with pytest.raises(ConflictError):
        work.save(data_work)
    assert [s["name"] for s in read(tmp_path / storage.DATA_FILE)["suppliers"]] == ["Von zuhause"]

    # Nach dem Neuladen kann wieder gespeichert werden.
    fresh = work.load()
    fresh["suppliers"].append(models.new_supplier("Von der Arbeit"))
    assert work.save(fresh) == 2


def test_save_copy_writes_separate_file(tmp_path):
    st = Storage(tmp_path)
    data = st.load(create=True)
    data["suppliers"].append(models.new_supplier("Meine Version"))
    copy = st.save_copy(data)
    assert copy.parent == tmp_path and copy.name.startswith("sos-dashboard-daten-kopie-")
    assert read(copy)["suppliers"][0]["name"] == "Meine Version"
    assert read(tmp_path / storage.DATA_FILE)["suppliers"] == []


# ----- Backups -----

def test_one_backup_per_day(tmp_path):
    day = [date(2026, 11, 14)]
    st = Storage(tmp_path, today=lambda: day[0])
    data = st.load(create=True)
    st.save(data)
    st.save(data)
    assert [p.parent.name for p in st.backups()] == ["2026-11-14"]
    assert read(st.backups()[0])["revision"] == 0  # Stand vor der ersten Änderung des Tages

    day[0] = date(2026, 11, 15)
    st.save(data)
    assert [p.parent.name for p in st.backups()] == ["2026-11-14", "2026-11-15"]
    assert read(st.backups()[1])["revision"] == 2


def test_only_last_14_backups_are_kept(tmp_path):
    day = [date(2026, 1, 1)]
    st = Storage(tmp_path, today=lambda: day[0])
    data = st.load(create=True)
    for _ in range(20):
        st.save(data)
        day[0] += timedelta(days=1)
    names = [p.parent.name for p in st.backups()]
    assert len(names) == 14
    assert names[0] == "2026-01-07"
    assert names[-1] == "2026-01-20"


def test_restore_latest_backup_after_corruption(tmp_path):
    day = [date(2026, 11, 13)]
    st = Storage(tmp_path, today=lambda: day[0])
    data = st.load(create=True)
    data["suppliers"].append(models.new_supplier("Gesichert"))
    st.save(data)
    day[0] = date(2026, 11, 14)
    st.save(data)  # Backup vom 14. enthält "Gesichert"

    path = tmp_path / storage.DATA_FILE
    path.write_text("kaputt", encoding="utf-8")
    fresh = Storage(tmp_path)
    with pytest.raises(CorruptDataError):
        fresh.load()
    restored = fresh.restore_latest_backup()
    assert [s["name"] for s in restored["suppliers"]] == ["Gesichert"]
    # Die beschädigte Datei wurde aufbewahrt, nicht gelöscht.
    kept = list(tmp_path.glob("sos-dashboard-daten-ersetzt-*.json"))
    assert len(kept) == 1 and kept[0].read_text(encoding="utf-8") == "kaputt"
    assert fresh.save(restored) == restored["revision"] + 1


def test_restore_without_backup_fails(tmp_path):
    st = Storage(tmp_path)
    st.load(create=True)
    with pytest.raises(StorageError):
        st.restore_latest_backup()


# ----- Modell -----

def test_new_supplier_has_five_default_blocks():
    s = models.new_supplier("Beispiel GmbH")
    assert [(b["type"], b["title"]) for b in s["blocks"]] == [
        ("fields", "Infos"), ("contacts", "Ansprechpartner"), ("addresses", "Adressen"),
        ("links", "Links"), ("notes", "Notizen")]
    assert s["blocks"][0]["fields"][0]["label"] == "Unsere Kundennr"
    assert [a["label"] for a in s["blocks"][2]["addresses"]] == ["Hauptadresse", "Retourenadresse", "Reklamationsadresse"]
    assert [a["isDefault"] for a in s["blocks"][2]["addresses"]] == [True, False, False]
    assert [g["label"] for g in s["blocks"][3]["groups"]] == ["B2B", "Reklamation", "Medien"]
    ids = [s["id"]] + [b["id"] for b in s["blocks"]]
    assert len(set(ids)) == len(ids)


def test_template_change_does_not_touch_existing_suppliers():
    data = models.new_data()
    old = models.new_supplier("Alt", data["blockTemplate"])
    data["blockTemplate"].append({"type": "notes", "title": "Intern"})
    data["blockTemplate"][0]["defaults"].append({"label": "Zahlungsziel", "value": ""})
    new = models.new_supplier("Neu", data["blockTemplate"])
    assert len(old["blocks"]) == 5 and len(old["blocks"][0]["fields"]) == 1
    assert len(new["blocks"]) == 6 and len(new["blocks"][0]["fields"]) == 2
    assert len(models.DEFAULT_BLOCK_TEMPLATE) == 5  # die eingebaute Vorlage bleibt unberührt


def test_exactly_one_default_address():
    addresses = [models.new_address(label="A", isDefault=True), models.new_address(label="B", isDefault=True)]
    models.ensure_single_default(addresses)
    assert [a["isDefault"] for a in addresses] == [True, False]
    single = [models.new_address(label="Einzige")]
    models.ensure_single_default(single)
    assert single[0]["isDefault"] is True


# ----- Konfiguration und JS-API -----

@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    folder = tmp_path / "config"
    monkeypatch.setenv("SOS_DASHBOARD_CONFIG_DIR", str(folder))
    return folder


def test_config_remembers_data_dir(cfg_dir, tmp_path):
    assert config.get_data_dir() is None
    config.set_data_dir(str(tmp_path / "Daten ÄÖÜ"))
    assert config.get_data_dir() == str(tmp_path / "Daten ÄÖÜ")
    assert (cfg_dir / "config.json").exists()


def test_api_load_save_cycle(cfg_dir, tmp_path):
    from app import Api

    data_dir = tmp_path / "daten"
    api = Api()
    assert api.hersteller_laden()["error"] == "no_folder"

    config.set_data_dir(str(data_dir))
    assert api.hersteller_laden()["error"] == "folder_unreachable"
    assert not data_dir.exists()

    data_dir.mkdir()
    assert api.hersteller_laden()["error"] == "file_missing"
    res = api.hersteller_datei_anlegen()
    assert res["ok"] and res["dataDir"] == str(data_dir)

    res["data"]["suppliers"].append(models.new_supplier("Über die API"))
    assert api.hersteller_speichern(res["data"]) == {"ok": True, "revision": 1}

    # Neustart: alles ist unverändert vorhanden.
    again = Api().hersteller_laden()
    assert again["ok"] and again["data"]["suppliers"][0]["name"] == "Über die API"

    # Zweite Instanz hat inzwischen gespeichert: Konflikt statt Überschreiben.
    other = Api()
    other_data = other.hersteller_laden()["data"]
    other.hersteller_speichern(other_data)
    assert api.hersteller_speichern(res["data"])["error"] == "conflict"
    assert api.hersteller_kopie_speichern(res["data"])["ok"]


def test_api_reports_backup_for_corrupt_file(cfg_dir, tmp_path):
    from app import Api

    config.set_data_dir(str(tmp_path))
    api = Api()
    data = api.hersteller_datei_anlegen()["data"]
    api.hersteller_speichern(data)
    (tmp_path / storage.DATA_FILE).write_text("{", encoding="utf-8")
    res = Api().hersteller_laden()
    assert res["error"] == "corrupt" and res["backup"] == date.today().isoformat()
    assert api.hersteller_backup_laden()["ok"]


def test_unexpected_errors_are_logged_not_raised(cfg_dir, tmp_path):
    from app import Api

    api = Api()
    res = api.hersteller_speichern("kein dict")  # ohne Datenordner: normale Meldung
    assert res["ok"] is False
    config.set_data_dir(str(tmp_path))
    api.hersteller_datei_anlegen()
    res = api.hersteller_speichern("kein dict")  # löst intern einen Fehler aus
    assert res["ok"] is False and res["error"] == "unexpected"
    assert "fehlerprotokoll.txt" in res["message"]
    assert "Traceback" in (cfg_dir / "fehlerprotokoll.txt").read_text(encoding="utf-8")


def test_backup_covers_all_module_json_files(tmp_path):
    (tmp_path / "preisschilder").mkdir()
    (tmp_path / "preisschilder" / "liste_helme.json").write_text("{}", encoding="utf-8")
    (tmp_path / "preisschilder" / "bild.png").write_bytes(b"x")
    st = Storage(tmp_path, today=lambda: date(2026, 11, 14))
    st.save(st.load(create=True))
    st.save(st.load())
    day = tmp_path / "backups" / "2026-11-14"
    assert (day / "sos-dashboard-daten.json").is_file()
    assert (day / "preisschilder" / "liste_helme.json").is_file()
    assert not (day / "preisschilder" / "bild.png").exists()


def test_second_json_file_uses_items_and_own_revision(tmp_path):
    st = Storage(tmp_path, filename="liste.json", list_key="items",
                 new_data=lambda: {"schemaVersion": 1, "revision": 0, "items": []}, normalize=lambda d: d)
    data = st.load(create=True)
    data["items"].append({"a": 1})
    assert st.save(data) == 1
    assert read(tmp_path / "liste.json")["items"] == [{"a": 1}]


def test_safe_url():
    from platform_utils import safe_url

    assert safe_url("portal.example.de") == "https://portal.example.de"
    assert safe_url(" https://b2b.example.de/x ") == "https://b2b.example.de/x"
    assert safe_url("mailto:a@example.de") == "mailto:a@example.de"
    assert safe_url("file:///C:/Windows") is None
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("ftp://example.de") is None
    assert safe_url("") is None


def test_nfc_names_and_relative_paths(tmp_path):
    import unicodedata

    import platform_utils

    nfd = unicodedata.normalize("NFD", "Schläger")
    assert nfd != "Schläger" and platform_utils.same_name(nfd, "Schläger")
    folder = tmp_path / nfd / "x.png"
    assert platform_utils.rel_path(folder, tmp_path) == "Schläger/x.png"
    assert "\\" not in platform_utils.rel_path(folder, tmp_path)


def test_modules_are_discovered_in_order():
    from app import discover_modules

    ids = [m["id"] for m in discover_modules()]
    assert ids[:3] == ["hersteller", "preisschilder", "formulare"]
