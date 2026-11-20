# SOS Dashboard

Desktop-Programm für die SOS Sport GmbH mit drei Modulen:

- **Hersteller:** pro Hersteller Kundennummer, Ansprechpartner, Adressen, Links und Notizen an einer Stelle. Daraus entstehen Retourenscheine und Reklamationsformulare als PDF.
- **Preisschilder:** Schilder für Helme, Tennisbälle, Schläger, Ski und Snowboards erstellen und als A4-PDF drucken.
- **Formulare:** Druckvorlagen (Kundenbestellung, Reklamation, Rücklage, Lieferschein) mit einem Klick öffnen und drucken.

Diese Anleitung ist für Einsteiger geschrieben. Du brauchst keine Programmierkenntnisse.

## 1. Installation

Das Programm läuft aus dem Quelltext. Es braucht **Python 3.11 oder neuer** (getestet mit 3.14).

### Auf dem Mac

1. Python von python.org installieren, falls noch nicht vorhanden.
2. Den Programmordner irgendwohin legen, zum Beispiel in „Dokumente“.
3. Doppelklick auf **`SOS Dashboard.app`** (ohne Terminalfenster) oder auf `start.command` (mit Terminalfenster, praktisch bei Fehlern). Beim ersten Start installiert das Programm die nötigen Pakete von selbst und braucht dafür Internet. Danach startet es sofort.

`SOS Dashboard.app` darf ins Dock, muss aber im Programmordner bleiben. Beim ersten Öffnen kann macOS warnen: Rechtsklick → „Öffnen“.

### Unter Windows

1. Python von python.org installieren. Dabei **„Add python.exe to PATH“** und den „py launcher“ anhaken.
2. Den Programmordner irgendwohin legen.
3. Doppelklick auf **`start.bat`**. Beim ersten Start werden die Pakete installiert (ein paar Minuten, Internet nötig). Danach startet das Programm ohne Konsolenfenster.

Das Programm braucht die „Microsoft Edge WebView2 Runtime“. Unter Windows 11 ist sie vorhanden. Bleibt das Fenster unter Windows 10 leer, die Runtime von Microsoft nachinstallieren (Suche nach „WebView2 Runtime Evergreen“).

## 2. Erster Start und Datenordner

Beim ersten Start fragt das Programm nach dem **Datenordner**. Dort liegt alles, was du einträgst.

- Wähle einen Ordner in OneDrive (oder einem anderen Cloud-Ordner), wenn du auf der Arbeit und zuhause dieselben Daten sehen möchtest.
- Auf dem zweiten Rechner wählst du denselben Ordner. Das Programm findet die vorhandenen Dateien.
- Welcher Ordner gewählt ist, merkt sich jeder Rechner für sich (Mac: `~/Library/Application Support/SOS-Dashboard/`, Windows: `%APPDATA%\SOS-Dashboard\`). Ändern kannst du ihn unter **Einstellungen**.

**Bitte keine Passwörter eintragen.** Die Daten liegen unverschlüsselt im Datenordner.

| Datei oder Ordner im Datenordner | Inhalt |
| --- | --- |
| `sos-dashboard-daten.json` | alle Hersteller, Absenderdaten und die Dokumentenliste |
| `dokumente/<Hersteller>/` | die erzeugten PDFs |
| `preisschilder/` | Einstellungen, Schilderlisten, gespeicherte Seiten und Logos (`logos/<Produkt>/`) |
| `formulare/` | die Druckvorlagen als PDF |
| `backups/JJJJ-MM-TT/` | je eine Sicherung aller Dateien pro Tag, an dem gespeichert wurde; die letzten 14 Tage bleiben |

Das Programm und sein Update fassen den Datenordner nicht an, außer um deine eigenen Eingaben zu speichern.

## 3. Bedienung in Kürze

Oben stehen die Module. **Gespeichert wird automatisch**, eine halbe Sekunde nach der letzten Änderung (oben rechts steht „Gespeichert“). Nach der letzten Eingabe bitte einen Moment warten, bevor du das Fenster schließt.

### Hersteller

- **Links** steht die Liste mit Suchfeld. Die Suche findet auch Kundennummern, Ansprechpartner, Links und Notizen und zeigt, wo der Treffer steht. Rechtsklick auf einen Hersteller: Bearbeiten oder Löschen.
- **Rechts** der gewählte Hersteller. Die Kopieren-Symbole legen Kundennummer, Telefon, E-Mail oder eine Adresse in die Zwischenablage. Links öffnen im Browser.
- **Bearbeiten** (oben rechts) schaltet alle Felder frei. Blöcke lassen sich verschieben, ausblenden, umbenennen, löschen und neu hinzufügen. **Notizen** kannst du immer direkt tippen.
- **Dokument erstellen** erzeugt einen Retourenschein oder ein Reklamationsformular. Empfängeradresse, Kundennummer und Ansprechpartner kommen aus den Herstellerdaten. Ist die Adresse oder die Person nicht hinterlegt, wähle „Andere Adresse eingeben …“ bzw. „Anderen Ansprechpartner eingeben …“; ein Haken legt sie zusätzlich beim Hersteller ab. Die Nummer (`RS-2026-0001`, `RK-2026-0001`) wird erst beim Klick auf „PDF erzeugen“ vergeben, danach öffnet sich das PDF. Unter **Dokumente (n)** stehen alle bisherigen Dokumente; „Als Kopie weiterverwenden“ füllt den Dialog mit den alten Eingaben vor.

### Preisschilder

Pro Schildtyp ein Reiter. Links Formular, Logo-Kacheln und Liste, rechts die Vorschau des Blatts.

- **Blatt-Zähler:** In der Liste legt „+“ ein Schild aufs Blatt, „−“ nimmt eines weg (die Zeile wird grün). „Blatt leeren“ setzt alles auf null. Die Blatt-Auswahl wird nicht gespeichert. Die Reihenfolge der Liste ist die Reihenfolge auf dem Blatt (▲ ▼, „Sortieren“).
- **Logos:** Dateien (PNG, JPG) liegen im Ordner `preisschilder/logos/<Produkt>/`. „Ordner öffnen“ zeigt ihn, „Neu laden“ liest ihn neu ein. Logos direkt in `logos/` erscheinen bei allen Produkten.
- **Helme:** „Helme aus CSV importieren …“ liest die Helm-CSV aus BITS (neue Modelle werden angehängt, vorhandene bleiben unberührt). „Alle Größen anlegen“ ergänzt zu jedem Modell die fehlenden Größen.
- **Schläger:** Die Liste ist die Seite (6 Schilder pro Seite). Kopfgröße in² eingeben, cm² wird berechnet. Klick auf ein Schild lädt es zum Bearbeiten, Ziehen sortiert um, „Kopieren“ legt es in die Zwischenablage. „Seite auffüllen“ wiederholt das letzte Schild bis zur vollen Seite. „Gespeicherte Seiten“ sichern eine Seite unter einem Namen (Export und Import als Datei). Die globale Suche findet Schilder in allen gespeicherten Seiten. Neue Marke: weiße PNG (z. B. `lacoste.png`) in `logos/Schläger/` legen und die Marke unter **Einstellungen** (Reiter Preisschilder) eintragen.
- **Drucken (PDF)** erzeugt ein A4-PDF und öffnet es. **Beim Drucken „100 % / Tatsächliche Größe“ wählen**, nicht „An Seite anpassen“, sonst stimmen die Maße nicht.
- **Einstellungen** (im Reiter): Schildmaße, Blattrand, Abstand, Marken und Farben. Dort steht auch „Daten aus dem alten Preisschilder-Programm übernehmen“: Du wählst den alten Ordner `daten`, das Programm kopiert Einstellungen, Listen und Logos. Vorhandenes wird nicht ohne Rückfrage überschrieben.

### Formulare

Eine Kachel pro PDF im Ordner `formulare/` des Datenordners, mit Vorschau. **Öffnen / Drucken** öffnet die Datei, **Im Ordner zeigen** markiert sie im Finder bzw. Explorer, **Ersetzen** tauscht sie gegen eine andere PDF aus (die alte landet mit Datum in `formulare/_alt/`). Eine neue PDF im Ordner erscheint als neue Kachel. Die Kurzzeile unter dem Namen kommt aus der optionalen Datei `formulare/beschreibung.json` (`{"Dateiname.pdf": "Text"}`).

## 4. Hersteller aus einer CSV-Datei importieren

Einstellungen → „Hersteller aus CSV importieren“. Vor dem Import zeigt eine Vorschau, was passieren wird.

- Die erste Zeile enthält die Spaltennamen. Pflicht ist `Name`. Möglich sind außerdem `Kundennr`, `B2B`, `Reklamation` und `Medien`.
- Trennzeichen ist Semikolon oder Komma. Excel: „Speichern unter“ → „CSV UTF-8 (durch Trennzeichen getrennt)“.
- Hersteller, die es schon gibt, werden übersprungen und nie überschrieben. `beispiel-import.csv` zeigt den Aufbau.

## 5. Programm aktualisieren

**Einstellungen → „Nach Aktualisierung suchen“.** Gibt es eine neuere Version im GitHub-Repository, installiert das Programm sie auf Nachfrage und startet neu.

- Das Update ersetzt die Programmdateien einschließlich der Unterordner (`modules/`, `web/`, `assets/`). Vorher wird alles geprüft; schlägt etwas fehl, bleibt der alte Stand erhalten.
- Dein Datenordner liegt außerhalb des Programmordners und wird nicht angefasst.
- Das Repository steht in `updater.py` (`DEFAULT_REPO`). Liegt es woanders, in der Datei `config.json` im Konfigurationsordner `"updateRepo": "Konto/Repo"` eintragen.
- Das Update geht nur, wenn das Programm über `start.command`, `SOS Dashboard.app` oder `start.bat` aus dem Quelltext läuft.

## 6. Backup zurückspielen

**Im Programm:** Einstellungen → „Backup zurückspielen“ lädt das neueste Backup der Herstellerdaten. Der bisherige Stand wird als `sos-dashboard-daten-ersetzt-…json` im Datenordner aufbewahrt.

**Von Hand (auch für Preisschilder-Listen):**

1. Programm schließen.
2. Im Datenordner die betroffene Datei umbenennen, zum Beispiel `liste_helme.json` in `liste_helme-alt.json`.
3. Aus `backups/JJJJ-MM-TT/` die gewünschte Datei an ihren Platz kopieren (gleicher Unterordner wie im Datenordner).
4. Programm starten.

**Meldungen, die auftauchen können:**

- *„Die Daten wurden auf einem anderen Rechner geändert“*: Auf dem anderen Rechner wurde inzwischen gespeichert. „Neu laden“ holt dessen Stand. „Meine Version als Kopie speichern“ legt deinen Stand als eigene Datei in den Datenordner und lädt dann neu. Am besten das Programm immer nur auf einem Rechner gleichzeitig offen haben.
- *„Der Datenordner ist nicht erreichbar“*: Laufwerk oder Cloud-Ordner ist nicht verbunden. Es wird nichts verändert.
- *„Im Datenordner liegt keine Datendatei“*: Bei einem Cloud-Ordner ist die Datei vielleicht noch nicht synchronisiert. Kurz warten und „Erneut versuchen“. Nur „Neue leere Datei anlegen“, wenn du wirklich neu anfangen möchtest.
- *„Die Datendatei ist beschädigt“*: Die Datei wird nicht angerührt. Das Programm bietet an, das neueste Backup zu laden.
- Unerwartete Fehler stehen mit Zeitstempel in `fehlerprotokoll.txt` im Konfigurationsordner (siehe Abschnitt 2).

## 7. Für Entwickler

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
.venv/bin/python app.py
```

Tests und Selbstprüfung:

```
python -m pytest tests
python app.py --selftest      # Module, PDF-Erzeugung, Vorschau
python app.py --guitest       # öffnet kurz das Fenster und prüft, ob alle Module eingehängt sind
```

Beispiel-PDFs: `python -m modules.hersteller.documents` und `python tools/preisschilder_beispiele.py` (Ziel: `beispiel-pdfs/`). `web/index.html` lässt sich auch im Browser öffnen: eine Vorschau mit Beispieldaten ohne Speichern und ohne PDFs.

| Datei | Aufgabe |
| --- | --- |
| `app.py` | Start, Fenster, Modullader, Schnittstelle zwischen Oberfläche und Python |
| `storage.py` | Laden, Speichern, Backups, Schutz vor Überschreiben |
| `platform_utils.py` | Mac und Windows: Dateien öffnen, Pfade, Fehlerprotokoll |
| `config.py` | merkt sich den Datenordner pro Rechner |
| `updater.py` | Aktualisierung des Programms aus GitHub |
| `modules/hersteller/` | Hersteller, Dokumente (PDF), CSV-Import |
| `modules/preisschilder/` | Schilder: Rechenkern `sheet.py`, Layouts, Helm-CSV, Backend |
| `modules/formulare/` | Druckvorlagen |
| `web/` | gemeinsame Oberfläche (Kopfzeile, Navigation, Dialoge, Design) |
| `assets/` | Logo, Vorlagen-PDFs, Schläger-Logos |
| `referenz/` | nur zum Lesen: Altprogramm der Preisschilder, Schläger-Generator, Chrome-Vergleichsdruck |
| `tests/` | automatische Tests |

Der Begriff „Lieferanten“ über der Liste steht an genau einer Stelle: `SIDEBAR_TITLE` ganz oben in `modules/hersteller/web/hersteller.js`.
