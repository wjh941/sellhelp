import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.desktop_runtime import desktop_data_dir
from app.desktop_secrets import ensure_desktop_jwt_secret


@dataclass(frozen=True)
class StartupResult:
    migration_applied: bool
    backup_path: Path | None


def configure_desktop_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "sellhelp.log"
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, "_sellhelp_desktop_log", False):
            root_logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler._sellhelp_desktop_log = True
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root_logger.addHandler(handler)
    return log_path


def _database_url(database_path: Path) -> str:
    return f"sqlite:///{database_path.as_posix()}"


def _alembic_config(database_path: Path) -> Config:
    backend_dir = Path(__file__).resolve().parent.parent
    config = Config(str(backend_dir / "alembic.ini"))
    config.attributes["database_url"] = _database_url(database_path)
    config.attributes["skip_logging_config"] = True
    return config


def _is_empty_database(database_path: Path) -> bool:
    if not database_path.exists() or database_path.stat().st_size == 0:
        return True
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0] == 0


def _has_alembic_version(database_path: Path) -> bool:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'alembic_version'"
        ).fetchone() is not None


def _current_revision(database_path: Path) -> str | None:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    return row[0] if row else None


def _sqlite_backup(database_path: Path, backups_dir: Path) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backups_dir / f"sellhelp-pre-migration-{datetime.now(timezone.utc):%Y%m%d%H%M%S%f}.db"
    with sqlite3.connect(database_path) as source, sqlite3.connect(backup_path) as destination:
        source.backup(destination)
    return backup_path


def _upgrade_to_head(database_path: Path) -> None:
    command.upgrade(_alembic_config(database_path), "head")


def prepare_desktop_startup(data_dir: Path | None = None) -> StartupResult:
    root_dir = Path(data_dir) if data_dir is not None else desktop_data_dir()
    database_path = root_dir / "data" / "sellhelp.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    configure_desktop_logging(root_dir / "logs")
    os.environ["SELLHELP_JWT_SECRET"] = ensure_desktop_jwt_secret(root_dir / "config")

    if _is_empty_database(database_path):
        _upgrade_to_head(database_path)
        return StartupResult(migration_applied=True, backup_path=None)

    config = _alembic_config(database_path)
    if not _has_alembic_version(database_path):
        backup_path = _sqlite_backup(database_path, root_dir / "backups")
        command.stamp(config, "d8f13722a89d")
        command.upgrade(config, "head")
        return StartupResult(migration_applied=True, backup_path=backup_path)

    if _current_revision(database_path) != ScriptDirectory.from_config(config).get_current_head():
        command.upgrade(config, "head")
        return StartupResult(migration_applied=True, backup_path=None)
    return StartupResult(migration_applied=False, backup_path=None)
