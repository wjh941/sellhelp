from datetime import datetime

import pytest
from app.models.all_models import Customer, Product, ProductBatch, ReceivableLedger, SalesOrder
from app.services.receivable_service import ReceivableService


CASH = "\u73b0\u7ed3"
CREDIT = "\u8d4a\u8d26"
PARTIAL = "\u90e8\u5206\u7ed3\u8d26"


def create_credit_order(db, customer, order_no, debt, sale_date):
    order = SalesOrder(
        order_no=order_no,
        customer_id=customer.id,
        sale_date=sale_date,
        total_amount=debt,
        final_amount=debt,
        payment_type=CREDIT,
        paid_amount=0,
        debt_amount=debt,
        status="\u5df2\u5b8c\u6210",
    )
    db.add(order)
    db.flush()
    return order


def ledger_movements(db):
    return [ledger.amount for ledger in db.query(ReceivableLedger).order_by(ReceivableLedger.id).all()]


def test_changing_credit_order_to_cash_reduces_customer_debt_once(client, db_session):
    customer = Customer(name="cash customer", current_debt=100)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-CASH", 100, datetime(2026, 1, 1))
    db_session.commit()

    response = client.post(f"/api/sales-orders/{order.id}/pay", json={"payment_type": CASH})

    assert response.status_code == 200
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(0)
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(0)
    assert ledger_movements(db_session) == [-100]
    ledger = db_session.query(ReceivableLedger).one()
    assert ledger.customer_id == customer.id
    assert ledger.sales_order_id == order.id


def test_completing_credit_order_payment_reduces_customer_debt_once(client, db_session):
    customer = Customer(name="complete customer", current_debt=100)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-COMPLETE", 100, datetime(2026, 1, 1))
    db_session.commit()

    response = client.post(f"/api/sales-orders/{order.id}/complete-payment")

    assert response.status_code == 200
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(0)
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(0)
    assert ledger_movements(db_session) == [-100]


def test_finance_partial_payment_leaves_only_remaining_debt_and_writes_negative_ledger(client, db_session):
    customer = Customer(name="partial customer", current_debt=100)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-PARTIAL", 100, datetime(2026, 1, 1))
    db_session.commit()

    response = client.post(f"/api/finance/customer/{customer.id}/repay", params={"amount": 40})

    assert response.status_code == 200
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(60)
    updated_order = db_session.get(SalesOrder, order.id)
    assert updated_order.paid_amount == pytest.approx(40)
    assert updated_order.debt_amount == pytest.approx(60)
    assert updated_order.payment_type == PARTIAL
    assert ledger_movements(db_session) == [-40]


@pytest.mark.parametrize(
    ("path_template", "request_kwargs"),
    [
        ("/api/customers/{customer_id}/pay", {"params": {"amount": 60}}),
        ("/api/finance/customer/{customer_id}/repay", {"params": {"amount": 60}}),
        ("/api/finance/batch-repay", {"json": {"items": [{"customer_id": "{customer_id}", "amount": 60}]}}),
    ],
)
def test_customer_finance_and_batch_payments_allocate_oldest_orders_first(client, db_session, path_template, request_kwargs):
    customer = Customer(name="oldest first customer", current_debt=100)
    db_session.add(customer)
    db_session.flush()
    old_order = create_credit_order(db_session, customer, "SO-OLD", 40, datetime(2026, 1, 1))
    new_order = create_credit_order(db_session, customer, "SO-NEW", 60, datetime(2026, 1, 2))
    db_session.commit()

    path = path_template.format(customer_id=customer.id)
    request_kwargs = {key: value for key, value in request_kwargs.items()}
    if "json" in request_kwargs:
        request_kwargs["json"] = {"items": [{"customer_id": customer.id, "amount": 60}]}
    response = client.post(path, **request_kwargs)

    assert response.status_code == 200
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(40)
    assert db_session.get(SalesOrder, old_order.id).debt_amount == pytest.approx(0)
    assert db_session.get(SalesOrder, old_order.id).paid_amount == pytest.approx(40)
    assert db_session.get(SalesOrder, new_order.id).debt_amount == pytest.approx(40)
    assert db_session.get(SalesOrder, new_order.id).paid_amount == pytest.approx(20)
    assert ledger_movements(db_session) == [-40, -20]


def test_service_rejects_payment_larger_than_outstanding_orders(db_session):
    customer = Customer(name="overpayment customer", current_debt=100)
    db_session.add(customer)
    db_session.flush()
    create_credit_order(db_session, customer, "SO-OVERPAY", 100, datetime(2026, 1, 1))
    db_session.commit()

    with pytest.raises(ValueError, match="exceeds outstanding"):
        ReceivableService(db_session).apply_payment(customer, 101, None, "overpayment")

    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(100)
    assert ledger_movements(db_session) == []


def test_deleting_credit_order_reverses_customer_debt_once(client, db_session):
    customer = Customer(name="delete customer", current_debt=100)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-DELETE", 100, datetime(2026, 1, 1))
    db_session.commit()

    response = client.delete(f"/api/sales-orders/{order.id}")

    assert response.status_code == 200
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(0)
    assert ledger_movements(db_session) == [-100]


def test_customer_delete_rejects_customer_with_receivable_ledger_history(client, db_session):
    customer = Customer(name="historical customer", current_debt=100)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-HISTORY", 100, datetime(2026, 1, 1))
    db_session.commit()

    assert client.delete(f"/api/sales-orders/{order.id}").status_code == 200

    response = client.delete(f"/api/customers/{customer.id}")

    assert response.status_code == 400
    assert db_session.get(Customer, customer.id) is not None
    assert db_session.query(ReceivableLedger).one().customer_id == customer.id


def test_service_rejects_inconsistent_payment_without_dirty_session(db_session):
    customer = Customer(name="inconsistent payment customer", current_debt=90)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-INCONSISTENT-PAY", 100, datetime(2026, 1, 1))
    db_session.commit()

    with pytest.raises(ValueError, match="inconsistent"):
        ReceivableService(db_session).apply_payment(customer, 10, None, "inconsistent payment")

    db_session.commit()
    db_session.expire_all()
    persisted_order = db_session.get(SalesOrder, order.id)
    persisted_customer = db_session.get(Customer, customer.id)
    assert persisted_order.debt_amount == pytest.approx(100)
    assert persisted_order.paid_amount == pytest.approx(0)
    assert persisted_customer.current_debt == pytest.approx(90)
    assert ledger_movements(db_session) == []


def test_service_rejects_inconsistent_order_transition_before_mutation(db_session):
    customer = Customer(name="inconsistent order customer", current_debt=90)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-INCONSISTENT-ORDER", 100, datetime(2026, 1, 1))
    db_session.commit()

    with pytest.raises(ValueError, match="inconsistent"):
        ReceivableService(db_session).apply_order_balance_change(order, 100, "test", order.order_no)

    db_session.commit()
    db_session.expire_all()
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(100)
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(90)
    assert ledger_movements(db_session) == []


def test_sales_order_rejects_inconsistent_customer_before_mutating_transaction_state(client, db_session):
    customer = Customer(name="inconsistent order creation customer", current_debt=90, total_consumption=12)
    product = Product(name="valid product", unit="unit", wholesale_price=10, purchase_price=6)
    db_session.add_all([customer, product])
    db_session.flush()
    batch = ProductBatch(
        product_id=product.id,
        batch_no="B-VALID",
        purchase_price=6,
        total_quantity=10,
        remaining_quantity=10,
    )
    db_session.add(batch)
    db_session.commit()

    response = client.post(
        "/api/sales-orders",
        json={
            "customer_id": customer.id,
            "payment_type": CASH,
            "items": [{"product_id": product.id, "quantity": 2, "unit_price": 10}],
        },
    )

    assert response.status_code == 400
    assert "reconcil" in response.json()["detail"].lower()
    db_session.expire_all()
    assert db_session.query(SalesOrder).count() == 0
    assert db_session.get(ProductBatch, batch.id).remaining_quantity == pytest.approx(10)
    persisted_customer = db_session.get(Customer, customer.id)
    assert persisted_customer.current_debt == pytest.approx(90)
    assert persisted_customer.total_consumption == pytest.approx(12)
    assert db_session.query(ReceivableLedger).count() == 0


def test_batch_repayment_does_not_commit_inconsistent_customer_changes(client, db_session):
    customer = Customer(name="inconsistent batch customer", current_debt=90)
    db_session.add(customer)
    db_session.flush()
    order = create_credit_order(db_session, customer, "SO-INCONSISTENT-BATCH", 100, datetime(2026, 1, 1))
    db_session.commit()

    response = client.post("/api/finance/batch-repay", json={"items": [{"customer_id": customer.id, "amount": 10}]})

    assert response.status_code == 200
    assert response.json()["details"][0]["status"] == "error"
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(100)
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(90)
    assert ledger_movements(db_session) == []


def test_payment_change_rejects_credit_limit_before_mutation(client, db_session):
    customer = Customer(name="limited customer", credit_limit=50, current_debt=0)
    db_session.add(customer)
    db_session.flush()
    order = SalesOrder(
        order_no="SO-LIMIT",
        customer_id=customer.id,
        sale_date=datetime(2026, 1, 1),
        total_amount=100,
        final_amount=100,
        payment_type=CASH,
        paid_amount=100,
        debt_amount=0,
        status="已完成",
    )
    db_session.add(order)
    db_session.commit()

    response = client.post(f"/api/sales-orders/{order.id}/pay", json={"payment_type": CREDIT})

    assert response.status_code == 400
    db_session.expire_all()
    assert db_session.get(SalesOrder, order.id).debt_amount == pytest.approx(0)
    assert db_session.get(SalesOrder, order.id).payment_type == CASH
    assert db_session.get(Customer, customer.id).current_debt == pytest.approx(0)
    assert ledger_movements(db_session) == []
