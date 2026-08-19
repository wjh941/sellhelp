"""Replicate completed desktop automatic backups to one owner-selected directory."""

import json
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database import active_backup_directory
from app.models.all_models import SystemConfig
from app.services.desktop_backup_service import (
    AUTO_BACKUP_PREFIX,
    AUTO_BACKUP_RETENTION_COUNT,
    utc_now,
)


logger = logging.getLogger(__name__)
OFFSITE_BACKUP_STATUS_KEY = "desktop_offsite_backup"


class DesktopOffsiteBackupService:
    def __init__(self, local_backup_dir, *, now=utc_now, copy_function=shutil.copy2):
        self.local_backup_dir = Path(local_backup_dir)
        self.now = now
        self.copy_function = copy_function

    @classmethod
    def for_active_database(cls):
        return cls(active_backup_directory())

    @classmethod
    def disabled_status(cls, db: Session) -> dict:
        return cls._status_payload(cls._load_state(db), enabled=False, pending=False)

    def configure(self, db: Session, directory) -> dict:
        target = self._validate_directory(directory)
        state = {
            "directory": str(target),
            "last_success": None,
            "last_failure": None,
        }
        self._save_state(db, state)
        return self._status_payload(state, enabled=True, pending=self._latest_local_backup() is None)

    def disable(self, db: Session) -> dict:
        state = self._load_state(db)
        state["directory"] = None
        state["last_failure"] = None
        self._save_state(db, state)
        return self._status_payload(state, enabled=True, pending=False)

    def sync_latest(self, db: Session) -> dict:
        state = self._load_state(db)
        directory = self._configured_directory(state)
        source = self._latest_local_backup()
        if directory is None or source is None:
            return self._status_payload(state, enabled=True, pending=directory is not None)

        temporary = directory / f".{source.name}.{uuid4().hex}.tmp"
        try:
            self._assert_readable_sqlite(source)
            self.copy_function(source, temporary)
            self._assert_readable_sqlite(temporary)
            os.replace(temporary, directory / source.name)
            self._prune_automatic_replicas(directory)
            state = {
                "directory": str(directory),
                "last_success": {
                    "completed_at": self.now().isoformat(),
                    "filename": source.name,
                    "size": (directory / source.name).stat().st_size,
                },
                "last_failure": None,
            }
            self._save_state(db, state)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            state = {
                "directory": state.get("directory"),
                "last_success": state.get("last_success"),
                "last_failure": {
                    "occurred_at": self.now().isoformat(),
                    "error_type": type(exc).__name__,
                },
            }
            self._save_state(db, state)
            logger.error("Desktop offsite backup failed: %s", type(exc).__name__)
        return self.status(db, enabled=True)

    def status(self, db: Session, enabled: bool) -> dict:
        state = self._load_state(db)
        directory = self._configured_directory(state)
        source = self._latest_local_backup() if enabled and directory is not None else None
        pending = enabled and directory is not None and (
            source is None
            or state.get("last_failure") is not None
            or state.get("last_success", {}).get("filename") != source.name
        )
        return self._status_payload(state, enabled=enabled, pending=pending)

    def _latest_local_backup(self) -> Path | None:
        if not self.local_backup_dir.is_dir():
            return None
        backups = sorted(
            (path for path in self.local_backup_dir.glob(f"{AUTO_BACKUP_PREFIX}*.db") if path.is_file()),
            key=lambda path: path.name,
            reverse=True,
        )
        return backups[0] if backups else None

    @staticmethod
    def _validate_directory(directory) -> Path:
        target = Path(directory)
        if not target.is_absolute() or not target.is_dir():
            raise ValueError("Offsite backup directory must be an existing absolute directory")
        probe = target / f".sellhelp-write-test-{uuid4().hex}.tmp"
        try:
            probe.touch(exist_ok=False)
        except OSError as exc:
            raise ValueError("Offsite backup directory is not writable") from exc
        finally:
            probe.unlink(missing_ok=True)
        return target

    @staticmethod
    def _assert_readable_sqlite(path: Path) -> None:
        connection = sqlite3.connect(path)
        try:
            result = connection.execute("PRAGMA quick_check").fetchone()
        finally:
            connection.close()
        if result != ("ok",):
            raise OSError("SQLite backup integrity check failed")

    @staticmethod
    def _configured_directory(state: dict) -> Path | None:
        directory = state.get("directory")
        return Path(directory) if isinstance(directory, str) and directory else None

    @staticmethod
    def _directory_name(directory: str | None) -> str | None:
        if not directory:
            return None
        path = Path(directory)
        return path.name or path.drive or "Selected directory"

    @staticmethod
    def _load_state(db: Session) -> dict:
        config = db.query(SystemConfig).filter(SystemConfig.key == OFFSITE_BACKUP_STATUS_KEY).first()
        if config is None or not config.value:
            return {"directory": None, "last_success": None, "last_failure": None}
        try:
            stored = json.loads(config.value)
        except (TypeError, json.JSONDecodeError):
            return {"directory": None, "last_success": None, "last_failure": None}
        if not isinstance(stored, dict):
            return {"directory": None, "last_success": None, "last_failure": None}
        return {
            "directory": stored.get("directory") if isinstance(stored.get("directory"), str) else None,
            "last_success": stored.get("last_success") if isinstance(stored.get("last_success"), dict) else None,
            "last_failure": stored.get("last_failure") if isinstance(stored.get("last_failure"), dict) else None,
        }

    @classmethod
    def _status_payload(cls, state: dict, *, enabled: bool, pending: bool) -> dict:
        directory = state.get("directory")
        return {
            "enabled": enabled,
            "configured": enabled and bool(directory),
            "directory_name": cls._directory_name(directory) if enabled else None,
            "retention_count": AUTO_BACKUP_RETENTION_COUNT,
            "is_pending": pending,
            "last_success": state.get("last_success"),
            "last_failure": state.get("last_failure"),
        }

    @staticmethod
    def _save_state(db: Session, state: dict) -> None:
        config = db.query(SystemConfig).filter(SystemConfig.key == OFFSITE_BACKUP_STATUS_KEY).first()
        value = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
        if config is None:
            db.add(SystemConfig(
                key=OFFSITE_BACKUP_STATUS_KEY,
                value=value,
                description="Desktop offsite backup status",
            ))
        else:
            config.value = value
        db.commit()

    @staticmethod
    def _prune_automatic_replicas(directory: Path) -> None:
        replicas = sorted(
            (path for path in directory.glob(f"{AUTO_BACKUP_PREFIX}*.db") if path.is_file()),
            key=lambda path: path.name,
            reverse=True,
        )
        for replica in replicas[AUTO_BACKUP_RETENTION_COUNT:]:
            replica.unlink()
