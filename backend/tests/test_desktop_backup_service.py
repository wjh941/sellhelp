import json
import sqlite3
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.all_models import SystemConfig
from app.services.desktop_backup_service import DesktopBackupService


NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def create_file_database(path, value="preserved"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE recovery_check (value TEXT)")
        connection.execute("INSERT INTO recovery_check VALUES (?)", (value,))
    return path


def create_session_factory(database_path):
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    SystemConfig.__table__.create(engine)
    return sessionmaker(bind=engine), engine


def create_automatic_backups(backup_dir, count):
    for offset in range(count):
        created_at = NOW - timedelta(days=2, minutes=count - offset)
        filename = f"sellhelp_auto_{created_at:%Y%m%d_%H%M%S%f}.db"
        (backup_dir / filename).touch()


def test_due_backup_copies_database_records_status_and_keeps_manual_backup(tmp_path):
    """A missing automatic copy must create a readable SQLite backup without removing a manual copy."""
    database_path = create_file_database(tmp_path / "data" / "sellhelp.db")
    backup_dir = database_path.parent / "backups"
    backup_dir.mkdir()
    manual_backup = backup_dir / "yingtai_backup_20260818_120000.db"
    manual_backup.touch()
    session_factory, engine = create_session_factory(database_path)
    service = DesktopBackupService(database_path, backup_dir, now=lambda: NOW)

    try:
        with session_factory() as db:
            result = service.run_if_due(db)

        created = backup_dir / result["last_success"]["filename"]
        with sqlite3.connect(created) as connection:
            assert connection.execute("SELECT value FROM recovery_check").fetchone() == ("preserved",)
        assert result["created"] is True
        assert result["last_success"] == {
            "completed_at": NOW.isoformat(),
            "filename": "sellhelp_auto_20260819_120000000000.db",
            "size": created.stat().st_size,
        }
        assert manual_backup.exists()
    finally:
        engine.dispose()


def test_recent_success_skips_copy_until_twenty_four_hour_interval_has_elapsed(tmp_path):
    """A duplicate copy before the policy interval would waste disk space and hide a scheduler bug."""
    database_path = create_file_database(tmp_path / "data" / "sellhelp.db")
    backup_dir = database_path.parent / "backups"
    session_factory, engine = create_session_factory(database_path)
    service = DesktopBackupService(database_path, backup_dir, now=lambda: NOW)

    try:
        with session_factory() as db:
            db.add(SystemConfig(
                key="desktop_automatic_backup",
                value=json.dumps({
                    "last_success": {
                        "completed_at": (NOW - timedelta(hours=23, minutes=59)).isoformat(),
                        "filename": "sellhelp_auto_20260818_120100000000.db",
                        "size": 1,
                    },
                    "last_failure": None,
                }),
            ))
            db.commit()

            result = service.run_if_due(db)

        assert result["created"] is False
        assert not backup_dir.exists()
        assert result["is_due"] is False
    finally:
        engine.dispose()


def test_retention_keeps_fourteen_automatic_backups_and_all_protection_backups(tmp_path):
    """Retention must prune only the oldest automatic copy, never a user or recovery-protection backup."""
    database_path = create_file_database(tmp_path / "data" / "sellhelp.db")
    backup_dir = database_path.parent / "backups"
    backup_dir.mkdir()
    create_automatic_backups(backup_dir, count=14)
    manual_backup = backup_dir / "yingtai_backup_20260818_120000.db"
    pre_restore_backup = backup_dir / "pre_restore_20260818_120000.db"
    pre_migration_backup = backup_dir / "sellhelp-pre-migration-20260818120000000000.db"
    manual_backup.touch()
    pre_restore_backup.touch()
    pre_migration_backup.touch()
    session_factory, engine = create_session_factory(database_path)
    service = DesktopBackupService(database_path, backup_dir, now=lambda: NOW)

    try:
        with session_factory() as db:
            service.run_if_due(db)

        automatic_backups = sorted(backup_dir.glob("sellhelp_auto_*.db"))
        assert len(automatic_backups) == 14
        assert automatic_backups[0].name == "sellhelp_auto_20260817_114700000000.db"
        assert manual_backup.exists()
        assert pre_restore_backup.exists()
        assert pre_migration_backup.exists()
    finally:
        engine.dispose()


def test_failed_backup_removes_partial_file_records_failure_and_later_retries(tmp_path):
    """A failed write must not leave a restore candidate behind and must not block the next due run."""
    database_path = create_file_database(tmp_path / "data" / "sellhelp.db")
    backup_dir = database_path.parent / "backups"
    session_factory, engine = create_session_factory(database_path)

    def write_partial_then_raise(_source, target):
        target.write_text("partial", encoding="utf-8")
        raise OSError("disk full")

    failed_service = DesktopBackupService(
        database_path, backup_dir, now=lambda: NOW, backup_function=write_partial_then_raise
    )
    healthy_service = DesktopBackupService(database_path, backup_dir, now=lambda: NOW)

    try:
        with session_factory() as db:
            failure = failed_service.run_if_due(db)

        assert failure["created"] is False
        assert failure["last_failure"] == {
            "occurred_at": NOW.isoformat(),
            "error_type": "OSError",
        }
        assert not list(backup_dir.glob("sellhelp_auto_*.db"))

        with session_factory() as db:
            retry = healthy_service.run_if_due(db)

        assert retry["created"] is True
        assert retry["last_failure"] is None
    finally:
        engine.dispose()
