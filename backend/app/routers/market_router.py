"""
市场行情与AI定价 API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from ..database import get_db
from ..models.all_models import MarketPrice, Product, PricingReference
from ..schemas.all_schemas import (
    MarketPriceCreate, MarketPriceResponse,
    PricingRequest, PricingReferenceResponse, MessageResponse
)
from ..services.pricing_service import PricingService

router = APIRouter(prefix="/api", tags=["行情与定价"])


def _commit_or_rollback(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


# ========== 市场行情 ==========

@router.get("/market-prices", response_model=List[MarketPriceResponse])
def list_market_prices(
    price_type: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取行情记录列表"""
    query = db.query(MarketPrice)
    if price_type:
        query = query.filter(MarketPrice.price_type == price_type)
    if product_id:
        query = query.filter(MarketPrice.product_id == product_id)
    if start_date:
        query = query.filter(MarketPrice.record_date >= start_date)
    if end_date:
        query = query.filter(MarketPrice.record_date <= end_date)

    records = query.order_by(MarketPrice.record_date.desc()).limit(100).all()

    results = []
    for r in records:
        result = MarketPriceResponse.model_validate(r)
        product = db.query(Product).filter(Product.id == r.product_id).first() if r.product_id else None
        result.product_name = product.name if product else None
        results.append(result)

    return results


@router.post("/market-prices", response_model=MarketPriceResponse)
def create_market_price(data: MarketPriceCreate, db: Session = Depends(get_db)):
    """创建行情记录（人工录入）"""
    record = MarketPrice(
        record_date=data.record_date,
        product_id=data.product_id,
        price_type=data.price_type,
        competitor_price=data.competitor_price,
        manufacturer_price=data.manufacturer_price,
        market_trend=data.market_trend,
        content=data.content,
        remark=data.remark,
        operator=data.operator
    )
    db.add(record)
    _commit_or_rollback(db)
    db.refresh(record)

    result = MarketPriceResponse.model_validate(record)
    if data.product_id:
        product = db.query(Product).filter(Product.id == data.product_id).first()
        result.product_name = product.name if product else None
    return result


@router.put("/market-prices/{record_id}", response_model=MarketPriceResponse)
def update_market_price(record_id: int, data: MarketPriceCreate, db: Session = Depends(get_db)):
    """更新行情记录"""
    record = db.query(MarketPrice).filter(MarketPrice.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    for key, value in data.model_dump().items():
        setattr(record, key, value)
    _commit_or_rollback(db)
    db.refresh(record)

    result = MarketPriceResponse.model_validate(record)
    if record.product_id:
        product = db.query(Product).filter(Product.id == record.product_id).first()
        result.product_name = product.name if product else None
    return result


@router.delete("/market-prices/{record_id}", response_model=MessageResponse)
def delete_market_price(record_id: int, db: Session = Depends(get_db)):
    """删除行情记录"""
    record = db.query(MarketPrice).filter(MarketPrice.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    _commit_or_rollback(db)
    return MessageResponse(message="删除成功")


# ========== AI定价 ==========

@router.post("/pricing/calculate")
def calculate_pricing(data: PricingRequest, db: Session = Depends(get_db)):
    """AI定价分析（仅供参考，不自动改价）"""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    pricing_service = PricingService(db)
    result = pricing_service.calculate_pricing(data.product_id)

    return result


@router.get("/pricing/history", response_model=List[PricingReferenceResponse])
def list_pricing_history(
    product_id: Optional[int] = Query(None),
    confirmed: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """获取定价参考历史"""
    query = db.query(PricingReference)
    if product_id:
        query = query.filter(PricingReference.product_id == product_id)
    if confirmed is not None:
        query = query.filter(PricingReference.confirmed == confirmed)

    records = query.order_by(PricingReference.created_at.desc()).limit(50).all()

    results = []
    for r in records:
        result = PricingReferenceResponse.model_validate(r)
        product = db.query(Product).filter(Product.id == r.product_id).first()
        result.product_name = product.name if product else None
        results.append(result)

    return results


@router.post("/pricing/{reference_id}/confirm", response_model=MessageResponse)
def confirm_pricing(
    reference_id: int,
    operator: str = Query("admin"),
    db: Session = Depends(get_db)
):
    """人工确认定价（仅标记，不自动修改商品价格）"""
    pricing_service = PricingService(db)
    success = pricing_service.confirm_pricing(reference_id, operator)
    if not success:
        raise HTTPException(status_code=404, detail="定价参考记录不存在")
    return MessageResponse(message="定价已人工确认，需手动更新商品价格")
