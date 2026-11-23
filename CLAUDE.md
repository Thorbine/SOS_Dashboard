# SOS Dashboard (SOS Sport Braunschweig)

Python + pywebview, Oberfläche in HTML/CSS/Vanilla-JS, Mac und Windows. Spezifikation: `SOS-Dashboard-Spezifikation.md`.

## Aufbau
- `app.py` ist das Grundgerüst: Fenster, Modullader, JS-API. Die öffentlichen Methoden von `modules/<name>/backend.py` (Klasse `Backend`) erscheinen in der Oberfläche als `<name>_<methode>()`.
- Neues Modul = Ordner `modules/<name>/` mit `module.json` (`id`, `titel`, `reihenfolge`), `backend.py` und `web/` (alle `*.js` und `*.css` dort werden geladen; das JS ruft `registerModule({id, title, mount(root)})` auf). Im Browser-Mockup ohne Python zusätzlich `DEMO_MODULES` in `web/shell.js` ergänzen.
- Einstellungen sind ein Tab (Modul `einstellungen`): jedes Modul trägt seine Abschnitte mit `registerSettingsSection({id, title, build})` ein, `openSettings(id)` springt hin.
- Gemeinsam: `storage.py` (JSON atomar, Revision, Backups), `config.py`, `platform_utils.py` (Öffnen, Pfade, NFC, Fehlerprotokoll), `updater.py`, `web/shell.js` und `web/style.css`.
- `referenz/` ist nur zum Lesen (Altprogramm Preisschilder, Tennis-Generator, Formular-PDFs).

## Arbeitsregeln
- Der Datenordner gehört dem Nutzer. Programm und Update fassen ihn nie an.
- Keine `*_previous.py` oder `*_v1.py` Kopien.
- Logik ohne Oberfläche bekommt Tests: `python -m pytest tests`. Prüfung des Fensters: `python app.py --selftest` und `--guitest`.
- Start: `start.command` (Mac), `start.bat` (Windows), `SOS Dashboard.app`. Kein PyInstaller, keine .exe. Update über `updater.py` (GitHub-ZIP von `main`, ersetzt Unterordner, Datenordner bleibt unberührt).
- Keine Passwörter speichern, nur http, https und mailto öffnen, Dateinamen mit Umlauten auf NFC normalisieren.
