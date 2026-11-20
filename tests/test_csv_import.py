import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.hersteller import csv_import  # noqa: E402
from modules.hersteller import models  # noqa: E402
from modules.hersteller.csv_import import CsvError  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def write(tmp_path, text, encoding="utf-8"):
    path = tmp_path / "import.csv"
    path.write_bytes(text.encode(encoding))
    return path


def data_with(*names):
    data = models.new_data()
    data["suppliers"] = [models.new_supplier(n, data["blockTemplate"]) for n in names]
    return data


def group(supplier, label):
    links = next(b for b in supplier["blocks"] if b["type"] == "links")
    return next(g for g in links["groups"] if g["label"] == label)


def customer_no(supplier):
    return supplier["blocks"][0]["fields"][0]["value"]


def test_sample_file_has_three_importable_rows():
    data = data_with()
    result = csv_import.preview(PROJECT / "beispiel-import.csv", data)
    assert result == {"file": "beispiel-import.csv", "errors": [], "duplicates": [],
                      "new": ["Muster Ski GmbH", "Beispiel Outdoor AG", "Tennis Vorlage KG"]}
    assert data["suppliers"] == []  # die Vorschau ändert nichts

    created = csv_import.apply(PROJECT / "beispiel-import.csv", data)
    first, second, third = created
    assert data["suppliers"] == created
    assert [b["title"] for b in first["blocks"]] == ["Infos", "Ansprechpartner", "Adressen", "Links", "Notizen"]
    assert customer_no(first) == "40012" and customer_no(second) == "77-310" and customer_no(third) == ""
    assert group(first, "B2B")["links"][0]["url"] == "https://b2b.muster-ski.example"
    assert group(first, "Reklamation")["links"][0]["url"].endswith("/reklamation")
    assert group(first, "Medien")["links"][0]["title"] == "Medien"
    assert group(second, "B2B")["links"][0]["url"] == "b2b.beispiel-outdoor.example"
    assert group(second, "Reklamation")["links"] == [] and group(third, "B2B")["links"] == []


@pytest.mark.parametrize("delimiter", [";", ","])
def test_delimiter_is_detected(tmp_path, delimiter):
    text = delimiter.join(["Name", "Kundennr", "B2B"]) + "\n" + delimiter.join(["Alpha GmbH", "123", "b2b.alpha.example"]) + "\n"
    rows, errors = csv_import.parse(csv_import.read_text(write(tmp_path, text)))
    assert errors == [] and rows[0]["name"] == "Alpha GmbH" and rows[0]["kundennr"] == "123"


def test_quoted_values_may_contain_the_delimiter(tmp_path):
    rows, _ = csv_import.parse('Name;Kundennr\n"Müller; Söhne GmbH";"12;34"\n')
    assert rows[0]["name"] == "Müller; Söhne GmbH" and rows[0]["kundennr"] == "12;34"
    rows, _ = csv_import.parse('Name,Kundennr\n"Berg, Tal & Co.",99\n')
    assert rows[0]["name"] == "Berg, Tal & Co."


def test_utf8_with_bom_and_windows_1252(tmp_path):
    text = "Name;Kundennr\nVölkl Größe Maß;1\n"
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        rows, _ = csv_import.parse(csv_import.read_text(write(tmp_path, text, encoding)))
        assert rows[0]["name"] == "Völkl Größe Maß", encoding


def test_header_is_case_insensitive_and_unknown_columns_are_ignored(tmp_path):
    rows, _ = csv_import.parse(" NAME ; kundennummer ; Telefon ; medien \nAlpha;7;0531 1;m.alpha.example\n")
    assert rows == [{"line": 2, "name": "Alpha", "kundennr": "7", "B2B": "", "Reklamation": "", "Medien": "m.alpha.example"}]


def test_missing_name_column_and_empty_file_are_errors():
    with pytest.raises(CsvError, match="Name"):
        csv_import.parse("Firma;Kundennr\nAlpha;1\n")
    with pytest.raises(CsvError, match="leer"):
        csv_import.parse("\n\n")
    with pytest.raises(CsvError):
        csv_import.read_text("gibt-es-nicht.csv")


def test_rows_without_name_are_reported_and_blank_lines_skipped():
    rows, errors = csv_import.parse("Name;Kundennr\nAlpha;1\n\n;2\n ; \nBeta;3\n")
    assert [r["name"] for r in rows] == ["Alpha", "Beta"]
    assert errors == [{"line": 4, "message": "Name fehlt"}]


def test_duplicates_are_skipped_case_insensitively(tmp_path):
    data = data_with("Wilson", "HEAD Sport")
    data["suppliers"][0]["blocks"][0]["fields"][0]["value"] = "ALT-1"
    path = write(tmp_path, "Name;Kundennr\nwilson;NEU-9\n HEAD SPORT ;5\nNeu GmbH;1\nneu gmbh;2\nStraße AG;3\nSTRASSE AG;4\n")
    result = csv_import.preview(path, data)
    assert result["new"] == ["Neu GmbH", "Straße AG"]
    assert result["duplicates"] == ["wilson", "HEAD SPORT", "neu gmbh", "STRASSE AG"]

    created = csv_import.apply(path, data)
    assert [s["name"] for s in data["suppliers"]] == ["Wilson", "HEAD Sport", "Neu GmbH", "Straße AG"]
    assert customer_no(data["suppliers"][0]) == "ALT-1"  # bestehende Hersteller bleiben unverändert
    assert customer_no(created[0]) == "1"
    assert csv_import.apply(path, data) == []  # zweiter Import derselben Datei legt nichts doppelt an


def test_import_works_with_changed_template():
    template = [{"type": "notes", "title": "Notizen"}]
    supplier = csv_import.build_supplier(
        {"line": 2, "name": "Alpha", "kundennr": "42", "B2B": "b2b.alpha.example", "Reklamation": "", "Medien": ""}, template)
    assert [b["type"] for b in supplier["blocks"]] == ["fields", "links", "notes"]
    assert supplier["blocks"][0]["fields"][0] | {"id": ""} == {"id": "", "label": "Unsere Kundennr", "value": "42"}
    assert group(supplier, "B2B")["links"][0]["url"] == "b2b.alpha.example"


def test_three_hundred_rows(tmp_path):
    text = "Name;Kundennr\n" + "".join(f"Hersteller {i:03d};{i}\n" for i in range(300))
    data = data_with()
    assert len(csv_import.apply(write(tmp_path, text), data)) == 300
    assert len({s["id"] for s in data["suppliers"]}) == 300


# ----- JS-API -----

def preview(api, path):
    """Wie csv_importieren(), nur ohne Dateidialog."""
    api._ctx.choose_file = lambda file_types=(): str(path)
    return api.hersteller_csv_importieren()


@pytest.fixture
def api(tmp_path, monkeypatch):
    import config
    from app import Api

    monkeypatch.setenv("SOS_DASHBOARD_CONFIG_DIR", str(tmp_path / "config"))
    data_dir = tmp_path / "daten"
    data_dir.mkdir()
    config.set_data_dir(str(data_dir))
    instance = Api()
    data = instance.hersteller_datei_anlegen()["data"]
    data["suppliers"].append(models.new_supplier("Muster Ski GmbH", data["blockTemplate"]))
    assert instance.hersteller_speichern(data)["ok"]
    return instance


def test_api_preview_then_confirm(api):
    assert api.hersteller_csv_bestaetigen()["error"] == "csv"  # ohne Vorschau kein Import

    result = preview(api, PROJECT / "beispiel-import.csv")
    assert result["ok"] and result["new"] == ["Beispiel Outdoor AG", "Tennis Vorlage KG"]
    assert result["duplicates"] == ["Muster Ski GmbH"]
    assert api.hersteller_status()["revision"] == 1  # die Vorschau speichert nichts

    done = api.hersteller_csv_bestaetigen()
    assert done["ok"] and done["revision"] == 2
    assert [s["name"] for s in done["suppliers"]] == ["Beispiel Outdoor AG", "Tennis Vorlage KG"]

    from app import Api
    names = [s["name"] for s in Api().hersteller_laden()["data"]["suppliers"]]
    assert names == ["Muster Ski GmbH", "Beispiel Outdoor AG", "Tennis Vorlage KG"]
    assert api.hersteller_csv_bestaetigen()["error"] == "csv"  # Bestätigung gilt nur einmal


def test_api_reports_csv_errors(api, tmp_path):
    bad = write(tmp_path, "Firma;Ort\nAlpha;Braunschweig\n")
    result = preview(api, bad)
    assert result == {"ok": False, "error": "csv", "message": "In der ersten Zeile fehlt die Spalte „Name“."}


def test_api_import_detects_conflict(api):
    from app import Api

    preview(api, PROJECT / "beispiel-import.csv")
    other = Api()
    other.hersteller_speichern(other.hersteller_laden()["data"])
    assert api.hersteller_csv_bestaetigen()["error"] == "conflict"
