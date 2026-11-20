"""Laden und Speichern der Datendatei: atomar, mit Tages-Backups und Revisionsprüfung."""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path

DATA_FILE = "sos-dashboard-daten.json"
BACKUP_DIR = "backups"
BACKUP_KEEP = 14
SCHEMA_VERSION = 1
BACKUP_SUBDIRS = ("preisschilder", "formulare")  # Modulordner mit JSON-Dateien, die mitgesichert werden


class StorageError(Exception):
    code = "io"


class DataFolderError(StorageError):
    """Der Datenordner ist nicht erreichbar."""
    code = "folder_unreachable"


class DataFileMissingError(StorageError):
    """Der Ordner ist da, aber die Datendatei fehlt (z. B. noch nicht synchronisiert)."""
    code = "file_missing"


class CorruptDataError(StorageError):
    """Die Datendatei enthält kein gültiges JSON."""
    code = "corrupt"


class ConflictError(StorageError):
    """Die Datei auf der Platte ist neuer als der geladene Stand."""
    code = "conflict"


class Storage:
    def __init__(self, data_dir, today=date.today, *, filename=DATA_FILE, list_key="suppliers", new_data=None, normalize=None):
        """Eine JSON-Datei im Datenordner. Ohne Angaben ist es die Datei des Moduls Hersteller."""
        if new_data is None or normalize is None:
            from modules.hersteller import models
            new_data = new_data or models.new_data
            normalize = normalize or models.normalize
        self.dir = Path(data_dir)
        self.filename = filename
        self.list_key = list_key
        self._new_data = new_data
        self._normalize = normalize
        self.path = self.dir / filename
        self.backup_dir = self.dir / BACKUP_DIR
        self.revision = 0          # Revision, die zuletzt geladen oder geschrieben wurde
        self._today = today

    # ----- Laden -----

    def _check_dir(self) -> None:
        try:
            ok = self.dir.is_dir()
        except OSError:
            ok = False
        if not ok:
            raise DataFolderError(f"Der Datenordner ist nicht erreichbar: {self.dir}")

    def _read(self, path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except OSError as exc:
            raise StorageError(f"Die Datei konnte nicht gelesen werden: {exc}") from exc
        except ValueError as exc:
            raise CorruptDataError(f"Die Datei {path.name} ist beschädigt: {exc}") from exc
        if not isinstance(data, dict) or (self.list_key and not isinstance(data.get(self.list_key), list)):
            raise CorruptDataError(f"Die Datei {path.name} hat nicht den erwarteten Aufbau.")
        return data

    def load(self, create: bool = False) -> dict:
        """Lädt die Daten. Eine neue leere Datei entsteht nur mit create=True."""
        self._check_dir()
        if not self.path.exists():
            if not create:
                raise DataFileMissingError(f"Im Datenordner liegt keine Datei {self.filename}.")
            data = self._new_data()
            self._write(data)
            self.revision = 0
            return data
        data = self._normalize(self._read(self.path))
        self.revision = data["revision"]
        return data

    def load_for_update(self) -> dict:
        """Aktueller Stand von der Platte für eine Änderung durch die App selbst (z. B. neues Dokument)."""
        self._check_dir()
        if not self.path.exists():
            raise DataFileMissingError(f"Im Datenordner liegt keine Datei {self.filename}.")
        try:
            data = self._read(self.path)
        except CorruptDataError as exc:
            raise ConflictError("Die Datei auf der Platte ist nicht lesbar und wird nicht überschrieben.") from exc
        if isinstance(data.get("revision"), int) and data["revision"] > self.revision:
            raise ConflictError("Die Daten wurden auf einem anderen Rechner geändert.")
        return self._normalize(data)

    # ----- Speichern -----

    def save(self, data: dict) -> int:
        """Speichert und gibt die neue Revision zurück."""
        self._check_dir()
        if self.path.exists():
            try:
                disk_revision = self._read(self.path).get("revision", 0)
            except CorruptDataError as exc:
                raise ConflictError("Die Datei auf der Platte ist nicht lesbar und wird nicht überschrieben.") from exc
            if isinstance(disk_revision, int) and disk_revision > self.revision:
                raise ConflictError("Die Daten wurden auf einem anderen Rechner geändert.")
        self._backup_if_needed()
        out = dict(data)
        out["schemaVersion"] = SCHEMA_VERSION
        out["revision"] = self.revision + 1
        self._write(out)
        self.revision += 1
        return self.revision

    def _write(self, data: dict) -> None:
        """Erst in eine .tmp-Datei schreiben, dann ersetzen: nie eine halbe Datei."""
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            for attempt in range(4):
                try:
                    os.replace(tmp, self.path)
                    break
                except PermissionError:
                    # Sync-Programme halten die Datei unter Windows manchmal kurz gesperrt.
                    if attempt == 3:
                        raise
                    time.sleep(0.15)
        except OSError as exc:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise StorageError(f"Speichern fehlgeschlagen: {exc}") from exc

    def save_copy(self, data: dict) -> Path:
        """Legt die eigene Version bei einem Konflikt als Kopie neben die Datendatei."""
        self._check_dir()
        stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        target = self.dir / f"{Path(self.filename).stem}-kopie-{stamp}.json"
        try:
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Die Kopie konnte nicht gespeichert werden: {exc}") from exc
        return target

    # ----- Backups -----

    def _day_folders(self) -> list[Path]:
        """Tagesordner backups/JJJJ-MM-TT, ältester zuerst."""
        try:
            return sorted(p for p in self.backup_dir.glob("????-??-??") if p.is_dir())
        except OSError:
            return []

    def backups(self) -> list[Path]:
        """Gesicherte Fassungen dieser Datei, ältestes zuerst (Tagesordner, davor ältere Einzeldateien)."""
        legacy = []
        try:
            legacy = sorted(self.backup_dir.glob(f"{Path(self.filename).stem}-????-??-??.json"))
        except OSError:
            pass
        return legacy + [f / self.filename for f in self._day_folders() if (f / self.filename).is_file()]

    @staticmethod
    def backup_date(path: Path) -> str:
        """Datum (JJJJ-MM-TT) eines Backups, für die Anzeige."""
        for parent in path.parents:
            if parent.parent.name == BACKUP_DIR:
                return parent.name
        return path.stem[-10:]

    def latest_backup(self) -> Path | None:
        found = self.backups()
        return found[-1] if found else None

    def _module_files(self) -> list[Path]:
        """Alle JSON-Dateien der Module im Datenordner (ohne Logos, PDFs und Kopien)."""
        files = [p for p in self.dir.glob("*.json") if "-kopie-" not in p.name and "-ersetzt-" not in p.name]
        for sub in BACKUP_SUBDIRS:
            files += sorted((self.dir / sub).glob("*.json"))
        return files

    def _backup_if_needed(self) -> None:
        """Beim ersten Speichern pro Tag alle JSON-Dateien der Module sichern, die letzten 14 Tage behalten."""
        if not self.path.exists():
            return
        day = self.backup_dir / self._today().isoformat()
        try:
            if not day.exists():
                for src in self._module_files():
                    target = day / src.relative_to(self.dir)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
            for old in self._day_folders()[:-BACKUP_KEEP]:
                shutil.rmtree(old, ignore_errors=True)
        except OSError:
            pass  # Ein fehlgeschlagenes Backup soll das Speichern nicht verhindern.

    def restore_latest_backup(self) -> dict:
        """Spielt das neueste Backup zurück. Die bisherige Datei wird umbenannt, nicht gelöscht."""
        self._check_dir()
        backup = self.latest_backup()
        if backup is None:
            raise StorageError("Es ist kein Backup vorhanden.")
        self._read(backup)  # nur ein lesbares Backup zurückspielen
        try:
            if self.path.exists():
                stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
                os.replace(self.path, self.dir / f"{Path(self.filename).stem}-ersetzt-{stamp}.json")
            shutil.copy2(backup, self.path)
        except OSError as exc:
            raise StorageError(f"Das Backup konnte nicht zurückgespielt werden: {exc}") from exc
        return self.load()
