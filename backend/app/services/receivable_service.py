from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..models.all_models import Customer, ReceivableLedger, SalesOrder


class ReceivableService:
    def __init__(self, db: Session):
        self.db = db

    def apply_order_balance_change(self, order: SalesOrder, old_debt: float, reason: str, reference_no: Optional[str]):
        delta = round((order.debt_amount or 0) - (old_debt or 0), 2)
        if delta == 0:
            return None

        customer = order.customer or self.db.get(Customer, order.customer_id)
        if not customer:
            raise ValueError("Customer does not exist")

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
