"""
入库单 API路由 - 批次入库核心
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import uuid

from ..database import get_db
from ..models.all_models import (
    PurchaseOrder, PurchaseOrderItem, ProductBatch, Product, Supplier
)
from ..schemas.all_schemas import (
    PurchaseOrderCreate, PurchaseOrderResponse, PurchaseItemResponse, MessageResponse
)
from ..services.inventory_service import InventoryService

router = APIRouter(prefix="/api/purchase-orders", tags=["入库管理"])


def _generate_order_no() -> str:
    """生成入库单号"""
    return f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"


@router.get("", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取入库单列表"""
    query = db.query(PurchaseOrder)
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    if start_date:
        query = query.filter(PurchaseOrder.purchase_date >= start_date)
    if end_date:
        query = query.filter(PurchaseOrder.purchase_date <= end_date)

    total = query.count()
    orders = query.order_by(PurchaseOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for order in orders:
        result = PurchaseOrderResponse.model_validate(order)
        result.supplier_name = order.supplier.name if order.supplier else None
        results.append(result)

    return results


@router.get("/{order_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(order_id: int, db: Session = Depends(get_db)):
    """获取入库单详情"""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="入库单不存在")

    result = PurchaseOrderResponse.model_validate(order)
    result.supplier_name = order.supplier.name if order.supplier else None

    # 补充明细的产品名称
    for item in result.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            item.product_name = product.name

    return result


@router.post("", response_model=PurchaseOrderResponse)
def create_purchase_order(data: PurchaseOrderCreate, db: Session = Depends(get_db)):
    """创建入库单（含批次生成）"""
    # 验证供应商
    supplier = db.query(Supplier).filter(Supplier.id == data.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=400, detail="供应商不存在")

    # 创建入库单
    order = PurchaseOrder(
        order_no=_generate_order_no(),
        supplier_id=data.supplier_id,
        purchase_date=data.purchase_date or datetime.now(),
        operator=data.operator,
        remark=data.remark
    )

    total_amount = 0
    inventory_service = InventoryService(db)

    # 处理每个入库明细
    for item_data in data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"商品ID {item_data.product_id} 不存在")

        amount = item_data.quantity * item_data.unit_price
        total_amount += amount

        # 创建入库明细
        order_item = PurchaseOrderItem(
            purchase_order=order,
            product_id=item_data.product_id,
            batch_no=item_data.batch_no,
            production_date=item_data.production_date,
            expiry_date=item_data.expiry_date,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            amount=amount,
            remark=item_data.remark
        )
        db.add(order_item)
        db.flush()

        # 创建批次记录
        batch = ProductBatch(
            product_id=item_data.product_id,
            purchase_item_id=order_item.id,
            batch_no=item_data.batch_no,
            production_date=item_data.production_date,
            expiry_date=item_data.expiry_date,
            purchase_price=item_data.unit_price,
            total_quantity=item_data.quantity,
            remaining_quantity=item_data.quantity
        )
        db.add(batch)

        # 更新商品参考进价
        product.purchase_price = item_data.unit_price

    order.total_amount = total_amount
    db.add(order)
    db.commit()
    db.refresh(order)

    # 返回结果
    result = PurchaseOrderResponse.model_validate(order)
    result.supplier_name = supplier.name
    return result


@router.delete("/{order_id}", response_model=MessageResponse)
def delete_purchase_order(order_id: int, db: Session = Depends(get_db)):
    """删除入库单（同时回滚批次库存）"""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="入库单不存在")

    # 检查是否已有销售出库
    for item in order.items:
        batch = db.query(ProductBatch).filter(ProductBatch.purchase_item_id == item.id).first()
        if batch and batch.remaining_quantity < batch.total_quantity:
            raise HTTPException(status_code=400, detail="该入库单已有部分销售出库，无法删除")

    # 回滚批次
    for item in order.items:
        batch = db.query(ProductBatch).filter(ProductBatch.purchase_item_id == item.id).first()
        if batch:
            db.delete(batch)

    db.delete(order)
    db.commit()
    return MessageResponse(message="删除成功")
