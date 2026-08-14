"""Controlled review APIs for externally discovered market quotations."""

from datetime import date, datetime
import json
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.all_models import ExternalMarketQuote, ExternalMarketSyncRun, MarketPrice, Product, SystemConfig
from ..schemas.all_schemas import (
    ExternalMarketQuoteAcceptCreate,
    ExternalMarketQuoteDismissCreate,
    ExternalMarketQuoteResponse,
    ExternalMarketSyncRunResponse,
    ExternalMarketSyncScheduleUpdate,
    ExternalMarketSyncStatusResponse,
    MarketPriceResponse,
)
from ..services.anysearch_client import AnySearchClient
from ..services.market_sync_service import DEFAULT_REGION, ExternalMarketSyncService
from ..services.market_sync_scheduler import get_market_sync_scheduler


router = APIRouter(prefix="/api", tags=["External market data"])
SYNC_TIME_KEY = "external_market_sync_time"
DEFAULT_SYNC_TIME = "02:00"


def _quote_response(quote: ExternalMarketQuote, db: Session) -> ExternalMarketQuoteResponse:
    result = ExternalMarketQuoteResponse.model_validate(quote)
    if quote.product_id:
        product = db.query(Product).filter(Product.id == quote.product_id).first()
        result.product_name = product.name if product else None
    return result


@router.get("/external-market-quotes", response_model=List[ExternalMarketQuoteResponse])
def list_external_market_quotes(
    status: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    quote_kind: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ExternalMarketQuote)
    if status:
        query = query.filter(ExternalMarketQuote.status == status)
    if product_id:
        query = query.filter(ExternalMarketQuote.product_id == product_id)
    if quote_kind:
        query = query.filter(ExternalMarketQuote.quote_kind == quote_kind)
    if region:
        query = query.filter(ExternalMarketQuote.region == region)
    return [_quote_response(quote, db) for quote in query.order_by(ExternalMarketQuote.fetched_at.desc()).all()]


@router.post("/external-market-quotes/sync", response_model=ExternalMarketSyncRunResponse)
def sync_external_market_quotes(request: Request, db: Session = Depends(get_db)):
    if request.query_params:
        raise HTTPException(status_code=422, detail="External market sync does not accept query controls")
    client = AnySearchClient()
    run = ExternalMarketSyncService(db, client).sync(trigger="manual")
    if run.status != "skipped" and not client.api_key:
        raise HTTPException(status_code=503, detail="External market search is not configured")
    return run


@router.post("/external-market-quotes/{quote_id}/accept", response_model=MarketPriceResponse)
def accept_external_market_quote(
    quote_id: int,
    data: ExternalMarketQuoteAcceptCreate,
    db: Session = Depends(get_db),
):
    quote = db.query(ExternalMarketQuote).filter(ExternalMarketQuote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="External market quote not found")
    if quote.status != "pending":
        raise HTTPException(status_code=409, detail="External market quote has already been processed")

    if quote.quote_kind == "retail_sku":
        if data.product_id is not None and data.product_id != quote.product_id:
            raise HTTPException(status_code=400, detail="SKU quote can only be accepted for its original product")
        product_id = quote.product_id
    else:
        if data.product_id is None:
            raise HTTPException(status_code=422, detail="Category quote acceptance requires product_id")
        product_id = data.product_id

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    claim = db.execute(
        update(ExternalMarketQuote)
        .where(ExternalMarketQuote.id == quote_id, ExternalMarketQuote.status == "pending")
        .values(status="accepting")
    )
    if claim.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="External market quote has already been processed")

    market_price = MarketPrice(
        record_date=quote.observed_at or date.today(),
        product_id=product_id,
        price_type="\u7f51\u7edc\u884c\u60c5\u53c2\u8003",
        competitor_price=data.price if data.price is not None else quote.price,
        market_trend=data.trend if data.trend is not None else quote.trend,
        content=json.dumps({
            "unit": data.unit if data.unit is not None else quote.unit,
            "source_name": quote.source_name,
            "source_url": quote.source_url,
            "source_excerpt": quote.source_excerpt,
        }, ensure_ascii=False),
        remark=data.remark,
        operator=data.operator,
    )
    try:
        db.add(market_price)
        db.flush()
        quote.accepted_market_price_id = market_price.id
        quote.accepted_at = datetime.now()
        quote.status = "accepted"
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(market_price)
    return market_price


@router.post("/external-market-quotes/{quote_id}/dismiss", response_model=ExternalMarketQuoteResponse)
def dismiss_external_market_quote(
    quote_id: int,
    data: ExternalMarketQuoteDismissCreate,
    db: Session = Depends(get_db),
):
    quote = db.query(ExternalMarketQuote).filter(ExternalMarketQuote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="External market quote not found")
    if quote.status != "pending":
        raise HTTPException(status_code=409, detail="External market quote has already been processed")

    claim = db.execute(
        update(ExternalMarketQuote)
        .where(ExternalMarketQuote.id == quote_id, ExternalMarketQuote.status == "pending")
        .values(
            status="dismissed",
            dismissed_at=datetime.now(),
            dismissed_remark=data.remark,
        )
    )
    if claim.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="External market quote has already been processed")

    db.commit()
    db.refresh(quote)
    return _quote_response(quote, db)


@router.get("/external-market-sync/status", response_model=ExternalMarketSyncStatusResponse)
def external_market_sync_status(db: Session = Depends(get_db)):
    schedule = db.query(SystemConfig).filter(SystemConfig.key == SYNC_TIME_KEY).first()
    last_run = db.query(ExternalMarketSyncRun).order_by(
        ExternalMarketSyncRun.started_at.desc(), ExternalMarketSyncRun.id.desc()
    ).first()
    return ExternalMarketSyncStatusResponse(
        is_configured=bool(os.getenv("ANYSEARCH_API_KEY")),
        sync_time=schedule.value if schedule else DEFAULT_SYNC_TIME,
        default_region=DEFAULT_REGION,
        last_run=ExternalMarketSyncRunResponse.model_validate(last_run) if last_run else None,
    )


@router.put("/external-market-sync/schedule", response_model=ExternalMarketSyncScheduleUpdate)
def update_external_market_sync_schedule(data: ExternalMarketSyncScheduleUpdate, db: Session = Depends(get_db)):
    schedule = db.query(SystemConfig).filter(SystemConfig.key == SYNC_TIME_KEY).first()
    if schedule:
        schedule.value = data.sync_time
    else:
        db.add(SystemConfig(key=SYNC_TIME_KEY, value=data.sync_time, description="External market sync time"))
    db.commit()
    get_market_sync_scheduler().reschedule(data.sync_time)
    return data
