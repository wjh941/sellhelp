"""
客户管理 API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.all_models import Customer, SalesOrder
from ..schemas.all_schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse, MessageResponse
)
from datetime import datetime
from ..services.receivable_service import ReceivableService

router = APIRouter(prefix="/api/customers", tags=["客户管理"])


@router.get("", response_model=List[CustomerResponse])
def list_customers(
    keyword: Optional[str] = None,
    customer_type: Optional[str] = None,
    is_vip: Optional[bool] = None,
    has_debt: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取客户列表"""
    query = db.query(Customer)
    if keyword:
        query = query.filter(Customer.name.contains(keyword))
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)
    if is_vip is not None:
        query = query.filter(Customer.is_vip == is_vip)
    if has_debt:
        query = query.filter(Customer.current_debt > 0)
    return query.order_by(Customer.id.desc()).all()


@router.post("", response_model=CustomerResponse)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    """创建客户"""
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """获取客户详情"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    """更新客户"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    for key, value in data.model_dump().items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", response_model=MessageResponse)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """删除客户"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if customer.sales_orders:
        raise HTTPException(status_code=400, detail="该客户有销售记录，无法删除")
    if customer.receivable_ledgers:
        raise HTTPException(status_code=400, detail="该客户有应收账款历史，无法删除")
    if customer.current_debt > 0:
        raise HTTPException(status_code=400, detail="客户还有欠款，无法删除")
    db.delete(customer)
    db.commit()
    return MessageResponse(message="删除成功")


@router.get("/{customer_id}/sales", response_model=List[dict])
def get_customer_sales(
    customer_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取客户的销售记录"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    query = db.query(SalesOrder).filter(SalesOrder.customer_id == customer_id)
    if start_date:
        query = query.filter(SalesOrder.sale_date >= start_date)
    if end_date:
        query = query.filter(SalesOrder.sale_date <= end_date)

    orders = query.order_by(SalesOrder.sale_date.desc()).all()
    return [{
        "order_no": o.order_no,
        "sale_date": str(o.sale_date),
        "total_amount": o.total_amount,
        "final_amount": o.final_amount,
        "payment_type": o.payment_type,
        "status": o.status,
        "items_count": len(o.items)
    } for o in orders]


@router.post("/{customer_id}/pay", response_model=CustomerResponse)
def pay_customer_debt(
    customer_id: int,
    amount: float = 0,
    db: Session = Depends(get_db)
):
    """客户还款"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="还款金额必须大于0")
    if amount > customer.current_debt:
        raise HTTPException(status_code=400, detail=f"还款金额超过欠款，当前欠款¥{customer.current_debt:.2f}")

    try:
        ReceivableService(db).apply_payment(customer, amount, None, "customer payment")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(customer)
    return customer
