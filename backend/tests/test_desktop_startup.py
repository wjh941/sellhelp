import logging
import sqlite3

from starlette.testclient import TestClient

from app.desktop_secrets import ensure_desktop_jwt_secret, load_desktop_jwt_secret
from app.main import create_app
from app.desktop_startup import configure_desktop_logging, prepare_desktop_startup


def role_codes_from_database(database_path):
    with sqlite3.connect(database_path) as connection:
        return {row[0] for row in connection.execute("SELECT code FROM roles")}


def has_table(database_path, table_name):
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)
        ).fetchone() is not None


def create_legacy_business_database(database_path):
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE system_configs (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT, "
            "description TEXT, updated_at DATETIME)"
        )
        connection.execute("INSERT INTO system_configs (key, value) VALUES ('legacy', 'preserved')")
    return database_path


def test_new_desktop_database_upgrades_to_head(tmp_path):
    result = prepare_desktop_startup(data_dir=tmp_path)
    database_path = tmp_path / "data" / "sellhelp.db"

    assert database_path.is_file()
    assert result.migration_applied is True
    assert role_codes_from_database(database_path) == {
        "owner", "warehouse_operator", "sales_clerk",
    }
    assert (tmp_path / "config").is_dir()
    assert (tmp_path / "logs" / "sellhelp.log").is_file()


def test_existing_legacy_database_is_backed_up_then_migrated(tmp_path):
    legacy_path = create_legacy_business_database(tmp_path / "data" / "sellhelp.db")

    result = prepare_desktop_startup(data_dir=tmp_path)

    assert result.backup_path is not None and result.backup_path.is_file()
    assert has_table(legacy_path, "users")
    assert role_codes_from_database(legacy_path) == {
        "owner", "warehouse_operator", "sales_clerk",
    }
    with sqlite3.connect(result.backup_path) as connection:
        assert connection.execute("SELECT value FROM system_configs WHERE key = 'legacy'").fetchone() == (
            "preserved",
        )
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'alembic_version'"
        ).fetchone() is None


def test_already_migrated_database_does_not_back_up_or_reapply_migrations(tmp_path):
    prepare_desktop_startup(data_dir=tmp_path)

    result = prepare_desktop_startup(data_dir=tmp_path)

    assert result.migration_applied is False
    assert result.backup_path is None


def test_desktop_secret_round_trips_for_same_windows_user(tmp_path):
    config_dir = tmp_path / "config"
    secret = ensure_desktop_jwt_secret(config_dir)

    assert len(secret) >= 32
    assert load_desktop_jwt_secret(config_dir) == secret
    assert secret.encode("utf-8") not in (config_dir / "jwt-secret.bin").read_bytes()


def test_desktop_logging_creates_utf8_rotating_log_file(tmp_path):
    log_path = configure_desktop_logging(tmp_path / "logs")
    logging.getLogger("sellhelp.desktop.startup-test").warning("desktop startup log entry")

    assert log_path.name == "sellhelp.log"
    assert log_path.read_text(encoding="utf-8").endswith("desktop startup log entry\n")


def test_desktop_lifespan_prepares_data_before_serving_requests(monkeypatch, tmp_path):
    monkeypatch.setenv("SELLHELP_DESKTOP_MODE", "1")
    monkeypatch.setenv("SELLHELP_DATA_DIR", str(tmp_path))

    with TestClient(create_app()):
        assert role_codes_from_database(tmp_path / "data" / "sellhelp.db") == {
            "owner", "warehouse_operator", "sales_clerk",
        }
