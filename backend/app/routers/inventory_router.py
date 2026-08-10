"""
库存管理 API路由 - 库存查询、预警
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from ..database import get_db
from ..models.all_models import Product, ProductBatch
from ..schemas.all_schemas import StockInfo, ExpiryWarning, MessageResponse
from ..services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["库存管理"])


@router.get("/stock-summary", response_model=dict)
def get_stock_summary(db: Session = Depends(get_db)):
    """获取库存汇总"""
    inventory_service = InventoryService(db)
    return inventory_service.get_stock_value_summary()


@router.get("/all-stock", response_model=List[dict])
def get_all_stock(
    include_empty: bool = Query(False),
    db: Session = Depends(get_db)
):
    """获取所有商品库存"""
    inventory_service = InventoryService(db)
    return inventory_service.get_all_products_stock(include_empty=include_empty)


@router.get("/product/{product_id}", response_model=StockInfo)
def get_product_stock(product_id: int, db: Session = Depends(get_db)):
    """获取单个商品库存详情（含批次）"""
    inventory_service = InventoryService(db)
    stock_info = inventory_service.get_stock_info(product_id)
    if not stock_info:
        raise HTTPException(status_code=404, detail="商品不存在")
    return stock_info


@router.get("/expiry-warnings", response_model=List[ExpiryWarning])
def get_expiry_warnings(
    warning_days: int = Query(30, ge=1, le=365),
    level: Optional[str] = Query(None, description="warning/critical/expired"),
    db: Session = Depends(get_db)
):
    """获取临期预警列表"""
    inventory_service = InventoryService(db)
    warnings = inventory_service.get_expiry_warnings(warning_days)

    if level:
        warnings = [w for w in warnings if w["warning_level"] == level]

    return warnings


@router.get("/low-stock", response_model=List[dict])
def get_low_stock_alerts(db: Session = Depends(get_db)):
    """获取低库存预警（低于安全库存）"""
    products = db.query(Product).filter(Product.is_active == True).all()
    inventory_service = InventoryService(db)
    alerts = []

    for product in products:
        stock = inventory_service.get_product_total_stock(product.id)
        if stock <= product.safe_stock:
            alerts.append({
                "product_id": product.id,
                "product_name": product.name,
                "current_stock": stock,
                "safe_stock": product.safe_stock,
                "category": product.category.name if product.category else None
            })

    return sorted(alerts, key=lambda x: x["current_stock"])


@router.get("/categories-stock", response_model=dict)
def get_categories_stock(db: Session = Depends(get_db)):
    """按分类统计库存"""
    from ..models.all_models import Category
    categories = db.query(Category).all()
    inventory_service = InventoryService(db)

    result = {}
    for cat in categories:
        products = db.query(Product).filter(
            Product.category_id == cat.id,
            Product.is_active == True
        ).all()

        cat_stock = 0
        cat_value = 0
        for p in products:
            batches = inventory_service.get_product_batches(p.id)
            stock = sum(b.remaining_quantity for b in batches)
            value = sum(b.remaining_quantity * b.purchase_price for b in batches)
            cat_stock += stock
            cat_value += value

        result[cat.name] = {
            "product_count": len(products),
            "total_stock": round(cat_stock, 2),
            "total_value": round(cat_value, 2)
        }

    return result
