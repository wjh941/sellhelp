"""
导出打印 API路由 - 送货单、入库单、销售单PDF/Excel导出
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import json
import io

from ..database import get_db
from ..models.all_models import SalesOrder, PurchaseOrder, Product, ProductBatch, Customer

router = APIRouter(prefix="/api/export", tags=["导出打印"])


@router.get("/sales/{order_id}")
def export_sales_order(order_id: int, format: str = "json", db: Session = Depends(get_db)):
    """导出销售单"""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")

    result = _build_sales_order_data(order, db)

    if format == "json":
        return result
    elif format == "print":
        return _generate_delivery_note(order, result, db)
    else:
        return result


@router.get("/purchase/{order_id}")
def export_purchase_order(order_id: int, format: str = "json", db: Session = Depends(get_db)):
    """导出入库单"""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="入库单不存在")

    result = _build_purchase_order_data(order, db)

    if format == "json":
        return result
    elif format == "print":
        return _generate_purchase_print(order, result, db)
    else:
        return result


@router.get("/customer-statement/{customer_id}")
def export_customer_statement(
    customer_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """导出客户对账单"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    query = db.query(SalesOrder).filter(SalesOrder.customer_id == customer_id)
    if start_date:
        query = query.filter(SalesOrder.sale_date >= start_date)
    if end_date:
        query = query.filter(SalesOrder.sale_date <= end_date)

    orders = query.order_by(SalesOrder.sale_date.asc()).all()

    total_amount = sum(o.total_amount for o in orders)
    total_paid = sum(o.paid_amount for o in orders)
    total_debt = sum(o.debt_amount for o in orders)

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "type": customer.customer_type,
            "phone": customer.phone,
            "address": customer.address,
            "credit_limit": customer.credit_limit,
            "current_debt": customer.current_debt
        },
        "period": {
            "start": start_date or "全部",
            "end": end_date or "全部"
        },
        "summary": {
            "order_count": len(orders),
            "total_amount": round(total_amount, 2),
            "total_paid": round(total_paid, 2),
            "total_debt": round(total_debt, 2)
        },
        "orders": [{
            "order_no": o.order_no,
            "date": str(o.sale_date),
            "total_amount": o.total_amount,
            "paid_amount": o.paid_amount,
            "debt_amount": o.debt_amount,
            "payment_type": o.payment_type,
            "items_count": len(o.items)
        } for o in orders]
    }


@router.get("/stock-report")
def export_stock_report(
    category_id: Optional[int] = None,
    include_empty: bool = False,
    db: Session = Depends(get_db)
):
    """导出库存报表"""
    from ..services.inventory_service import InventoryService
    inventory_service = InventoryService(db)

    stock_data = inventory_service.get_all_products_stock(include_empty=include_empty)

    if category_id:
        stock_data = [s for s in stock_data if s.get("category_id") == category_id]

    return {
        "export_time": datetime.now().isoformat(),
        "total_products": len(stock_data),
        "stock_value": sum(s["stock_value"] for s in stock_data),
        "items": stock_data
    }


@router.get("/expiry-report")
def export_expiry_report(
    warning_days: int = 30,
    level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """导过期预警报表"""
    from ..services.inventory_service import InventoryService
    inventory_service = InventoryService(db)

    warnings = inventory_service.get_expiry_warnings(warning_days)
    if level:
        warnings = [w for w in warnings if w["warning_level"] == level]

    return {
        "export_time": datetime.now().isoformat(),
        "warning_days": warning_days,
        "total_warnings": len(warnings),
        "critical_count": len([w for w in warnings if w["warning_level"] == "critical"]),
        "items": warnings
    }


def _build_sales_order_data(order: SalesOrder, db: Session) -> dict:
    """构建销售单数据"""
    customer = order.customer

    items_data = []
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        item_data = {
            "product_name": product.name if product else "未知商品",
            "spec": product.spec if product else "",
            "unit": product.unit if product else "",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "cost_price": item.cost_price,
            "amount": item.amount,
            "profit": item.profit
        }

        # FIFO批次信息
        outbounds = db.query(ProductBatch).filter(
            ProductBatch.id.in_([ob.batch_id for ob in item.outbound_records])
        ).all() if item.outbound_records else []

        if outbounds:
            item_data["batches"] = [{
                "batch_no": b.batch_no,
                "unit_cost": b.purchase_price
            } for b in outbounds]

        items_data.append(item_data)

    return {
        "order_no": order.order_no,
        "customer": {
            "name": customer.name if customer else "散客",
            "type": order.customer_type_snapshot,
            "price_level": order.price_level_used
        },
        "date": str(order.sale_date),
        "operator": order.operator,
        "payment": {
            "type": order.payment_type,
            "total_amount": order.total_amount,
            "paid_amount": order.paid_amount,
            "debt_amount": order.debt_amount
        },
        "items": items_data,
        "remark": order.remark,
        "status": order.status
    }


def _build_purchase_order_data(order: PurchaseOrder, db: Session) -> dict:
    """构建入库单数据"""
    supplier = order.supplier

    items_data = []
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        items_data.append({
            "product_name": product.name if product else "未知商品",
            "spec": product.spec if product else "",
            "unit": product.unit if product else "",
            "batch_no": item.batch_no,
            "production_date": str(item.production_date) if item.production_date else None,
            "expiry_date": str(item.expiry_date) if item.expiry_date else None,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "amount": item.amount
        })

    return {
        "order_no": order.order_no,
        "supplier": {
            "name": supplier.name if supplier else "",
            "contact": supplier.contact_person if supplier else "",
            "phone": supplier.phone if supplier else ""
        },
        "date": str(order.purchase_date),
        "operator": order.operator,
        "total_amount": order.total_amount,
        "items": items_data,
        "remark": order.remark
    }


def _generate_delivery_note(order: SalesOrder, data: dict, db: Session) -> dict:
    """生成送货单打印数据"""
    return {
        "print_type": "delivery_note",
        "title": "盈泰副食贸易部 · 送货单",
        "order": data,
        "print_time": datetime.now().isoformat(),
        "company": {
            "name": "盈泰副食贸易部",
            "address": "东莞高埗新联综合市场",
            "phone": ""
        }
    }


def _generate_purchase_print(order: PurchaseOrder, data: dict, db: Session) -> dict:
    """生成入库单打印数据"""
    return {
        "print_type": "purchase_order",
        "title": "盈泰副食贸易部 · 入库单",
        "order": data,
        "print_time": datetime.now().isoformat(),
        "company": {
            "name": "盈泰副食贸易部",
            "address": "东莞高埗新联综合市场",
            "phone": ""
        }
    }
