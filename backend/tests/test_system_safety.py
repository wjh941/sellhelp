from datetime import datetime
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

import pytest
from sqlalchemy import create_engine

from app import database
from app.models.all_models import Customer, Product, SalesOrder, SalesOrderItem, SystemConfig
from app.routers import system_router


COMPLETED = "\u5df2\u5b8c\u6210"


def create_completed_sale(db, order_no, sale_date, product_name, amount, status=COMPLETED, product=None):
    customer = Customer(name=f"Customer {order_no}")
    product = product or Product(name=product_name, unit="unit", purchase_price=1)
    db.add_all([customer, product])
    db.flush()

    order = SalesOrder(
        order_no=order_no,
        customer_id=customer.id,
        sale_date=sale_date,
        total_amount=amount,
        final_amount=amount,
        status=status,
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        sales_order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=amount,
        amount=amount,
    ))
    db.commit()
    return product


def test_dashboard_metrics_zero_fill_and_top_products(client, db_session):
    product_a = create_completed_sale(db_session, "SO-METRICS-A", datetime(2026, 8, 12), "A", 30)
    create_completed_sale(db_session, "SO-METRICS-B", datetime(2026, 8, 14), "B", 75)
    create_completed_sale(db_session, "SO-METRICS-C", datetime(2026, 8, 14), "A", 20, product=product_a)
    create_completed_sale(db_session, "SO-METRICS-D", datetime(2026, 8, 14), "Ignored", 500, status="\u5df2\u9000\u8d27")

    response = client.get("/api/dashboard/metrics", params={"end_date": "2026-08-14"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["daily_sales"] == [
        {"date": "2026-08-08", "amount": 0.0},
        {"date": "2026-08-09", "amount": 0.0},
        {"date": "2026-08-10", "amount": 0.0},
        {"date": "2026-08-11", "amount": 0.0},
        {"date": "2026-08-12", "amount": 30.0},
        {"date": "2026-08-13", "amount": 0.0},
        {"date": "2026-08-14", "amount": 95.0},
    ]
    assert payload["top_products"] == [
        {"product_id": 2, "product_name": "B", "amount": 75.0},
        {"product_id": 1, "product_name": "A", "amount": 50.0},
    ]


@pytest.mark.parametrize("filename", ["../yingtai.db", "C:\\\\temp\\\\bad.db", "not-a-backup.txt"])
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/system/restore"),
        ("get", "/api/system/backups/{filename}"),
        ("delete", "/api/system/backups/{filename}"),
    ],
)
def test_backup_operations_reject_unsafe_filenames(client, method, path, filename):
    response = getattr(client, method)(
        path.format(filename=quote(filename, safe="")),
        params={"backup_file": filename} if method == "post" else None,
    )

    assert response.status_code == 400


def test_backup_status_exposes_desktop_policy_without_a_database_path(client, db_session, monkeypatch, tmp_path):
    """The Settings status must show recovery policy without exposing local data locations."""
    database_path = tmp_path / "configured.db"
    database_path.touch()
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("SELLHELP_DESKTOP_MODE", "1")
    db_session.add(SystemConfig(
        key="desktop_automatic_backup",
        value=json.dumps({
            "last_success": {
                "completed_at": "2026-08-19T00:00:00+00:00",
                "filename": "sellhelp_auto_20260819_000000000000.db",
                "size": 32,
            },
            "last_failure": None,
        }),
    ))
    db_session.commit()

    response = client.get("/api/system/backup-status")

    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["interval_hours"] == 24
    assert response.json()["retention_count"] == 14
    assert response.json()["last_success"]["filename"] == "sellhelp_auto_20260819_000000000000.db"
    assert "path" not in json.dumps(response.json())


def test_backup_operations_allow_only_valid_automatic_backup_filenames(client, monkeypatch, tmp_path):
    """Automatic copies must remain downloadable without weakening the backup-directory boundary."""
    database_path = tmp_path / "configured.db"
    database_path.touch()
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    backup_dir = database.active_backup_directory()
    backup_dir.mkdir()
    filename = "sellhelp_auto_20260819_000000000000.db"
    (backup_dir / filename).write_bytes(b"automatic backup")

    valid = client.get(f"/api/system/backups/{filename}")
    invalid = client.get("/api/system/backups/sellhelp_auto_.._outside.db")

    assert valid.status_code == 200
    assert invalid.status_code == 400


def test_backup_uses_active_database_parent_and_sqlite_backup_api(client, monkeypatch, tmp_path):
    database_path = tmp_path / "configured.db"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE recovery_check (value TEXT)")
    connection.execute("INSERT INTO recovery_check VALUES ('backup value')")
    connection.commit()
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")

    backup = client.post("/api/system/backup")

    try:
        assert backup.status_code == 200
        backup_path = Path(backup.json()["backup_path"])
        assert backup_path.parent == database_path.parent / "backups"
        with sqlite3.connect(backup_path) as backup_connection:
            assert backup_connection.execute("SELECT value FROM recovery_check").fetchone() == ("backup value",)
    finally:
        connection.close()


def test_restore_disposes_connections_and_requires_desktop_restart(client, monkeypatch, tmp_path):
    database_path = tmp_path / "configured.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE recovery_check (value TEXT)")
        connection.execute("INSERT INTO recovery_check VALUES ('backup value')")

    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    backup = client.post("/api/system/backup")
    assert backup.status_code == 200

    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE recovery_check SET value = 'changed value'")

    active_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    previous_pool = active_engine.pool
    monkeypatch.setattr(system_router, "engine", active_engine)
    restored = client.post("/api/system/restore", params={"backup_file": backup.json()["backup_file"]})

    try:
        assert restored.status_code == 200
        assert restored.json()["restart_required"] is True
        assert active_engine.pool is not previous_pool
        with sqlite3.connect(database_path) as connection:
            assert connection.execute("SELECT value FROM recovery_check").fetchone() == ("backup value",)
        with sqlite3.connect(restored.json()["pre_restore_backup"]) as connection:
            assert connection.execute("SELECT value FROM recovery_check").fetchone() == ("changed value",)
    finally:
        active_engine.dispose()


@pytest.mark.parametrize("database_url", ["sqlite://", "sqlite:///:memory:", "postgresql://example/sellhelp"])
@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/system/backup", None),
        ("/api/system/restore", {"backup_file": "yingtai_backup_20260814_120000.db"}),
    ],
)
def test_backup_operations_reject_non_file_database_urls(client, monkeypatch, database_url, path, params):
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", database_url)

    response = client.post(path, params=params)

    assert response.status_code == 400
    assert "file-based SQLite" in response.json()["detail"]
