from datetime import date

import pytest

from app.models.all_models import (
    Customer,
    InventoryMovement,
    Product,
    ProductBatch,
    Supplier,
)
from app.services.inventory_service import InventoryService


CUSTOMER_RETURN = "\u5ba2\u6237\u9000\u8d27"
SUPPLIER_RETURN = "\u4f9b\u5e94\u5546\u9000\u8d27"


def make_product(db_session, *, quantity=10, expiry_date=None):
    product = Product(name="Integrity product", unit="unit", purchase_price=3, retail_price=6)
    customer = Customer(name="Integrity customer")
    supplier = Supplier(name="Integrity supplier")
    db_session.add_all([product, customer, supplier])
    db_session.flush()
    batch = ProductBatch(
        product_id=product.id,
        batch_no="B-INTEGRITY",
        purchase_price=3,
        total_quantity=quantity,
        remaining_quantity=quantity,
        expiry_date=expiry_date,
        is_expired=False,
    )
    db_session.add(batch)
    db_session.commit()
    return product, customer, supplier, batch


def movement_rows(db_session, *, product_id):
    return db_session.query(InventoryMovement).filter(
        InventoryMovement.product_id == product_id
    ).order_by(InventoryMovement.id).all()


def test_inventory_service_rejects_nonpositive_quantities(db_session):
    service = InventoryService(db_session)

    with pytest.raises(ValueError, match="greater than zero"):
        service.find_fifo_batches(1, 0)
    with pytest.raises(ValueError, match="greater than zero"):
        service.record_movement(1, None, "inbound", 0, "test")


def test_expired_batch_is_rejected_without_changing_stock(client, db_session):
    product, customer, _, batch = make_product(db_session, expiry_date=date.today())

    response = client.post(
        "/api/sales-orders",
        json={
            "customer_id": customer.id,
            "items": [{"product_id": product.id, "quantity": 2, "unit_price": 6}],
        },
    )

    assert response.status_code == 400
    db_session.expire_all()
    assert db_session.get(ProductBatch, batch.id).remaining_quantity == pytest.approx(10)
    assert movement_rows(db_session, product_id=product.id) == []


def test_purchase_records_inbound_movement(client, db_session):
    product = Product(name="Purchase product", unit="unit")
    supplier = Supplier(name="Purchase supplier")
    db_session.add_all([product, supplier])
    db_session.commit()

    response = client.post(
        "/api/purchase-orders",
        json={
            "supplier_id": supplier.id,
            "operator": "buyer",
            "items": [{"product_id": product.id, "batch_no": "B-PURCHASE", "quantity": 4, "unit_price": 3}],
        },
    )

    assert response.status_code == 200
    movements = movement_rows(db_session, product_id=product.id)
    assert len(movements) == 1
    assert movements[0].quantity == pytest.approx(4)
    assert movements[0].direction == "inbound"
    assert movements[0].reason == "purchase"
    assert movements[0].reference_no == response.json()["order_no"]


def test_sale_records_outbound_movement_and_delete_records_reversal(client, db_session):
    product, customer, _, batch = make_product(db_session)

    sale = client.post(
        "/api/sales-orders",
        json={
            "customer_id": customer.id,
            "operator": "seller",
            "items": [{"product_id": product.id, "quantity": 2, "unit_price": 6}],
        },
    )
    assert sale.status_code == 200
    assert db_session.get(ProductBatch, batch.id).remaining_quantity == pytest.approx(8)
    movements = movement_rows(db_session, product_id=product.id)
    assert [(row.direction, row.quantity, row.reason) for row in movements] == [("outbound", 2, "sale")]

    deleted = client.delete(f"/api/sales-orders/{sale.json()['id']}")
    assert deleted.status_code == 200
    assert db_session.get(ProductBatch, batch.id).remaining_quantity == pytest.approx(10)
    movements = movement_rows(db_session, product_id=product.id)
    assert [(row.direction, row.quantity, row.reason) for row in movements] == [
        ("outbound", 2, "sale"),
        ("inbound", 2, "sale_reversal"),
    ]


def test_supplier_return_without_batch_uses_saleable_stock_and_records_outbound(client, db_session):
    product, _, supplier, batch = make_product(db_session, expiry_date=date.today())
    saleable_batch = ProductBatch(
        product_id=product.id,
        batch_no="B-SALEABLE",
        purchase_price=4,
        total_quantity=5,
        remaining_quantity=5,
        expiry_date=None,
    )
    db_session.add(saleable_batch)
    db_session.commit()

    response = client.post(
        "/api/returns",
        json={
            "return_type": SUPPLIER_RETURN,
            "partner_id": supplier.id,
            "product_id": product.id,
            "quantity": 2,
            "refund_amount": 0,
            "operator": "buyer",
        },
    )

    assert response.status_code == 200
    assert response.json()["batch_id"] is None
    assert db_session.get(ProductBatch, batch.id).remaining_quantity == pytest.approx(10)
    assert db_session.get(ProductBatch, saleable_batch.id).remaining_quantity == pytest.approx(3)
    movement = movement_rows(db_session, product_id=product.id)[0]
    assert (movement.direction, movement.quantity, movement.reason) == ("outbound", 2, "supplier_return")
    assert movement.batch_id == saleable_batch.id


def test_supplier_return_without_batch_can_span_saleable_batches(client, db_session):
    product, _, supplier, first_batch = make_product(db_session, quantity=1)
    second_batch = ProductBatch(
        product_id=product.id,
        batch_no="B-SECOND",
        purchase_price=4,
        total_quantity=2,
        remaining_quantity=2,
        expiry_date=None,
    )
    db_session.add(second_batch)
    db_session.commit()

    response = client.post(
        "/api/returns",
        json={
            "return_type": SUPPLIER_RETURN,
            "partner_id": supplier.id,
            "product_id": product.id,
            "quantity": 3,
            "refund_amount": 0,
        },
    )

    assert response.status_code == 200
    assert db_session.get(ProductBatch, first_batch.id).remaining_quantity == pytest.approx(0)
    assert db_session.get(ProductBatch, second_batch.id).remaining_quantity == pytest.approx(0)
    assert [row.quantity for row in movement_rows(db_session, product_id=product.id)] == [1, 2]


def test_customer_return_and_confirmed_stocktake_record_movements(client, db_session):
    product, customer, _, batch = make_product(db_session, quantity=5)

    returned = client.post(
        "/api/returns",
        json={
            "return_type": CUSTOMER_RETURN,
            "related_order_no": "missing-order",
            "partner_id": customer.id,
            "product_id": product.id,
            "quantity": 2,
            "refund_amount": 0,
            "operator": "seller",
        },
    )
    assert returned.status_code == 200

    stocktake = client.post(
        "/api/stock-takes/confirm",
        json=[{
            "product_id": product.id,
            "batch_id": batch.id,
            "actual_quantity": 6,
            "reason": "count correction",
        }],
    )
    assert stocktake.status_code == 200
    rows = movement_rows(db_session, product_id=product.id)
    assert [(row.direction, row.quantity, row.reason) for row in rows] == [
        ("inbound", 2, "customer_return"),
        ("inbound", 1, "stocktake_adjustment"),
    ]
