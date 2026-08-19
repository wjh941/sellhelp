"""Local automatic SQLite backup policy for the packaged desktop application."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import active_backup_directory, get_active_sqlite_db_path, sqlite_backup
from app.models.all_models import SystemConfig


logger = logging.getLogger(__name__)
AUTO_BACKUP_PREFIX = "sellhelp_auto_"
AUTO_BACKUP_INTERVAL_HOURS = 24
AUTO_BACKUP_RETENTION_COUNT = 14
AUTO_BACKUP_STATUS_KEY = "desktop_automatic_backup"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DesktopBackupService:
    def __init__(self, database_path, backup_dir, *, now=utc_now, backup_function=sqlite_backup):
        self.database_path = Path(database_path)
        self.backup_dir = Path(backup_dir)
        self.now = now
        self.backup_function = backup_function

    @classmethod
    def for_active_database(cls):
        return cls(Path(get_active_sqlite_db_path()), active_backup_directory())

    @classmethod
    def disabled_status(cls, db: Session) -> dict:
        return cls._status_payload(cls._load_persisted_state(db), enabled=False, now=utc_now())

    def run_if_due(self, db: Session) -> dict:
        state = self._load_persisted_state(db)
        current_time = self.now()
        if not self._is_due(state, current_time):
            return {"created": False, **self._status_payload(state, enabled=True, now=current_time)}

        target = self._next_backup_path(current_time)
        try:
            if not self.database_path.is_file():
                raise FileNotFoundError("Desktop SQLite database file is unavailable")
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.backup_function(self.database_path, target)
            success = {
                "completed_at": current_time.isoformat(),
                "filename": target.name,
                "size": target.stat().st_size,
            }
            state = {"last_success": success, "last_failure": None}
            self._save_state(db, state)
            self._prune_automatic_backups()
            return {"created": True, **self._status_payload(state, enabled=True, now=current_time)}
        except Exception as exc:
            target.unlink(missing_ok=True)
            state = {
                "last_success": state.get("last_success"),
                "last_failure": {
                    "occurred_at": current_time.isoformat(),
                    "error_type": type(exc).__name__,
                },
            }
            self._save_state(db, state)
            logger.error("Desktop automatic backup failed: %s", type(exc).__name__)
            return {"created": False, **self._status_payload(state, enabled=True, now=current_time)}

    def status(self, db: Session, enabled: bool) -> dict:
        state = self._load_persisted_state(db)
        return self._status_payload(state, enabled=enabled, now=self.now())

    def _next_backup_path(self, current_time: datetime) -> Path:
        return self.backup_dir / f"{AUTO_BACKUP_PREFIX}{current_time:%Y%m%d_%H%M%S%f}.db"

    def _prune_automatic_backups(self) -> None:
        automatic_backups = sorted(
            (path for path in self.backup_dir.glob(f"{AUTO_BACKUP_PREFIX}*.db") if path.is_file()),
            key=lambda path: path.name,
            reverse=True,
        )
        for backup_path in automatic_backups[AUTO_BACKUP_RETENTION_COUNT:]:
            backup_path.unlink()

    @staticmethod
    def _load_persisted_state(db: Session) -> dict:
        config = db.query(SystemConfig).filter(SystemConfig.key == AUTO_BACKUP_STATUS_KEY).first()
        if config is None or not config.value:
            return {"last_success": None, "last_failure": None}
        try:
            stored = json.loads(config.value)
        except (TypeError, json.JSONDecodeError):
            return {"last_success": None, "last_failure": None}
        if not isinstance(stored, dict):
            return {"last_success": None, "last_failure": None}
        return {
            "last_success": stored.get("last_success") if isinstance(stored.get("last_success"), dict) else None,
            "last_failure": stored.get("last_failure") if isinstance(stored.get("last_failure"), dict) else None,
        }

    @staticmethod
    def _is_due(state: dict, current_time: datetime) -> bool:
        last_success = state.get("last_success")
        if not isinstance(last_success, dict):
            return True
        completed_at = last_success.get("completed_at")
        if not isinstance(completed_at, str):
            return True
        try:
            parsed = datetime.fromisoformat(completed_at)
        except ValueError:
            return True
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return current_time >= parsed.astimezone(timezone.utc) + timedelta(hours=AUTO_BACKUP_INTERVAL_HOURS)

    @classmethod
    def _status_payload(cls, state: dict, *, enabled: bool, now: datetime) -> dict:
        return {
            "enabled": enabled,
            "interval_hours": AUTO_BACKUP_INTERVAL_HOURS,
            "retention_count": AUTO_BACKUP_RETENTION_COUNT,
            "is_due": enabled and cls._is_due(state, now),
            "last_success": state.get("last_success"),
            "last_failure": state.get("last_failure"),
        }

    @staticmethod
    def _save_state(db: Session, state: dict) -> None:
        config = db.query(SystemConfig).filter(SystemConfig.key == AUTO_BACKUP_STATUS_KEY).first()
        value = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
        if config is None:
            db.add(SystemConfig(
                key=AUTO_BACKUP_STATUS_KEY,
                value=value,
                description="Automatic desktop backup status",
            ))
        else:
            config.value = value
        db.commit()
