from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pytest

from app import database
from app.models.all_models import Customer, Product, SalesOrder, SalesOrderItem


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


def test_backup_and_restore_use_configured_file_sqlite_database(client, monkeypatch, tmp_path):
    database_path = tmp_path / "configured.db"
    database_path.write_bytes(b"configured database")
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")

    system_info = client.get("/api/system/info")
    backup = client.post("/api/system/backup")

    assert system_info.status_code == 200
    assert system_info.json()["database"] == {
        "path": str(database_path),
        "size": len(b"configured database"),
        "tables": {
            "products": 0,
            "customers": 0,
            "suppliers": 0,
            "sales_orders": 0,
            "batch_records": 0,
        },
    }
    assert backup.status_code == 200
    backup_path = backup.json()["backup_path"]
    assert Path(backup_path).read_bytes() == b"configured database"

    database_path.write_bytes(b"changed database")
    restored = client.post("/api/system/restore", params={"backup_file": backup.json()["backup_file"]})

    assert restored.status_code == 200
    assert database_path.read_bytes() == b"configured database"
    assert Path(restored.json()["pre_restore_backup"]).read_bytes() == b"changed database"


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
