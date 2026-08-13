"""
销售单 API路由 - 含FIFO先进先出出库核心逻辑
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from ..database import get_db
from ..models.all_models import (
    SalesOrder, SalesOrderItem, BatchOutbound, Customer, Product, ProductBatch
)
from ..schemas.all_schemas import (
    SalesOrderCreate, SalesOrderResponse, SalesOrderPay, SalesItemResponse, MessageResponse
)
from ..services.inventory_service import InventoryService
from ..services.receivable_service import ReceivableService

router = APIRouter(prefix="/api/sales-orders", tags=["销售管理"])


def _generate_order_no() -> str:
    """生成销售单号"""
    return f"SO{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"


def _get_price_for_customer(product: Product, customer_type: str, is_vip: bool) -> float:
    """根据客户类型获取对应价格"""
    if is_vip or customer_type == "VIP":
        return product.vip_price
    elif customer_type in ["食堂", "工厂"]:
        return product.wholesale_price
    elif customer_type == "小店":
        return product.wholesale_price
    elif customer_type == "散户":
        return product.retail_price
    else:
        return product.wholesale_price


def _get_price_level_name(customer_type: str, is_vip: bool) -> str:
    """获取价格档次名称"""
    if is_vip or customer_type == "VIP":
        return "大客户价"
    elif customer_type in ["食堂", "工厂"]:
        return "批发价"
    elif customer_type == "小店":
        return "批发价"
    else:
        return "零售价"


@router.get("", response_model=List[SalesOrderResponse])
def list_sales_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    payment_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取销售单列表"""
    query = db.query(SalesOrder)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if start_date:
        query = query.filter(SalesOrder.sale_date >= start_date)
    if end_date:
        query = query.filter(SalesOrder.sale_date <= end_date)
    if status:
        query = query.filter(SalesOrder.status == status)
    if payment_type:
        query = query.filter(SalesOrder.payment_type == payment_type)

    orders = query.order_by(SalesOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for order in orders:
        result = SalesOrderResponse.model_validate(order)
        result.customer_name = order.customer.name if order.customer else None
        results.append(result)

    return results


@router.get("/{order_id}", response_model=SalesOrderResponse)
def get_sales_order(order_id: int, db: Session = Depends(get_db)):
    """获取销售单详情"""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")

    result = SalesOrderResponse.model_validate(order)
    result.customer_name = order.customer.name if order.customer else None

    # 补充明细信息
    for item in result.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            item.product_name = product.name

        # 查询该明细使用的批次
        outbounds = db.query(BatchOutbound).filter(BatchOutbound.sales_item_id == item.id).all()
        batches_used = []
        for ob in outbounds:
            batch = db.query(ProductBatch).filter(ProductBatch.id == ob.batch_id).first()
            if batch:
                batches_used.append({
                    "batch_id": batch.id,
                    "batch_no": batch.batch_no,
                    "quantity": ob.outbound_quantity,
                    "unit_cost": ob.unit_cost
                })
        item.batches_used = batches_used

    return result


@router.post("", response_model=SalesOrderResponse)
def create_sales_order(data: SalesOrderCreate, db: Session = Depends(get_db)):
    """创建销售单（含FIFO出库核心逻辑）"""
    # 验证客户
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")

    inventory_service = InventoryService(db)
    items_data = []
    total_amount = 0
    all_profit = 0

    # 处理每个商品
    for item_data in data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"商品ID {item_data.product_id} 不存在")

        # FIFO分配库存
        try:
            avg_cost, batch_details = inventory_service.allocate_stock_for_sale(
                item_data.product_id, item_data.quantity
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"{product.name}: {str(e)}")

        # 如果前端没传价格，自动匹配
        unit_price = item_data.unit_price
        if unit_price <= 0:
            unit_price = _get_price_for_customer(product, customer.customer_type, customer.is_vip)

        amount = unit_price * item_data.quantity
        profit = amount - (avg_cost * item_data.quantity)

        items_data.append({
            "product": product,
            "quantity": item_data.quantity,
            "unit_price": unit_price,
            "cost_price": avg_cost,
            "amount": amount,
            "profit": profit,
            "remark": item_data.remark,
            "batch_details": batch_details
        })
        total_amount += amount
        all_profit += profit

    # 根据支付类型确定金额
    payment_type = data.payment_type or "现结"
    if payment_type == "现结":
        paid_amount = total_amount
        debt_amount = 0
    elif payment_type == "赊账":
        paid_amount = 0
        debt_amount = total_amount
    elif payment_type == "部分结账":
        paid_amount = data.paid_amount or 0
        if paid_amount < 0 or paid_amount > total_amount:
            raise HTTPException(status_code=400, detail="付款金额无效")
        debt_amount = total_amount - paid_amount
    else:
        paid_amount = total_amount
        debt_amount = 0

    # 检查客户信用额度
    if debt_amount > 0 and customer.credit_limit > 0:
        if customer.current_debt + debt_amount > customer.credit_limit:
            raise HTTPException(status_code=400, detail=f"客户欠款将超过额度！当前欠款¥{customer.current_debt:.2f}，额度¥{customer.credit_limit:.2f}")

    # 创建销售单
    order = SalesOrder(
        order_no=_generate_order_no(),
        customer_id=data.customer_id,
        sale_date=data.sale_date or datetime.now(),
        total_amount=total_amount,
        discount_amount=0,
        final_amount=total_amount,
        payment_type=payment_type,
        paid_amount=paid_amount,
        debt_amount=debt_amount,
        customer_type_snapshot=customer.customer_type,
        price_level_used=_get_price_level_name(customer.customer_type, customer.is_vip),
        operator=data.operator,
        remark=data.remark
    )
    db.add(order)
    db.flush()

    # 创建明细并执行FIFO出库
    for item_data in items_data:
        sales_item = SalesOrderItem(
            sales_order_id=order.id,
            product_id=item_data["product"].id,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            cost_price=item_data["cost_price"],
            amount=item_data["amount"],
            profit=item_data["profit"],
            remark=item_data["remark"]
        )
        db.add(sales_item)
        db.flush()

        # 执行FIFO出库（扣减批次库存）
        inventory_service.confirm_outbound(
            sales_item_id=sales_item.id,
            product_id=item_data["product"].id,
            quantity=item_data["quantity"]
        )

    # Automatically update customer consumption and receivable balance.
    customer.total_consumption += total_amount
    ReceivableService(db).apply_order_balance_change(order, 0, "sales_order_created", order.order_no)

    db.commit()
    db.refresh(order)

    # 返回结果
    result = SalesOrderResponse.model_validate(order)
    result.customer_name = customer.name
    return result


@router.post("/{order_id}/pay", response_model=SalesOrderResponse)
def update_payment(order_id: int, pay_data: SalesOrderPay, db: Session = Depends(get_db)):
    """更新销售单付款状态"""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")

    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()

    old_debt = order.debt_amount
    if pay_data.payment_type == "现结":
        new_debt = 0
    elif pay_data.payment_type == "赊账":
        new_debt = order.final_amount
    else:
        paid = pay_data.paid_amount or 0
        if paid < 0 or paid > order.final_amount:
            raise HTTPException(status_code=400, detail="付款金额无效")
        new_debt = order.final_amount - paid

    try:
        ReceivableService(db).validate_order_balance_change(order, old_debt, new_debt)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    if new_debt > 0 and customer and customer.credit_limit > 0:
        resulting_debt = round(customer.current_debt - old_debt + new_debt, 2)
        if resulting_debt > customer.credit_limit:
            raise HTTPException(status_code=400, detail=f"客户欠款将超过额度！变更后欠款¥{resulting_debt:.2f}，额度¥{customer.credit_limit:.2f}")

    if pay_data.payment_type == "现结":
        order.payment_type = "现结"
        order.paid_amount = order.final_amount
        order.debt_amount = 0

    elif pay_data.payment_type == "赊账":
        order.payment_type = "赊账"
        order.paid_amount = 0
        order.debt_amount = order.final_amount

    elif pay_data.payment_type == "部分结账":
        paid = pay_data.paid_amount or 0
        order.payment_type = "部分结账"
        order.paid_amount = paid
        order.debt_amount = order.final_amount - paid
    try:
        ReceivableService(db).apply_order_balance_change(order, old_debt, "sales_payment_changed", order.order_no)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(order)

    result = SalesOrderResponse.model_validate(order)
    result.customer_name = customer.name if customer else None
    return result


@router.post("/{order_id}/complete-payment", response_model=SalesOrderResponse)
def complete_payment(order_id: int, db: Session = Depends(get_db)):
    """完成付款（将赊账改为已结清）"""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")

    if order.debt_amount <= 0:
        raise HTTPException(status_code=400, detail="该订单无欠款")

    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()

    old_debt = order.debt_amount
    try:
        ReceivableService(db).validate_order_balance_change(order, old_debt, 0)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    order.payment_type = "现结"
    order.paid_amount = order.final_amount
    order.debt_amount = 0
    order.status = "已完成"

    try:
        ReceivableService(db).apply_order_balance_change(order, old_debt, "sales_payment_completed", order.order_no)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(order)

    result = SalesOrderResponse.model_validate(order)
    result.customer_name = customer.name if customer else None
    return result


@router.delete("/{order_id}", response_model=MessageResponse)
def delete_sales_order(order_id: int, db: Session = Depends(get_db)):
    """删除销售单（冲回FIFO库存）"""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")

    if order.status == "已退货":
        raise HTTPException(status_code=400, detail="已退货订单无法删除")

    inventory_service = InventoryService(db)

    # 冲回所有出库
    for item in order.items:
        inventory_service.reverse_outbound(item.id)

    # 减少客户累计消费
    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
    if customer:
        customer.total_consumption = max(0, customer.total_consumption - order.final_amount)
        old_debt = order.debt_amount
        try:
            ReceivableService(db).validate_order_balance_change(order, old_debt, 0)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc))
        order.debt_amount = 0
        try:
            ReceivableService(db).apply_order_balance_change(order, old_debt, "sales_order_deleted", order.order_no)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc))

    # 删除订单明细
    for item in order.items:
        db.delete(item)

    db.delete(order)
    db.commit()
    return MessageResponse(message="删除成功，库存已冲回")
