from datetime import datetime

import pytest

from app.models.all_models import (
    Customer,
    InventoryMovement,
    Product,
    ProductBatch,
    ReceivableLedger,
    ReturnOrder,
    SalesOrder,
    SalesOrderItem,
)


CUSTOMER_RETURN = "\u5ba2\u6237\u9000\u8d27"
CREDIT = "\u8d4a\u8d26"


def create_credit_sale(db_session, *, quantity=4, unit_price=10, outstanding_debt=None):
    outstanding_debt = quantity * unit_price if outstanding_debt is None else outstanding_debt
    customer = Customer(name="Return customer", current_debt=outstanding_debt)
    product = Product(name="Returned product", unit="unit", purchase_price=3)
    db_session.add_all([customer, product])
    db_session.flush()
    order = SalesOrder(
        order_no="SO-RETURN-SOURCE",
        customer_id=customer.id,
        sale_date=datetime(2026, 8, 14),
        total_amount=quantity * unit_price,
        final_amount=quantity * unit_price,
        payment_type=CREDIT,
        paid_amount=0,
        debt_amount=outstanding_debt,
        status="\u5df2\u5b8c\u6210",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(SalesOrderItem(
        sales_order_id=order.id,
        product_id=product.id,
        quantity=quantity,
        unit_price=unit_price,
        cost_price=3,
        amount=quantity * unit_price,
        profit=0,
    ))
    db_session.commit()
    return customer, product, order


def return_payload(*, customer_id, product_id, related_order_no=None, quantity=1):
    return {
        "return_type": CUSTOMER_RETURN,
        "related_order_no": related_order_no,
        "partner_id": customer_id,
        "product_id": product_id,
        "quantity": quantity,
        "refund_amount": 999,
    }


@pytest.mark.parametrize("related_order_no", [None, "SO-NOT-FOUND"])
def test_customer_return_rejects_missing_or_unknown_source_without_mutation(client, db_session, related_order_no):
    customer = Customer(name="Unlinked customer")
    product = Product(name="Unlinked product", unit="unit")
    db_session.add_all([customer, product])
    db_session.commit()

    response = client.post(
        "/api/returns",
        json=return_payload(
            customer_id=customer.id,
            product_id=product.id,
            related_order_no=related_order_no,
        ),
    )

    assert response.status_code == 400
    assert db_session.query(ReturnOrder).count() == 0
    assert db_session.query(ProductBatch).count() == 0
    assert db_session.query(InventoryMovement).count() == 0


def test_customer_return_rejects_source_owned_by_another_customer_without_mutation(client, db_session):
    customer, product, order = create_credit_sale(db_session)
    other_customer = Customer(name="Other customer")
    db_session.add(other_customer)
    db_session.commit()

    response = client.post(
        "/api/returns",
        json=return_payload(
            customer_id=other_customer.id,
            product_id=product.id,
            related_order_no=order.order_no,
        ),
    )

    assert response.status_code == 400
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(40)
    assert db_session.query(ReturnOrder).count() == 0
    assert db_session.query(ProductBatch).count() == 0
    assert db_session.query(InventoryMovement).count() == 0


def test_customer_return_rejects_product_not_on_source_order_without_mutation(client, db_session):
    customer, _, order = create_credit_sale(db_session)
    other_product = Product(name="Other product", unit="unit")
    db_session.add(other_product)
    db_session.commit()

    response = client.post(
        "/api/returns",
        json=return_payload(
            customer_id=customer.id,
            product_id=other_product.id,
            related_order_no=order.order_no,
        ),
    )

    assert response.status_code == 400
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(40)
    assert db_session.query(ReturnOrder).count() == 0
    assert db_session.query(ProductBatch).count() == 0
    assert db_session.query(InventoryMovement).count() == 0


def test_customer_return_rejects_quantity_above_unreturned_source_quantity(client, db_session):
    customer, product, order = create_credit_sale(db_session)

    accepted = client.post(
        "/api/returns",
        json=return_payload(
            customer_id=customer.id,
            product_id=product.id,
            related_order_no=order.order_no,
            quantity=2,
        ),
    )
    assert accepted.status_code == 200

    response = client.post(
        "/api/returns",
        json=return_payload(
            customer_id=customer.id,
            product_id=product.id,
            related_order_no=order.order_no,
            quantity=3,
        ),
    )

    assert response.status_code == 400
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(20)
    assert db_session.query(ReturnOrder).count() == 1
    assert db_session.query(ProductBatch).count() == 1
    assert db_session.query(InventoryMovement).count() == 1


def test_customer_return_reduces_open_source_order_debt(client, db_session):
    customer, product, order = create_credit_sale(db_session, quantity=4, unit_price=10)

    response = client.post(
        "/api/returns",
        json=return_payload(
            customer_id=customer.id,
            product_id=product.id,
            related_order_no=order.order_no,
            quantity=2,
        ),
    )

    assert response.status_code == 200
    assert response.json()["refund_amount"] == pytest.approx(20)
    return_order = db_session.query(ReturnOrder).one()
    assert return_order.batch_id is not None
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(20)
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(20)
    ledger = db_session.query(ReceivableLedger).one()
    assert (ledger.amount, ledger.reason, ledger.reference_no) == (-20, "customer_return", return_order.order_no)


def test_customer_return_credit_is_capped_at_source_outstanding_debt(client, db_session):
    customer, product, order = create_credit_sale(
        db_session, quantity=4, unit_price=10, outstanding_debt=10,
    )

    response = client.post(
        "/api/returns",
        json=return_payload(
            customer_id=customer.id,
            product_id=product.id,
            related_order_no=order.order_no,
            quantity=4,
        ),
    )

    assert response.status_code == 200
    assert response.json()["refund_amount"] == pytest.approx(40)
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(0)
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(0)
    assert db_session.query(ReceivableLedger).one().amount == pytest.approx(-10)
