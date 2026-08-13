from datetime import datetime

import pytest
from app.models.all_models import Customer, ReceivableLedger, SalesOrder
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
