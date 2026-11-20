"""Update aus dem GitHub-ZIP: Unterordner ersetzen, Datenordner nie anfassen, bei Fehlern den alten Stand behalten."""
import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import updater  # noqa: E402

BASE = {
    "app.py": "print('neu')\n", "storage.py": "X = 1\n", "updater.py": "Y = 1\n", "requirements.txt": "reportlab\n",
    "start.command": "#!/bin/bash\n", "modules/hersteller/module.json": '{"id": "hersteller", "titel": "Hersteller"}',
    "modules/hersteller/backend.py": "class Backend: pass\n", "web/index.html": "<html></html>", "web/shell.js": "// neu\n",
    "assets/sos-logo.svg": "<svg/>", "modules/neu/web/neu.js": "// neues Modul\n",
}


def make_zip(files=None, root="SOS_Dashboard-main"):
    files = dict(BASE if files is None else files)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, content in files.items():
            info = zipfile.ZipInfo(f"{root}/{name}")
            info.external_attr = (0o755 if name == "start.command" else 0o644) << 16
            archive.writestr(info, content)
    return buf.getvalue()


@pytest.fixture
def app(tmp_path):
    folder = tmp_path / "programm"
    for name, content in {"app.py": "print('alt')\n", "storage.py": "X = 0\n", "web/shell.js": "// alt\n", "web/veraltet.js": "// weg\n",
                          "modules/hersteller/backend.py": "ALT = 1\n", "modules/hersteller/module.json": "{}", "version.txt": "abc1234",
                          "daten/liste.json": "[1]", "eigene-notiz.txt": "bleibt"}.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return folder


def test_update_replaces_subfolders_and_removes_obsolete_files(app):
    updater.apply_package(updater.read_package(make_zip()), app, "def5678")
    assert (app / "web" / "shell.js").read_text() == "// neu\n"
    assert (app / "modules" / "hersteller" / "backend.py").read_text().startswith("class Backend")
    assert (app / "modules" / "neu" / "web" / "neu.js").is_file()  # neues Modul kommt in einem Unterordner dazu
    assert not (app / "web" / "veraltet.js").exists()
    assert (app / "version.txt").read_text() == "def5678"
    assert (app / "start.command").stat().st_mode & 0o100  # bleibt ausfuehrbar


def test_update_never_touches_user_files(app):
    updater.apply_package(updater.read_package(make_zip()), app, "x")
    assert (app / "daten" / "liste.json").read_text() == "[1]"
    assert (app / "eigene-notiz.txt").read_text() == "bleibt"
    assert not list(app.glob(".update-*"))  # keine Reste


def test_unmanaged_paths_in_zip_are_ignored(app):
    files = dict(BASE, **{"daten/sos-dashboard-daten.json": "ÜBERSCHRIEBEN", "referenz/x.py": "x", ".git/config": "x", "tests/t.py": "x"})
    package = updater.read_package(make_zip(files))
    assert "daten/sos-dashboard-daten.json" not in package and "referenz/x.py" not in package and ".git/config" not in package
    updater.apply_package(package, app, "x")
    assert not (app / "daten" / "sos-dashboard-daten.json").exists()


@pytest.mark.parametrize("broken", [
    lambda f: f.pop("app.py"),                                   # Pflichtdatei fehlt
    lambda f: f.__setitem__("web/shell.js", "x") or f.__setitem__("storage.py", "def (:\n"),  # Syntaxfehler
    lambda f: f.__setitem__("modules/hersteller/module.json", "{kaputt"),
])
def test_incomplete_or_broken_update_changes_nothing(app, broken):
    files = dict(BASE)
    broken(files)
    with pytest.raises(updater.UpdateError):
        updater.read_package(make_zip(files))
    assert (app / "app.py").read_text() == "print('alt')\n"


def test_not_a_zip_is_rejected():
    with pytest.raises(updater.UpdateError):
        updater.read_package(b"kein zip")


def test_path_traversal_is_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("root/app.py", "x")
        archive.writestr("root/modules/../../evil.py", "x")
    with pytest.raises(updater.UpdateError):
        updater.read_package(buf.getvalue())


def test_failure_during_copy_restores_old_state(app, monkeypatch):
    before = {p.relative_to(app).as_posix(): p.read_text() for p in app.rglob("*") if p.is_file()}
    real_replace = updater.os.replace
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 4:
            raise OSError("Platte voll")
        return real_replace(src, dst)

    monkeypatch.setattr(updater.os, "replace", flaky)
    with pytest.raises(updater.UpdateError, match="alte Stand"):
        updater.apply_package(updater.read_package(make_zip()), app, "def5678")
    after = {p.relative_to(app).as_posix(): p.read_text() for p in app.rglob("*") if p.is_file()}
    assert after == before
    assert not list(app.glob(".update-*"))


def test_install_flow_with_fake_github(app, monkeypatch):
    monkeypatch.setattr(updater.os, "access", lambda *a, **k: True)
    info = {"sha": "d" * 40, "kurz": "ddddddd", "notiz": "Neue Preisschilder"}
    assert updater.check(current="abc1234", fetch=lambda: info)["available"] is True
    assert updater.check(current="ddddddd", fetch=lambda: info)["available"] is False
    version = updater.install(current="abc1234", fetch=lambda: info, download=lambda: make_zip(), target=app)
    assert version == "ddddddd" and updater.current_version(app) == "ddddddd"
    with pytest.raises(updater.UpdateError, match="keine neuere"):
        updater.install(current="ddddddd", fetch=lambda: info, download=lambda: make_zip(), target=app)


def test_install_reports_download_errors_and_keeps_old_version(app):
    info = {"sha": "e" * 40, "kurz": "eeeeeee", "notiz": ""}

    def offline():
        raise OSError("offline")

    with pytest.raises(updater.UpdateError, match="Download"):
        updater.install(current="abc1234", fetch=lambda: info, download=offline, target=app)
    assert updater.current_version(app) == "abc1234"


def test_frozen_app_cannot_update(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert updater.can_update() is False
    assert updater.check(current="x")["canUpdate"] is False
