from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..models.all_models import Customer, ReceivableLedger, SalesOrder


class ReceivableService:
    def __init__(self, db: Session):
        self.db = db

    def _outstanding_debt_excluding_order(self, customer_id: int, order_id: Optional[int]) -> float:
        with self.db.no_autoflush:
            query = self.db.query(SalesOrder.debt_amount).filter(
                SalesOrder.customer_id == customer_id,
                SalesOrder.debt_amount > 0,
            )
            if order_id is not None:
                query = query.filter(SalesOrder.id != order_id)
            return round(sum(row[0] or 0 for row in query.all()), 2)

    def outstanding_debt(self, customer_id: int) -> float:
        return self._outstanding_debt_excluding_order(customer_id, None)

    def validate_customer_aggregate(self, customer: Customer, expected_debt: float):
        current_debt = round(customer.current_debt or 0, 2)
        expected_debt = round(expected_debt, 2)
        if current_debt != expected_debt:
            raise ValueError(
                "Customer receivable aggregate is inconsistent: "
                f"current_debt={current_debt:.2f}, outstanding_order_debt={expected_debt:.2f}; "
                "reconcile before changing receivables"
            )

    def validate_order_balance_change(self, order: SalesOrder, old_debt: float, new_debt: Optional[float] = None):
        customer = order.customer or self.db.get(Customer, order.customer_id)
        if not customer:
            raise ValueError("Customer does not exist")

        old_debt = round(old_debt or 0, 2)
        other_debt = self._outstanding_debt_excluding_order(customer.id, order.id)
        self.validate_customer_aggregate(customer, other_debt + old_debt)
        return customer, round(order.debt_amount if new_debt is None else new_debt or 0, 2)

    def apply_order_balance_change(self, order: SalesOrder, old_debt: float, reason: str, reference_no: Optional[str]):
        customer, new_debt = self.validate_order_balance_change(order, old_debt)
        old_debt = round(old_debt or 0, 2)

        delta = round(new_debt - old_debt, 2)
        if delta == 0:
            return None

        customer.current_debt = round((customer.current_debt or 0) + delta, 2)
        if customer.current_debt < 0:
            raise ValueError("Customer receivable balance cannot be negative")

        ledger = ReceivableLedger(
            customer_id=customer.id,
            sales_order_id=order.id,
            amount=delta,
            reason=reason,
            reference_no=reference_no,
        )
        self.db.add(ledger)
        return ledger

    def apply_payment(self, customer: Customer, amount: float, allocations: Optional[Iterable] = None, remark: Optional[str] = None):
        amount = round(amount or 0, 2)
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero")

        orders = self.db.query(SalesOrder).filter(
            SalesOrder.customer_id == customer.id,
            SalesOrder.debt_amount > 0,
        ).order_by(SalesOrder.sale_date.asc(), SalesOrder.id.asc()).all()
        outstanding = round(sum(order.debt_amount for order in orders), 2)
        self.validate_customer_aggregate(customer, outstanding)
        if amount > outstanding:
            raise ValueError("Payment amount exceeds outstanding receivables")

        remaining = amount
        payment_allocations = []
        for order in orders:
            if remaining <= 0:
                break
            applied = min(round(order.debt_amount, 2), remaining)
            old_debt = order.debt_amount
            order.paid_amount = round((order.paid_amount or 0) + applied, 2)
            order.debt_amount = round(old_debt - applied, 2)
            if order.debt_amount == 0:
                order.paid_amount = order.final_amount
                order.payment_type = "\u73b0\u7ed3"
                order.status = "\u5df2\u5b8c\u6210"
            elif order.paid_amount > 0:
                order.payment_type = "\u90e8\u5206\u7ed3\u8d26"
            payment_allocations.append((order, applied))
            remaining = round(remaining - applied, 2)

        customer.current_debt = round((customer.current_debt or 0) - amount, 2)
        if customer.current_debt < 0:
            raise ValueError("Customer receivable balance cannot be negative")
        ledgers = []
        for order, applied in payment_allocations:
            ledger = ReceivableLedger(
                customer_id=customer.id,
                sales_order_id=order.id,
                amount=-applied,
                reason="payment",
                reference_no=order.order_no,
                remark=remark,
            )
            self.db.add(ledger)
            ledgers.append(ledger)
        return ledgers
