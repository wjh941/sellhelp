"""
退货与盘点 API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import uuid

from ..database import get_db
from ..models.all_models import (
    ReturnOrder, StockTake, Product, ProductBatch, SalesOrder, SalesOrderItem
)
from ..schemas.all_schemas import (
    ReturnOrderCreate, ReturnOrderResponse,
    StockTakeItemCreate, StockTakeResponse, MessageResponse
)
from ..services.inventory_service import InventoryService

router = APIRouter(prefix="/api", tags=["退货盘点"])


def _generate_return_no() -> str:
    return f"RT{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"


def _generate_stocktake_no() -> str:
    return f"ST{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"


# ========== 退货管理 ==========

@router.get("/returns", response_model=List[ReturnOrderResponse])
def list_returns(
    return_type: Optional[str] = Query(None),
    partner_id: Optional[int] = Query(None),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取退货单列表"""
    query = db.query(ReturnOrder)
    if return_type:
        query = query.filter(ReturnOrder.return_type == return_type)
    if partner_id:
        query = query.filter(ReturnOrder.partner_id == partner_id)
    if start_date:
        query = query.filter(ReturnOrder.created_at >= start_date)
    if end_date:
        query = query.filter(ReturnOrder.created_at <= end_date)

    returns = query.order_by(ReturnOrder.id.desc()).all()

    results = []
    for r in returns:
        result = ReturnOrderResponse.model_validate(r)
        product = db.query(Product).filter(Product.id == r.product_id).first()
        result.product_name = product.name if product else None
        if r.batch_id:
            batch = db.query(ProductBatch).filter(ProductBatch.id == r.batch_id).first()
            result.batch_no = batch.batch_no if batch else None
        results.append(result)

    return results


@router.post("/returns", response_model=ReturnOrderResponse)
def create_return(data: ReturnOrderCreate, db: Session = Depends(get_db)):
    """创建退货单"""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=400, detail="商品不存在")

    inventory_service = InventoryService(db)
    # 客户退货：先检查是否有原销售单
    selected_batch_id = data.batch_id
    supplier_allocations = []
    if data.return_type == "客户退货" and data.related_order_no:
        sale_order = db.query(SalesOrder).filter(SalesOrder.order_no == data.related_order_no).first()
        if sale_order:
            if data.batch_id:
                inventory_service.return_to_batch(data.batch_id, data.quantity)
                selected_batch_id = data.batch_id
            else:
                # 如果未指定批次，创建新批次记录
                new_batch = ProductBatch(
                    product_id=product.id,
                    batch_no=f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    purchase_price=product.purchase_price or 0,
                    total_quantity=data.quantity,
                    remaining_quantity=data.quantity,
                    remark="客户退货入库"
                )
                db.add(new_batch)
                db.flush()
                selected_batch_id = new_batch.id
        else:
            # 无原单，直接入库
            new_batch = ProductBatch(
                product_id=product.id,
                batch_no=f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                purchase_price=product.purchase_price or 0,
                total_quantity=data.quantity,
                remaining_quantity=data.quantity,
                remark="客户退货入库"
            )
            db.add(new_batch)
            db.flush()
            selected_batch_id = new_batch.id

    elif data.return_type == "供应商退货":
        # 供应商退货：从指定批次扣减
        if data.batch_id:
            batch = db.query(ProductBatch).filter(ProductBatch.id == data.batch_id).first()
            if not batch:
                raise HTTPException(status_code=400, detail="批次不存在")
            if batch.expiry_date and batch.expiry_date <= date.today():
                raise HTTPException(status_code=400, detail="批次已过期，无法退给供应商")
            if batch.remaining_quantity < data.quantity:
                raise HTTPException(status_code=400, detail="批次库存不足")
            batch.remaining_quantity -= data.quantity
            batch.total_quantity -= data.quantity
            selected_batch_id = batch.id
        else:
            # 从可销售批次按 FIFO 扣减
            try:
                supplier_allocations = inventory_service.find_fifo_batches(product.id, data.quantity)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            for batch, allocated_quantity in supplier_allocations:
                batch.remaining_quantity -= allocated_quantity
                batch.total_quantity -= allocated_quantity

    return_order = ReturnOrder(
        order_no=_generate_return_no(),
        return_type=data.return_type,
        related_order_no=data.related_order_no,
        partner_id=data.partner_id,
        product_id=data.product_id,
        batch_id=data.batch_id,
        quantity=data.quantity,
        refund_amount=data.refund_amount,
        reason=data.reason,
        operator=data.operator
    )
    db.add(return_order)
    db.flush()
    if data.return_type == "客户退货":
        inventory_service = InventoryService(db)
        inventory_service.record_movement(
            product_id=product.id,
            batch_id=selected_batch_id,
            direction="inbound",
            quantity=data.quantity,
            reason="customer_return",
            reference_no=return_order.order_no,
            return_order_id=return_order.id,
            operator=data.operator,
            remark=data.reason,
        )
    else:
        if not supplier_allocations:
            supplier_allocations = [(db.get(ProductBatch, selected_batch_id), data.quantity)]
        for batch, allocated_quantity in supplier_allocations:
            inventory_service.record_movement(
                product_id=product.id,
                batch_id=batch.id,
                direction="outbound",
                quantity=allocated_quantity,
                reason="supplier_return",
                reference_no=return_order.order_no,
                return_order_id=return_order.id,
                operator=data.operator,
                remark=data.reason,
            )
    db.commit()
    db.refresh(return_order)

    result = ReturnOrderResponse.model_validate(return_order)
    result.product_name = product.name
    return result


# ========== 盘点管理 ==========

@router.get("/stock-takes", response_model=List[StockTakeResponse])
def list_stock_takes(
    take_date: Optional[str] = None,
    product_id: Optional[int] = None,
    confirmed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取盘点记录列表"""
    query = db.query(StockTake)
    if take_date:
        query = query.filter(StockTake.take_date == take_date)
    if product_id:
        query = query.filter(StockTake.product_id == product_id)
    if confirmed is not None:
        query = query.filter(StockTake.confirmed == confirmed)

    records = query.order_by(StockTake.id.desc()).all()

    results = []
    for r in records:
        result = StockTakeResponse.model_validate(r)
        product = db.query(Product).filter(Product.id == r.product_id).first()
        result.product_name = product.name if product else None
        if r.batch_id:
            batch = db.query(ProductBatch).filter(ProductBatch.id == r.batch_id).first()
            result.batch_no = batch.batch_no if batch else None
        results.append(result)

    return results


@router.post("/stock-takes/prepare", response_model=List[dict])
def prepare_stock_take(
    category_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """准备盘点清单（获取系统库存数据）"""
    query = db.query(Product).filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if product_id:
        query = query.filter(Product.id == product_id)

    products = query.all()
    inventory_service = InventoryService(db)

    items = []
    for product in products:
        batches = inventory_service.get_product_batches(product.id)
        if batches:
            for batch in batches:
                items.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "batch_id": batch.id,
                    "batch_no": batch.batch_no,
                    "system_quantity": batch.remaining_quantity,
                    "unit_price": batch.purchase_price,
                    "expiry_date": str(batch.expiry_date) if batch.expiry_date else None
                })
        # 无库存商品也显示
        if not batches:
            total_stock = inventory_service.get_product_total_stock(product.id)
            items.append({
                "product_id": product.id,
                "product_name": product.name,
                "batch_id": None,
                "batch_no": "无批次",
                "system_quantity": total_stock,
                "unit_price": product.purchase_price or 0,
                "expiry_date": None
            })

    return items


@router.post("/stock-takes/confirm", response_model=List[StockTakeResponse])
def confirm_stock_take(items: List[StockTakeItemCreate], db: Session = Depends(get_db)):
    """确认盘点结果"""
    today = date.today()
    inventory_service = InventoryService(db)
    results = []

    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            continue

        if item.batch_id:
            batch = db.query(ProductBatch).filter(ProductBatch.id == item.batch_id).first()
            if not batch:
                continue
            system_qty = batch.remaining_quantity
        else:
            system_qty = inventory_service.get_product_total_stock(item.product_id)

        diff = item.actual_quantity - system_qty
        diff_amount = diff * (batch.purchase_price if item.batch_id else (product.purchase_price or 0))

        stocktake = StockTake(
            take_date=today,
            product_id=item.product_id,
            batch_id=item.batch_id,
            system_quantity=system_qty,
            actual_quantity=item.actual_quantity,
            diff_quantity=diff,
            diff_amount=round(diff_amount, 2),
            reason=item.reason,
            confirmed=True
        )
        db.add(stocktake)
        db.flush()

        # 如果有差异且已确认，调整库存
        if item.batch_id and diff != 0:
            batch = db.query(ProductBatch).filter(ProductBatch.id == item.batch_id).first()
            if batch:
                batch.remaining_quantity = max(0, batch.remaining_quantity + diff)
                InventoryService(db).record_movement(
                    product_id=item.product_id,
                    batch_id=batch.id,
                    direction="inbound" if diff > 0 else "outbound",
                    quantity=abs(diff),
                    reason="stocktake_adjustment",
                    reference_no=f"stocktake:{stocktake.id}",
                    stock_take_id=stocktake.id,
                    operator=item.operator if hasattr(item, "operator") else None,
                    remark=item.reason,
                )

        results.append(StockTakeResponse.model_validate(stocktake))

    db.commit()
    return results
