"""
财务/回款管理 API路由 - 客户欠款、还款、对账
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models.all_models import Customer, SalesOrder, SalesOrderItem
from ..schemas.all_schemas import MessageResponse
from ..services.receivable_service import ReceivableService

router = APIRouter(prefix="/api/finance", tags=["财务管理"])


@router.get("/debt-customers", response_model=List[dict])
def list_debt_customers(
    min_debt: float = Query(0, ge=0),
    customer_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取欠款客户列表"""
    query = db.query(Customer).filter(Customer.current_debt > min_debt)
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)

    customers = query.order_by(Customer.current_debt.desc()).all()

    result = []
    for c in customers:
        # 获取欠款明细
        debt_orders = db.query(SalesOrder).filter(
            SalesOrder.customer_id == c.id,
            SalesOrder.debt_amount > 0
        ).order_by(SalesOrder.sale_date.desc()).all()

        result.append({
            "customer_id": c.id,
            "name": c.name,
            "type": c.customer_type,
            "is_vip": c.is_vip,
            "contact_person": c.contact_person,
            "phone": c.phone,
            "credit_limit": c.credit_limit,
            "current_debt": c.current_debt,
            "total_consumption": c.total_consumption,
            "debt_order_count": len(debt_orders),
            "last_debt_date": str(debt_orders[0].sale_date) if debt_orders else None,
            "usage_rate": round(c.current_debt / c.credit_limit * 100, 1) if c.credit_limit > 0 else 0
        })

    return result


@router.get("/customer/{customer_id}/debts", response_model=dict)
def get_customer_debts(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """获取客户欠款详情"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 欠款订单
    debt_orders = db.query(SalesOrder).filter(
        SalesOrder.customer_id == customer_id,
        SalesOrder.debt_amount > 0
    ).order_by(SalesOrder.sale_date.desc()).all()

    # 已结清订单
    paid_orders = db.query(SalesOrder).filter(
        SalesOrder.customer_id == customer_id,
        SalesOrder.debt_amount == 0
    ).order_by(SalesOrder.sale_date.desc()).limit(20).all()

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "type": customer.customer_type,
            "credit_limit": customer.credit_limit,
            "current_debt": customer.current_debt,
            "total_consumption": customer.total_consumption
        },
        "debt_orders": [{
            "order_no": o.order_no,
            "date": str(o.sale_date),
            "total_amount": o.total_amount,
            "paid_amount": o.paid_amount,
            "debt_amount": o.debt_amount,
            "payment_type": o.payment_type,
            "items": [{
                "product_name": i.product.name if i.product else "未知",
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "amount": i.amount
            } for i in o.items]
        } for o in debt_orders],
        "paid_orders_count": len(paid_orders)
    }


@router.post("/customer/{customer_id}/repay", response_model=dict)
def repay_customer_debt(
    customer_id: int,
    amount: float = 0,
    remark: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """客户还款（支持部分还款）"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="还款金额必须大于0")
    if amount > customer.current_debt:
        raise HTTPException(status_code=400, detail=f"还款金额超过欠款，当前欠款¥{customer.current_debt:.2f}")

    try:
        ReceivableService(db).apply_payment(customer, amount, None, remark)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(customer)

    return {
        "message": "还款成功",
        "customer": customer.name,
        "amount": amount,
        "remaining_debt": customer.current_debt,
        "remark": remark
    }


@router.get("/customer/{customer_id}/statement", response_model=dict)
def get_customer_statement(
    customer_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取客户对账单"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    query = db.query(SalesOrder).filter(SalesOrder.customer_id == customer_id)
    if start_date:
        query = query.filter(SalesOrder.sale_date >= start_date)
    if end_date:
        query = query.filter(SalesOrder.sale_date <= end_date)

    orders = query.order_by(SalesOrder.sale_date.asc()).all()

    # 汇总
    total_amount = sum(o.total_amount for o in orders)
    total_paid = sum(o.paid_amount for o in orders)
    total_debt = sum(o.debt_amount for o in orders)
    total_profit = 0
    for o in orders:
        for i in o.items:
            total_profit += i.profit

    # 按日汇总
    daily_summary = {}
    for o in orders:
        day = str(o.sale_date.date()) if hasattr(o.sale_date, 'date') else str(o.sale_date)[:10]
        if day not in daily_summary:
            daily_summary[day] = {"count": 0, "amount": 0, "paid": 0, "debt": 0}
        daily_summary[day]["count"] += 1
        daily_summary[day]["amount"] += o.total_amount
        daily_summary[day]["paid"] += o.paid_amount
        daily_summary[day]["debt"] += o.debt_amount

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "type": customer.customer_type,
            "phone": customer.phone,
            "address": customer.address,
            "credit_limit": customer.credit_limit,
            "current_debt": customer.current_debt,
            "total_consumption": customer.total_consumption
        },
        "period": {
            "start": start_date or "全部",
            "end": end_date or "全部"
        },
        "summary": {
            "order_count": len(orders),
            "total_amount": round(total_amount, 2),
            "total_paid": round(total_paid, 2),
            "total_debt": round(total_debt, 2),
            "total_profit": round(total_profit, 2)
        },
        "daily_summary": daily_summary,
        "orders": [{
            "order_no": o.order_no,
            "date": str(o.sale_date),
            "total_amount": o.total_amount,
            "paid_amount": o.paid_amount,
            "debt_amount": o.debt_amount,
            "payment_type": o.payment_type,
            "status": o.status,
            "item_count": len(o.items),
            "items": [{
                "product_name": i.product.name if i.product else "未知",
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "amount": i.amount,
                "profit": i.profit
            } for i in o.items]
        } for o in orders]
    }


@router.get("/overdue-customers", response_model=List[dict])
def get_overdue_customers(
    db: Session = Depends(get_db)
):
    """获取超期欠款客户（超过30天未还款）"""
    thirty_days_ago = datetime.now() - timedelta(days=30)

    customers = db.query(Customer).filter(Customer.current_debt > 0).all()
    result = []

    for c in customers:
        # 查找最早的欠款订单
        oldest_debt = db.query(SalesOrder).filter(
            SalesOrder.customer_id == c.id,
            SalesOrder.debt_amount > 0
        ).order_by(SalesOrder.sale_date.asc()).first()

        if oldest_debt and oldest_debt.sale_date < thirty_days_ago:
            days_overdue = (datetime.now() - oldest_debt.sale_date).days
            result.append({
                "customer_id": c.id,
                "name": c.name,
                "current_debt": c.current_debt,
                "oldest_debt_date": str(oldest_debt.sale_date),
                "days_overdue": days_overdue,
                "debt_count": db.query(SalesOrder).filter(
                    SalesOrder.customer_id == c.id,
                    SalesOrder.debt_amount > 0
                ).count()
            })

    return sorted(result, key=lambda x: x["days_overdue"], reverse=True)


@router.post("/batch-repay", response_model=dict)
def batch_repay(
    data: dict,
    db: Session = Depends(get_db)
):
    """批量还款"""
    results = []
    total_amount = 0

    for item in data.get("items", []):
        customer_id = item.get("customer_id")
        amount = item.get("amount", 0)

        if not customer_id or amount <= 0:
            continue

        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            results.append({"customer_id": customer_id, "status": "error", "message": "客户不存在"})
            continue

        actual_amount = min(amount, customer.current_debt)
        if actual_amount <= 0:
            continue
        try:
            with db.begin_nested():
                ReceivableService(db).apply_payment(customer, actual_amount, None, "batch repayment")
        except ValueError as exc:
            results.append({"customer_id": customer_id, "status": "error", "message": str(exc)})
            continue

        results.append({
            "customer_id": customer_id,
            "name": customer.name,
            "amount": actual_amount,
            "remaining_debt": customer.current_debt,
            "status": "success"
        })
        total_amount += actual_amount

    db.commit()

    return {
        "message": f"批量还款完成",
        "total_repaid": round(total_amount, 2),
        "details": results
    }
