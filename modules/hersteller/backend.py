"""Python-Seite des Moduls Hersteller. Die Methoden erscheinen in der Oberfläche als hersteller_<name>()."""

from __future__ import annotations

import config
import platform_utils
from storage import Storage, StorageError

from . import csv_import, documents

NO_FOLDER = {"ok": False, "error": "no_folder", "message": "Es ist kein Datenordner gewählt."}


class Backend:
    def __init__(self, ctx):
        self.ctx = ctx
        self._storage = None
        self._import_path = None

    # ----- intern -----

    def _error(self, exc: Exception) -> dict:
        res = {"ok": False, "error": getattr(exc, "code", "io"), "message": str(exc), "dataDir": config.get_data_dir()}
        if self._storage is not None:
            backup = self._storage.latest_backup()
            res["backup"] = Storage.backup_date(backup) if backup else None
        return res

    def _load(self, create: bool = False) -> dict:
        data_dir = config.get_data_dir()
        if not data_dir:
            self._storage = None
            return {"ok": False, "error": "no_folder", "message": "Es ist noch kein Datenordner gewählt."}
        self._storage = Storage(data_dir)
        try:
            data = self._storage.load(create=create)
        except StorageError as exc:
            return self._error(exc)
        return {"ok": True, "data": data, "dataDir": data_dir}

    # ----- Daten -----

    def laden(self) -> dict:
        return self._load()

    def datei_anlegen(self) -> dict:
        """Legt im gewählten Ordner bewusst eine neue leere Datendatei an."""
        return self._load(create=True)

    def speichern(self, daten: dict) -> dict:
        if self._storage is None:
            return NO_FOLDER
        try:
            return {"ok": True, "revision": self._storage.save(daten)}
        except StorageError as exc:
            return self._error(exc)

    def kopie_speichern(self, daten: dict) -> dict:
        if self._storage is None:
            return NO_FOLDER
        try:
            return {"ok": True, "file": str(self._storage.save_copy(daten))}
        except StorageError as exc:
            return self._error(exc)

    def backup_laden(self) -> dict:
        if self._storage is None:
            return NO_FOLDER
        try:
            data = self._storage.restore_latest_backup()
        except StorageError as exc:
            return self._error(exc)
        return {"ok": True, "data": data, "dataDir": config.get_data_dir()}

    def status(self) -> dict:
        backup = self._storage.latest_backup() if self._storage else None
        return {"ok": True, "revision": self._storage.revision if self._storage else None,
                "lastBackup": Storage.backup_date(backup) if backup else None}

    # ----- Dokumente -----

    def _documents_call(self, action) -> dict:
        if self._storage is None:
            return NO_FOLDER
        try:
            return action()
        except documents.DocumentError as exc:
            return {"ok": False, "error": "document", "message": str(exc)}
        except StorageError as exc:
            return self._error(exc)
        except OSError as exc:
            return {"ok": False, "error": "io", "message": f"Das Öffnen ist fehlgeschlagen: {exc}"}

    def dokument_erzeugen(self, doc_type: str, payload: dict) -> dict:
        """Vergibt die Nummer, schreibt das PDF ins Archiv, speichert den Eintrag und öffnet das PDF."""
        def action():
            data = self._storage.load_for_update()
            entry = documents.create_document(data, self._storage.dir, doc_type, payload,
                                              logo_path=self.ctx.base_dir / "assets" / "sos-logo.svg")
            pdf = self._storage.dir / entry["file"]
            try:
                revision = self._storage.save(data)
            except StorageError:
                pdf.unlink(missing_ok=True)  # Nummer nicht verbraucht, also auch keine verwaiste Datei
                raise
            try:
                platform_utils.open_path(pdf)
                opened = True
            except OSError:
                opened = False
            return {"ok": True, "document": entry, "counters": data["counters"], "revision": revision, "opened": opened}
        return self._documents_call(action)

    def dokumente(self, supplier_id: str) -> dict:
        def action():
            data = self._storage.load_for_update()
            found = [dict(d, exists=(self._storage.dir / str(d.get("file", ""))).is_file())
                     for d in data["documents"] if d.get("supplierId") == supplier_id]
            return {"ok": True, "documents": sorted(found, key=lambda d: d.get("createdAt", ""), reverse=True)}
        return self._documents_call(action)

    def dokument_oeffnen(self, document_id: str) -> dict:
        def action():
            platform_utils.open_path(documents.document_path(self._storage.load_for_update(), self._storage.dir, document_id))
            return {"ok": True}
        return self._documents_call(action)

    def dokumente_ordner_oeffnen(self, supplier_id: str, document_id: str | None = None) -> dict:
        """Öffnet den Archivordner des Herstellers; mit document_id wird die Datei dort markiert."""
        def action():
            data = self._storage.load_for_update()
            if document_id:
                platform_utils.reveal_path(documents.document_path(data, self._storage.dir, document_id))
            else:
                platform_utils.open_path(documents.supplier_folder(data, self._storage.dir, supplier_id))
            return {"ok": True}
        return self._documents_call(action)

    # ----- CSV-Import -----

    def _import_call(self, action) -> dict:
        if self._storage is None:
            return NO_FOLDER
        try:
            return action()
        except csv_import.CsvError as exc:
            return {"ok": False, "error": "csv", "message": str(exc)}
        except StorageError as exc:
            return self._error(exc)

    def csv_importieren(self) -> dict:
        """Fragt nach der CSV-Datei und liefert die Vorschau. Importiert wird erst mit csv_bestaetigen()."""
        chosen = self.ctx.choose_file(("CSV-Dateien (*.csv;*.txt)", "Alle Dateien (*.*)"))
        if not chosen:
            return {"ok": False, "error": "cancelled"}

        def action():
            result = csv_import.preview(chosen, self._storage.load_for_update())
            self._import_path = str(chosen)
            return {"ok": True, **result}
        return self._import_call(action)

    def csv_bestaetigen(self) -> dict:
        """Importiert die zuletzt in der Vorschau gezeigte Datei."""
        def action():
            if not self._import_path:
                raise csv_import.CsvError("Es wurde noch keine Datei ausgewählt.")
            data = self._storage.load_for_update()
            created = csv_import.apply(self._import_path, data)
            revision = self._storage.save(data) if created else self._storage.revision
            self._import_path = None
            return {"ok": True, "suppliers": created, "revision": revision}
        return self._import_call(action)
