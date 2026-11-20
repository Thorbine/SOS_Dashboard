"""Backend des Moduls Formulare ueber die JS-API (Api.formulare_*), ohne Fenster."""
import json
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import platform_utils  # noqa: E402
from app import Api  # noqa: E402


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("SOS_DASHBOARD_CONFIG_DIR", str(tmp_path / "config"))
    data = tmp_path / "Daten"
    data.mkdir()
    config.set_data_dir(str(data))
    instance = Api()
    instance.opened, instance.revealed = [], []
    monkeypatch.setattr(platform_utils, "open_path", lambda p: instance.opened.append(Path(p)))
    monkeypatch.setattr(platform_utils, "reveal_path", lambda p: instance.revealed.append(Path(p)))
    instance.data = data
    return instance


def test_first_start_copies_the_four_templates_with_previews(api):
    res = api.formulare_liste()
    assert res["ok"]
    names = [f["name"] for f in res["formulare"]]
    assert names == ["Kundenbestellung", "Lieferschein", "Reklamation", "Rücklage"] or names == ["Kundenbestellung", "Lieferschein", "Reklamation", "Ruecklage"]
    formats = {f["name"][:3]: f["format"] for f in res["formulare"]}
    assert formats["Lie"] == "A4 hoch" and formats["Kun"] == "A4 quer"
    assert all(f["bild"].startswith("data:image/png;base64,") for f in res["formulare"])
    assert (api.data / "formulare").is_dir()


def test_folder_in_data_dir_wins_afterwards(api):
    api.formulare_liste()
    (api.data / "formulare" / "Reklamation.pdf").unlink()
    again = api.formulare_liste()
    assert "Reklamation" not in [f["name"] for f in again["formulare"]]  # wird nicht neu hineinkopiert


def test_new_pdf_appears_automatically_with_description(api):
    api.formulare_liste()
    import shutil
    shutil.copyfile(ROOT / "assets" / "formulare" / "Lieferschein.pdf", api.data / "formulare" / "Neue Vorlage.pdf")
    (api.data / "formulare" / "beschreibung.json").write_text(json.dumps({"Neue Vorlage.pdf": "Für Tests"}), encoding="utf-8")
    tiles = {f["name"]: f for f in api.formulare_liste()["formulare"]}
    assert tiles["Neue Vorlage"]["text"] == "Für Tests"


def test_open_and_reveal_only_accept_plain_pdf_names(api):
    api.formulare_liste()
    assert api.formulare_oeffnen("Lieferschein.pdf") == {"ok": True}
    assert api.opened[-1].name == "Lieferschein.pdf"
    assert api.formulare_im_ordner_zeigen("Lieferschein.pdf")["ok"] and api.revealed[-1].name == "Lieferschein.pdf"
    for bad in ("../x.pdf", "/etc/passwd", "a/b.pdf", "Lieferschein.txt", "", "nicht-da.pdf"):
        assert api.formulare_oeffnen(bad)["ok"] is False


def test_nfd_file_names_are_matched(api):
    api.formulare_liste()
    folder = api.data / "formulare"
    (folder / "Rücklage.pdf").rename(folder / (unicodedata.normalize("NFD", "Rücklage") + ".pdf")) if (folder / "Rücklage.pdf").exists() else None
    names = [f["datei"] for f in api.formulare_liste()["formulare"]]
    assert unicodedata.normalize("NFC", "Rücklage.pdf") in names or "Ruecklage.pdf" in names
    target = unicodedata.normalize("NFC", "Rücklage.pdf") if unicodedata.normalize("NFC", "Rücklage.pdf") in names else "Ruecklage.pdf"
    assert api.formulare_oeffnen(target)["ok"]


def test_replace_moves_old_file_to_archive(api, monkeypatch, tmp_path):
    api.formulare_liste()
    new = tmp_path / "neu.pdf"
    new.write_bytes((ROOT / "assets" / "formulare" / "Reklamation.pdf").read_bytes() + b"\n%neu")
    monkeypatch.setattr(api._ctx, "choose_file", lambda file_types=(): str(new))
    old_bytes = (api.data / "formulare" / "Lieferschein.pdf").read_bytes()
    res = api.formulare_ersetzen("Lieferschein.pdf")
    assert res["ok"]
    saved = Path(res["alt"])
    assert saved.parent.name == "_alt" and saved.read_bytes() == old_bytes and "Lieferschein_" in saved.name
    assert (api.data / "formulare" / "Lieferschein.pdf").read_bytes() == new.read_bytes()
    monkeypatch.setattr(api._ctx, "choose_file", lambda file_types=(): None)
    assert api.formulare_ersetzen("Lieferschein.pdf")["error"] == "cancelled"
    monkeypatch.setattr(api._ctx, "choose_file", lambda file_types=(): str(tmp_path / "x.txt"))
    (tmp_path / "x.txt").write_text("x")
    assert api.formulare_ersetzen("Lieferschein.pdf")["ok"] is False


def test_no_data_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("SOS_DASHBOARD_CONFIG_DIR", str(tmp_path / "cfg2"))
    assert Api().formulare_liste()["error"] == "no_folder"
