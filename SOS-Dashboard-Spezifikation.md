# SOS Dashboard: Spezifikation für Claude Code

## 1. Ziel

Ein Desktop-Dashboard für Thorben (SOS Sport GmbH, Braunschweig), das pro Hersteller/Lieferant alle wichtigen Arbeitsinfos an einer Stelle zeigt: eigene Kundennummer, Ansprechpartner mit Kontaktdaten, Links zu B2B-, Reklamations- und Medienportalen und freie Notizen. Was pro Hersteller angezeigt wird, kann Thorben selbst konfigurieren.

Nutzer: nur Thorben. Sprache der Oberfläche: Deutsch. Texte mit echten Umlauten (ä, ö, ü, ß).

## 2. Festgelegte Entscheidungen

- Form: Desktop-App. Python-Backend, Oberfläche in HTML/CSS/JavaScript, eingebettet über pywebview. Kein Tkinter, kein Browser, kein Server.
- Daten: eine JSON-Datei in einem frei wählbaren Ordner. Der Ordner kann per Cloud-Sync (OneDrive o. Ä.) zwischen Arbeits-Rechner und Zuhause geteilt werden. Nur ein Nutzer.
- Konfigurierbarkeit: Standardblöcke als Vorlage, pro Hersteller ausblendbar, umbenennbar, sortierbar, plus frei hinzufügbare Blöcke.
- Start: Hersteller manuell anlegen und per CSV-Import einlesen.
- Adressen: mehrere benannte Adressen pro Hersteller (z. B. Haupt-, Retouren-, Reklamationsadresse).
- Dokumente: aus den Herstellerdaten werden Retourenscheine (Begleitschein für Rücksendungen an den Hersteller) und Reklamationsformulare (Optik wie das vorhandene interne Formular) als PDF erzeugt. Eingaben tippt Thorben im Dashboard ein, keine Anbindung an BITS.
- Zielsystem: Windows (Zuhause Windows-PC, auf der Arbeit Windows in Parallels auf dem Mac). Ausgeliefert als .exe, gebaut unter Windows.

## 3. Tech-Stack

- Python 3.11 oder neuer
- pywebview (Edge WebView2 unter Windows)
- Frontend: reines HTML, CSS und Vanilla-JavaScript. Keine Frameworks, kein Node, kein Build-Schritt.
- Speicherung: JSON, UTF-8
- Tests: pytest für Speicherlogik und CSV-Import
- Paketierung: PyInstaller (`--onefile --windowed`), Icon aus dem SOS-Logo

## 4. Oberfläche

Layout nach Skizze "SOS-Dashboard":

**Kopfzeile**: Titel "SOS Dashboard", links daneben das SOS-Logo (Datei `sos-logo.svg`, Thorben legt sie ins Projekt unter `assets/`). Falls die Datei fehlt, nur Text.

**Linke Seitenleiste** (feste Breite ca. 280 px, scrollbar):
1. Suchfeld ganz oben. Filtert die Liste live beim Tippen. Standard: Treffer im Herstellernamen. Zusätzlich Volltextsuche in allen Blöcken (Kundennummer, Ansprechpartner, Linkbeschriftungen, Notizen). Hersteller, die nur im Inhalt treffen, bekommen unter dem Namen eine kleine graue Zeile mit dem Fundort.
2. Überschrift "Lieferanten" (laut Skizze). Der Begriff steht an genau einer Stelle im Code als Konstante, damit er leicht in "Hersteller" geändert werden kann.
3. Alphabetische Liste aller Hersteller. Der aktive Eintrag ist hervorgehoben.
4. Unten Button "+ Hersteller anlegen" und ein Zahnrad für Einstellungen (Datenordner, Import, Backup).

**Hauptbereich rechts**: zeigt den gewählten Hersteller.
- Oben der Herstellername als große Überschrift und rechts die Buttons "Dokument erstellen" und "Dokumente (n)" (siehe Abschnitt 7) sowie der Schalter "Bearbeiten".
- Darunter die Blöcke untereinander in der gespeicherten Reihenfolge. Standardreihenfolge laut Skizze:
  1. **Infos**: Schlüssel-Wert-Felder, Standardfeld "Unsere Kundennr".
  2. **Ansprechpartner**: Liste von Kontakten.
  3. **Adressen**: mehrere benannte Adressen (Standard: Hauptadresse, Retourenadresse, Reklamationsadresse) mit Firma, Zusatz, Straße, PLZ, Ort, Land, Ansprechpartner, Telefon, E-Mail, Notiz. Eine Adresse ist als Standard markiert (Stern). Jede Adresse hat einen Kopieren-Button, der sie als mehrzeiligen Text in die Zwischenablage legt.
  4. **Links**: Gruppen mit Beschriftung, Standard "B2B", "Reklamation", "Medien". Pro Gruppe beliebig viele Links.
  5. **Notizen**: großes Textfeld, immer ganz unten.
- Ohne gewählten Hersteller: leere Startansicht mit Hinweis "Hersteller links auswählen oder neu anlegen".

**Ansichtsmodus (Standard)**: nur lesen, schnell scannen.
- Links öffnen per Klick im Standardbrowser des Systems (nicht im Dashboard-Fenster).
- Kundennummer, Telefon und E-Mail haben einen kleinen Kopieren-Button. E-Mail ist zusätzlich ein `mailto:`-Link.
- Leere Felder werden im Ansichtsmodus nicht angezeigt, damit keine Platzhalterzeilen stören.

**Bearbeitungsmodus** (Schalter oben rechts):
- Alle Felder werden editierbar. Blöcke haben Griffe zum Verschieben (Drag and Drop oder Pfeile hoch/runter), ein Auge-Symbol zum Ausblenden, Stift zum Umbenennen und Papierkorb zum Löschen (mit Rückfrage).
- Button "+ Block hinzufügen" mit Auswahl: Infos-Felder, Ansprechpartner, Linkgruppe, Notiz, Freitext.
- Innerhalb von Blöcken: Zeilen hinzufügen, löschen, umsortieren.
- Ausgeblendete Blöcke bleiben erhalten und lassen sich im Bearbeitungsmodus wieder einblenden.
- Notizen sind auch im Ansichtsmodus direkt editierbar, weil sie ständig gebraucht werden.

**Design**:
- Markenfarbe Anthrazit `#595959` für Kopfzeile, Hervorhebungen und Buttons. Hintergrund hell, Karten weiß mit dezenter Kontur.
- Systemschrift, gut lesbar, sachlich. Keine Animationen außer dezenten Hover-Effekten.
- Die Farbe als CSS-Variable `--brand: #595959` definieren.
- Mindestfenstergröße 1000 x 650, Fenster skaliert sauber.

## 5. Datenmodell

Eine Datei `sos-dashboard-daten.json` im Datenordner:

```json
{
  "schemaVersion": 1,
  "revision": 42,
  "blockTemplate": [
    { "type": "fields",   "title": "Infos",          "defaults": [{ "label": "Unsere Kundennr", "value": "" }] },
    { "type": "contacts", "title": "Ansprechpartner" },
    { "type": "addresses", "title": "Adressen",       "defaults": [{ "label": "Hauptadresse" }, { "label": "Retourenadresse" }, { "label": "Reklamationsadresse" }] },
    { "type": "links",    "title": "Links",          "defaults": [{ "label": "B2B" }, { "label": "Reklamation" }, { "label": "Medien" }] },
    { "type": "notes",    "title": "Notizen" }
  ],
  "company": { "name": "SOS Sport GmbH", "street": "Rebenring 10", "zip": "38106", "city": "Braunschweig", "country": "Deutschland", "phone": "+49 (0) 531-347711", "email": "shop@sos-sport.de",
               "managingDirector": "Oliver Nieß", "register": "HRB 4881, Amtsgericht Braunschweig", "vatId": "DE 201646705", "showFooter": false },
  "counters": { "RS": { "2026": 0 }, "RK": { "2026": 0 } },
  "documents": [
    { "id": "uuid", "supplierId": "uuid", "type": "RS", "number": "RS-2026-0001", "createdAt": "2026-11-14T10:00:00",
      "file": "dokumente/Beispiel GmbH/RS-2026-0001_Retourenschein.pdf",
      "addressSnapshot": { "label": "Retourenadresse", "company": "", "street": "", "zip": "", "city": "", "country": "" },
      "data": {} }
  ],
  "suppliers": [
    {
      "id": "uuid",
      "name": "Beispiel GmbH",
      "createdAt": "2026-11-14T09:30:00",
      "updatedAt": "2026-11-14T09:30:00",
      "blocks": [
        { "id": "uuid", "type": "fields", "title": "Infos", "visible": true,
          "fields": [{ "id": "uuid", "label": "Unsere Kundennr", "value": "12345" }] },
        { "id": "uuid", "type": "contacts", "title": "Ansprechpartner", "visible": true,
          "contacts": [{ "id": "uuid", "name": "", "role": "", "phone": "", "mobile": "", "email": "", "note": "" }] },
        { "id": "uuid", "type": "addresses", "title": "Adressen", "visible": true,
          "addresses": [{ "id": "uuid", "label": "Retourenadresse", "isDefault": true, "company": "", "addition": "", "street": "", "zip": "", "city": "", "country": "Deutschland", "contactName": "", "phone": "", "email": "", "note": "" }] },
        { "id": "uuid", "type": "links", "title": "Links", "visible": true,
          "groups": [{ "id": "uuid", "label": "B2B", "links": [{ "id": "uuid", "title": "", "url": "" }] }] },
        { "id": "uuid", "type": "notes", "title": "Notizen", "visible": true, "text": "" }
      ]
    }
  ]
}
```

Regeln:
- Die Reihenfolge der Blöcke ergibt sich aus der Reihenfolge im Array `blocks`.
- Neue Hersteller werden aus `blockTemplate` erzeugt. Spätere Änderungen an der Vorlage ändern bestehende Hersteller nicht.
- Blocktypen: `fields`, `contacts`, `addresses`, `links`, `notes`. Ein Freitext-Block ist ein `notes`-Block mit eigenem Titel.
- Pro Hersteller darf genau eine Adresse `isDefault` sein. Wird eine andere als Standard markiert, verliert die bisherige das Flag. Gibt es nur eine Adresse, ist sie automatisch Standard.
- Dokumente werden nie in Herstellerdaten eingebettet, sondern über `supplierId` zugeordnet. Wird ein Hersteller gelöscht, bleiben seine Dokumente und PDFs erhalten (Rückfrage beim Löschen: "Dokumente bleiben im Archiv erhalten").
- Die Datei kann bei vielen Dokumenten wachsen. Das ist für die erwartete Menge (einige hundert Einträge) unkritisch, bei Bedarf später auf eine eigene Datei `dokumente.json` auslagern.
- Alle IDs sind UUIDs, damit Umsortieren und Löschen robust bleibt.
- Links ohne Schema (z. B. `portal.example.de`) werden beim Öffnen automatisch mit `https://` ergänzt. Nur `http`, `https` und `mailto` werden geöffnet, alles andere wird abgelehnt.
- Keine Felder für Passwörter oder Zugangsdaten vorsehen. Die Datei liegt im Klartext in einem Sync-Ordner. Im Einstellungsdialog ein kurzer Hinweis: "Bitte keine Passwörter speichern."

## 6. Speichern, Sicherheit der Daten, Sync

- Automatisches Speichern nach jeder Änderung mit 500 ms Verzögerung (Debounce). Kein Speichern-Button. Kleine Statusanzeige "Gespeichert" bzw. "Speichern fehlgeschlagen" in der Kopfzeile.
- Atomares Schreiben: erst in `datei.tmp` schreiben, dann per `os.replace` ersetzen, damit bei Absturz nie eine halbe Datei entsteht.
- Backups: beim ersten Speichern pro Tag eine Kopie in `backups/sos-dashboard-daten-JJJJ-MM-TT.json` im Datenordner. Die letzten 14 Backups behalten, ältere löschen.
- Sync-Schutz: Die `revision` wird bei jedem Speichern um 1 erhöht. Vor dem Speichern wird geprüft, ob die Datei auf der Platte eine höhere Revision hat als die beim Laden gelesene (andere Maschine hat zwischenzeitlich geschrieben). In dem Fall nicht überschreiben, sondern Dialog: "Die Daten wurden auf einem anderen Rechner geändert. Neu laden (eigene Änderungen gehen verloren) oder meine Version als Kopie speichern?"
- Datenordner: beim ersten Start fragt die App per Ordnerauswahl-Dialog, wo die Daten liegen sollen. Der Pfad steht in `%APPDATA%\SOS-Dashboard\config.json` (pro Rechner, nicht im Sync-Ordner). Änderbar in den Einstellungen. Existiert dort schon eine Datendatei, wird sie geladen, sonst eine neue angelegt.
- Ist der Datenordner nicht erreichbar, klare Fehlermeldung mit Button "Anderen Ordner wählen". Nicht still eine neue leere Datei anlegen.
- Fehlerhaftes JSON beim Laden: nicht überschreiben, Fehlermeldung zeigen und anbieten, das neueste Backup zu laden.

## 7. Dokumente: Retourenschein und Reklamationsformular

Aus den Daten eines Herstellers lassen sich zwei PDF-Dokumente erzeugen. Beide gehen an den Hersteller (nicht an Endkunden).

**Auslöser**: Im Kopf des Hauptbereichs steht neben dem Bearbeiten-Schalter der Button "Dokument erstellen" mit Auswahl "Retourenschein" und "Reklamationsformular". Daneben der Button "Dokumente (n)", der ein Seitenpanel mit allen bisher erzeugten Dokumenten dieses Herstellers öffnet (Nummer, Typ, Datum, Buttons "Öffnen", "Als Kopie weiterverwenden"). Das Panel ist kein Block und verändert die Reihenfolge der Blöcke nicht, Notizen bleiben ganz unten.

**Gemeinsame Regeln**
- Format A4 hoch, eine Seite, bei vielen Positionen automatisch weitere Seiten mit Kopfzeile und Seitenzahl.
- Erzeugt mit `reportlab` (Helvetica, WinAnsi). Umlaute, ß und € müssen korrekt erscheinen, dafür gibt es einen Test.
- Optik an Thorbens vorhandenem Reklamationsformular ausgerichtet: SOS-Logo links oben, "Datum:" rechts oben, Abschnitte mit anthrazitem Balken `#595959` und weißer Schrift, Beschriftungsfelder hellgrau, Tabellenlinien dünn.
- Absenderdaten sind die Firmendaten des Shops (Quelle: Impressum auf www.sos-sport.de, Stand 14.11.2026). Sie stehen in den Einstellungen, sind dort editierbar und werden im Datenmodell unter `company` gespeichert. Vorbelegung: SOS Sport GmbH, Rebenring 10, 38106 Braunschweig, Telefon +49 (0) 531-347711, E-Mail shop@sos-sport.de. Im PDF stehen im Absenderfeld Name, Anschrift, Telefon und E-Mail. Geschäftsführer, Handelsregister und USt-IdNr. stehen als optionale Felder in den Einstellungen (Geschäftsführer Oliver Nieß, HRB 4881 Amtsgericht Braunschweig, USt-IdNr. DE 201646705) und erscheinen nur im Fuß des PDFs, wenn der Haken "Firmendaten im Fuß anzeigen" gesetzt ist (Standard aus).
- Der Empfänger kommt aus einer der Adressen des Herstellers (Auswahl im Dialog, Standardadresse vorausgewählt). Beim Erzeugen wird eine Kopie der Adresse im Dokument gespeichert (Snapshot). Spätere Änderungen an der Adresse ändern alte Dokumente nicht.
- "Unsere Kundennr" wird automatisch aus dem Feld "Unsere Kundennr" im Infos-Block übernommen und kann im Dialog überschrieben werden. Fehlt sie, bleibt das Feld im PDF leer.
- Optionaler Ansprechpartner: Auswahlliste aus den Kontakten des Herstellers, auch "keiner".
- Nummernkreise: Retourenschein `RS-JJJJ-0001`, Reklamationsformular `RK-JJJJ-0001`. Laufende Nummer pro Typ und Jahr, gespeichert im Datenmodell unter `counters`. Die Nummer wird erst beim Klick auf "PDF erzeugen" vergeben, nicht beim Öffnen des Dialogs, und nur nach erfolgreichem Schreiben der PDF-Datei endgültig verbraucht.
- Archiv: Die PDF liegt unter `<Datenordner>/dokumente/<Herstellername>/<Nummer>_<Typ>.pdf` (Dateinamen bereinigt, keine Sonderzeichen). Zusätzlich steht ein Eintrag mit allen Eingabedaten in `documents` in der JSON-Datei, damit "Als Kopie weiterverwenden" die Felder wieder vorbefüllen kann (Kopie bekommt neue Nummer).
- Nach dem Erzeugen öffnet sich das PDF im Standardprogramm für PDFs (unter Windows `os.startfile`). Zusätzlich Button "Ordner öffnen", der den Ordner mit markierter Datei im Explorer zeigt (für Anhänge in Mails und Uploads in Portalen). Die PDFs haben saubere, sprechende Dateinamen und keine Schreibschutz- oder Passwortfunktion, damit Portale sie annehmen.
- Alle Dialogfelder haben sinnvolle Standardwerte, Datum ist heute und änderbar. Pflichtfelder: Adresse und mindestens eine Position (Retourenschein) bzw. Artikel und Fehlerbeschreibung (Reklamation).

**Retourenschein** (Begleitschein für Rücksendungen an den Hersteller)
- Kopf: Logo, Titel "Retourenschein", Nummer, Datum.
- Zwei Adressfelder nebeneinander: Absender (SOS) und Empfänger (Hersteller, gewählte Adresse mit Ansprechpartner).
- Referenzzeile: Unsere Kundennr, RMA-/Retourennummer des Herstellers (optional), Versandart (Freitext, optional), Anzahl Pakete.
- Positionstabelle mit beliebig vielen Zeilen: Pos., Artikel, Artikelnr. (optional), Größe, Farbe, Menge, Grund. Im Dialog Zeilen hinzufügen, löschen und per Tab schnell durchfahren.
- Grund allgemein als Auswahl (Reklamation, Retoure, Fehllieferung, Garantie, Sonstiges) plus Bemerkungsfeld.
- Fuß: Zeile für Datum und Unterschrift. Keine festen Textbausteine, nur was Thorben im Dialog einträgt.

**Reklamationsformular** (Reklamation von SOS beim Hersteller, Layout wie das vorhandene interne Formular)
- Kopf: Logo, Titel "Reklamation", Nummer, Datum.
- Abschnitt "Hersteller": Empfängeradresse, Unsere Kundennr, Ansprechpartner, Referenz/RMA-Nr (optional).
- Abschnitt "Artikel": Artikel, Artikelnr. (optional), Größe, Farbe, Kaufdatum, Beleg-Nr. Mehrere Artikel sind möglich, jeder als eigener Abschnitt-Block, ein Artikel ist Standard.
- Abschnitt "Reklamation": Fehlerbeschreibung (mehrzeilig), Gewünscht als Ankreuzfelder (Reparatur, Umtausch, Gutschrift, Geld zurück, mehrfach wählbar), Zubehör dabei (Freitext).
- Abschnitt "Bearbeitung" (Gesendet am, Rückmeldung, Ergebnis) nur wenn im Dialog "Bearbeitungsfelder mit ausdrucken" angehakt ist, Standard aus. Dort bleiben die Felder leer zum handschriftlichen Ausfüllen.
- Kein Preisfeld und keine Kundendaten (Name, Telefon, E-Mail des Endkunden). Das Formular geht an den Hersteller.

## 8. CSV-Import

Zugang über Einstellungen, "Hersteller aus CSV importieren".
- Trennzeichen automatisch erkennen (Semikolon oder Komma). Kodierung UTF-8, bei Fehlern Windows-1252.
- Pflichtspalte: `Name`. Optionale Spalten: `Kundennr`, `B2B`, `Reklamation`, `Medien` (Werte werden als Link in die jeweilige Standardgruppe geschrieben, Kundennr ins Feld "Unsere Kundennr").
- Vorschau vor dem Import: Anzahl neuer Hersteller, Anzahl übersprungener Duplikate (Vergleich des Namens ohne Beachtung von Groß-/Kleinschreibung), Zeilen mit Fehlern.
- Bestehende Hersteller werden nie überschrieben.
- Eine Beispiel-CSV `beispiel-import.csv` mit 3 Zeilen im Projekt ablegen.

## 9. Projektstruktur

```
sos-dashboard/
  app.py                 # Start, pywebview-Fenster, JS-API
  storage.py             # Laden, Speichern, Backup, Revision
  models.py              # Block-Vorlagen, Erzeugen neuer Hersteller
  documents.py           # PDF-Erzeugung (reportlab), Nummernkreise, Archiv
  csv_import.py
  config.py              # %APPDATA%-Konfiguration
  web/
    index.html
    style.css
    app.js
  assets/
    sos-logo.svg
    vorlagen/
      Reklamation.pdf    # Optik-Referenz, wird nicht zur Laufzeit gebraucht
  tests/
    test_storage.py
    test_documents.py
    test_csv_import.py
  beispiel-import.csv
  requirements.txt       # pywebview, reportlab, svglib (Logo im PDF), pytest
  build.bat              # PyInstaller-Aufruf
  README.md
```

Die JS-API (Python-Methoden, von `app.js` über `window.pywebview.api` aufgerufen): `load()`, `save(data)`, `open_url(url)`, `choose_data_folder()`, `import_csv()`, `get_status()`, `create_document(type, payload)`, `list_documents(supplier_id)`, `open_document(document_id)`, `open_documents_folder(supplier_id)`.

## 10. Vorgehen in Phasen

**Phase 1: Mockup (hier zuerst stoppen und Thorben zeigen)**
Nur `web/index.html`, `style.css`, `app.js` mit 5 bis 6 Beispiel-Herstellern fest im JavaScript. Läuft per Doppelklick im Browser, ohne Python. Alle Ansichten und Interaktionen funktionieren am Bildschirm: Seitenleiste, Suche, Ansichtsmodus, Bearbeitungsmodus, Blöcke verschieben, ausblenden, hinzufügen. Zusätzlich im Mockup: der Adressen-Block, der Button "Dokument erstellen", beide Eingabedialoge (Retourenschein, Reklamationsformular) und das Dokumente-Panel, jeweils mit Beispieldaten und ohne echte Funktion. Kein Speichern. Danach Screenshot oder Link zeigen und auf Feedback warten. Erst nach Freigabe weiter.

**Phase 2: Programmlogik**
`storage.py`, `models.py`, `config.py`, `app.py` mit pywebview. Frontend ersetzt die Beispieldaten durch `api.load()` und `api.save()`. Automatisches Speichern, Backups, Revisionsprüfung, Ordnerauswahl beim ersten Start. Tests dazu.

**Phase 3: Dokumente**
- 3a: Nur die zwei PDF-Layouts mit `reportlab` als eigenständiges Skript mit festen Beispieldaten erzeugen (`documents.py`). Beide Beispiel-PDFs Thorben zeigen und auf Freigabe des Layouts warten. Referenz für die Optik ist die Vorlage `assets/vorlagen/Reklamation.pdf` (Thorben legt sie aus dem Projekt dort ab).
- 3b: Anbindung an die App: Dialoge, Nummernkreise, Archiv, Dokumente-Panel, Öffnen nach dem Erzeugen. Tests für Nummernvergabe und Adress-Snapshot.

**Phase 4: Import und Feinschliff**
CSV-Import mit Vorschau, Einstellungsdialog (inklusive Absenderdaten), Fehlerdialoge, Volltextsuche mit Fundort-Hinweis.

**Phase 5: Auslieferung**
`build.bat` mit PyInstaller (Logo und Vorlagen als Datendateien einbinden), Icon aus dem Logo, README mit Anleitung für Einsteiger (Installation, erster Start, Datenordner, Backup zurückspielen). Test der .exe unter Windows und in der Parallels-VM, inklusive PDF-Erzeugung und Öffnen des PDFs.

## 11. Abnahmekriterien

- Neuer Hersteller lässt sich anlegen und enthält die fünf Standardblöcke (Infos, Ansprechpartner, Adressen, Links, Notizen).
- Pro Hersteller lassen sich mehrere benannte Adressen speichern, eine davon als Standard.
- Retourenschein und Reklamationsformular lassen sich für einen Hersteller erzeugen, erscheinen als PDF im Datenordner und öffnen sich danach automatisch.
- Dokumentnummern laufen pro Typ und Jahr lückenlos hoch und werden nie doppelt vergeben.
- Eine später geänderte Adresse verändert bereits erzeugte Dokumente nicht.
- Ein erzeugtes Dokument lässt sich aus der Dokumentenliste erneut öffnen und als Kopie mit neuer Nummer weiterverwenden.
- Die PDFs enthalten Umlaute, ß und das Eurozeichen korrekt.
- Pro Hersteller lassen sich Blöcke ausblenden, umbenennen, verschieben, löschen und neu hinzufügen, ohne andere Hersteller zu verändern.
- Nach Schließen und Neustart ist alles unverändert vorhanden.
- Suche filtert die Liste ohne spürbare Verzögerung bei 300 Herstellern.
- Links öffnen im Standardbrowser, E-Mail öffnet das Mailprogramm, Kopieren-Buttons funktionieren.
- Datei wird nie halb geschrieben, Backup pro Tag vorhanden, Konflikt zwischen zwei Rechnern wird erkannt.
- Alle Texte in der Oberfläche sind deutsch mit korrekten Umlauten.

## 12. Nicht im Umfang

- Mehrbenutzerbetrieb, Login, Rechteverwaltung
- Speichern von Passwörtern
- Anbindung an BITS oder Shopware, automatisches Vorbefüllen aus Kunden- oder Artikeldaten
- Lieferscheine an Kunden (kommen aus dem Onlineshop, nur Retourenscheine an Hersteller)
- Word-Ausgabe der Dokumente (alles ist im Programm eintragbar, PDF genügt)
- E-Mail-Versand aus dem Dashboard. Die PDFs werden von Hand versendet oder in Hersteller-Portalen hochgeladen, deshalb sind "Öffnen" und "Ordner öffnen" die wichtigen Buttons.
- Web- oder Handy-Version
