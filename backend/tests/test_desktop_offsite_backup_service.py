import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.all_models import SystemConfig
from app.services.desktop_offsite_backup_service import DesktopOffsiteBackupService


NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def create_sqlite_backup(path, value="preserved"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE recovery_check (value TEXT)")
        connection.execute("INSERT INTO recovery_check VALUES (?)", (value,))
    return path


def create_session_factory(database_path):
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    SystemConfig.__table__.create(engine)
    return sessionmaker(bind=engine), engine


def create_automatic_files(directory, count):
    for offset in range(count):
        created_at = NOW - timedelta(days=2, minutes=count - offset)
        (directory / f"sellhelp_auto_{created_at:%Y%m%d_%H%M%S%f}.db").touch()


def test_replica_is_readable_and_keeps_only_automatic_files(tmp_path):
    source = create_sqlite_backup(tmp_path / "local" / "sellhelp_auto_20260819_120000000000.db")
    target = tmp_path / "external"
    target.mkdir()
    create_automatic_files(target, count=14)
    protected = target / "customer-notes.txt"
    protected.write_text("keep", encoding="utf-8")
    session_factory, engine = create_session_factory(source)
    service = DesktopOffsiteBackupService(source.parent, now=lambda: NOW)

    try:
        with session_factory() as db:
            service.configure(db, target)
            result = service.sync_latest(db)

        with sqlite3.connect(target / source.name) as copy:
            assert copy.execute("SELECT value FROM recovery_check").fetchone() == ("preserved",)
        assert result["last_success"] == {
            "completed_at": NOW.isoformat(),
            "filename": source.name,
            "size": (target / source.name).stat().st_size,
        }
        assert len(list(target.glob("sellhelp_auto_*.db"))) == 14
        assert protected.read_text(encoding="utf-8") == "keep"
    finally:
        engine.dispose()


def test_replica_failure_cleans_temporary_file_and_later_retry_succeeds(tmp_path):
    source = create_sqlite_backup(tmp_path / "local" / "sellhelp_auto_20260819_120000000000.db")
    target = tmp_path / "external"
    target.mkdir()
    session_factory, engine = create_session_factory(source)

    def copy_partial_then_raise(_source, destination):
        destination.write_text("partial", encoding="utf-8")
        raise OSError("target is full")

    try:
        with session_factory() as db:
            failed_service = DesktopOffsiteBackupService(
                source.parent, now=lambda: NOW, copy_function=copy_partial_then_raise
            )
            failed_service.configure(db, target)
            failed = failed_service.sync_latest(db)
            retried = DesktopOffsiteBackupService(source.parent, now=lambda: NOW).sync_latest(db)

        assert failed["last_failure"] == {
            "occurred_at": NOW.isoformat(),
            "error_type": "OSError",
        }
        assert not list(target.glob("*.tmp"))
        assert retried["last_failure"] is None
        assert (target / source.name).is_file()
    finally:
        engine.dispose()


def test_configuration_rejects_unsafe_target_redacts_path_and_disable_keeps_files(tmp_path):
    database_path = create_sqlite_backup(tmp_path / "local" / "sellhelp_auto_20260819_120000000000.db")
    target = tmp_path / "external"
    target.mkdir()
    preserved = target / "sellhelp_auto_20260819_120000000000.db"
    preserved.write_bytes(b"existing")
    session_factory, engine = create_session_factory(database_path)
    service = DesktopOffsiteBackupService(database_path.parent, now=lambda: NOW)

    try:
        with session_factory() as db:
            with pytest.raises(ValueError):
                service.configure(db, "relative-directory")
            with pytest.raises(ValueError):
                service.configure(db, tmp_path / "missing")
            configured = service.configure(db, target)
            disabled = service.disable(db)

        assert configured["configured"] is True
        assert configured["directory_name"] == "external"
        assert str(target) not in json.dumps(configured)
        assert disabled["configured"] is False
        assert preserved.is_file()
    finally:
        engine.dispose()


def test_configured_target_without_a_local_automatic_backup_is_pending(tmp_path):
    database_path = create_sqlite_backup(tmp_path / "database.db")
    target = tmp_path / "external"
    target.mkdir()
    session_factory, engine = create_session_factory(database_path)
    service = DesktopOffsiteBackupService(tmp_path / "empty", now=lambda: NOW)

    try:
        with session_factory() as db:
            service.configure(db, target)
            result = service.sync_latest(db)

        assert result["is_pending"] is True
        assert result["last_success"] is None
        assert result["last_failure"] is None
    finally:
        engine.dispose()


def test_configured_target_with_an_unsynced_local_backup_reports_pending(tmp_path):
    source = create_sqlite_backup(tmp_path / "local" / "sellhelp_auto_20260819_120000000000.db")
    target = tmp_path / "external"
    target.mkdir()
    session_factory, engine = create_session_factory(source)
    service = DesktopOffsiteBackupService(source.parent, now=lambda: NOW)

    try:
        with session_factory() as db:
            service.configure(db, target)
            status = service.status(db, enabled=True)

        assert status["configured"] is True
        assert status["is_pending"] is True
        assert status["last_success"] is None
    finally:
        engine.dispose()


def test_replica_ignores_noncanonical_prefixed_files_when_selecting_and_pruning(tmp_path):
    source = create_sqlite_backup(tmp_path / "local" / "sellhelp_auto_20260819_120000000000.db")
    fake_local = source.parent / "sellhelp_auto_20261340_251111111111.db"
    fake_local.write_bytes(b"not a generated backup")
    target = tmp_path / "external"
    target.mkdir()
    create_automatic_files(target, count=14)
    fake_replica = target / "sellhelp_auto_20261340_251111111111.db"
    fake_replica.write_bytes(b"keep")
    session_factory, engine = create_session_factory(source)
    service = DesktopOffsiteBackupService(source.parent, now=lambda: NOW)

    try:
        with session_factory() as db:
            service.configure(db, target)
            result = service.sync_latest(db)

        assert result["last_success"]["filename"] == source.name
        assert (target / source.name).is_file()
        assert fake_replica.read_bytes() == b"keep"
        assert len([path for path in target.glob("sellhelp_auto_*.db") if path != fake_replica]) == 14
    finally:
        engine.dispose()
