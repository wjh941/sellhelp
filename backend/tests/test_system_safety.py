from datetime import datetime
from urllib.parse import quote

import pytest

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
