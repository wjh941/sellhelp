import json
from datetime import date, datetime

from app.models.all_models import (
    ExternalMarketQuote,
    ExternalMarketSyncLock,
    ExternalMarketSyncRun,
    MarketPrice,
    Product,
    SystemConfig,
)
from app.services.anysearch_client import SearchResult


def add_product(db, name="Cooking oil"):
    product = Product(name=name, unit="bottle", is_active=True)
    db.add(product)
    db.commit()
    return product


def add_quote(db, *, product_id=None, quote_kind="official_category", status="pending", price=12.5):
    quote = ExternalMarketQuote(
        product_id=product_id,
        scope_label="Edible oil",
        region="National",
        quote_kind=quote_kind,
        source_name="Official bulletin",
        source_url="https://source.example.test/quotes/1",
        source_excerpt="Reference price from the official bulletin.",
        observed_at=date(2026, 8, 14),
        price=price,
        unit="CNY/L",
        trend="steady",
        status=status,
        quote_key=f"quote-{datetime.now().timestamp()}-{status}",
    )
    db.add(quote)
    db.commit()
    return quote


def test_list_external_quotes_filters_pending_product_kind_and_region(client, db_session):
    """Removing any list filter would expose a quote outside the requested review queue."""
    product = add_product(db_session)
    matching = add_quote(db_session, product_id=product.id, quote_kind="retail_sku")
    add_quote(db_session, quote_kind="official_category")
    add_quote(db_session, product_id=product.id, quote_kind="retail_sku", status="dismissed")

    response = client.get(
        "/api/external-market-quotes",
        params={
            "status": "pending",
            "product_id": product.id,
            "quote_kind": "retail_sku",
            "region": "National",
        },
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [matching.id]


def test_manual_sync_uses_fixed_manual_trigger_and_persists_pending_quotes(client, db_session, monkeypatch):
    """Changing the API trigger or allowing an external call would break controlled manual sync."""
    from app.routers import external_market_router

    class FakeSearchClient:
        api_key = "test-key"

        def search(self, query, max_results=5):
            return [SearchResult("Market bulletin", "https://source.example.test/new", "Price is \u00a56.80")]

    monkeypatch.setattr(external_market_router, "AnySearchClient", FakeSearchClient)
    response = client.post("/api/external-market-quotes/sync", params={"region": "ignored"})

    assert response.status_code == 200
    assert response.json()["trigger"] == "manual"
    assert response.json()["status"] == "success"
    assert db_session.query(ExternalMarketQuote).count() > 0
    assert db_session.query(MarketPrice).count() == 0


def test_manual_sync_reports_configuration_error_without_exposing_secret(client, db_session, monkeypatch):
    """Treating an absent API key as success or leaking it would make the sync unsafe to operate."""
    monkeypatch.delenv("ANYSEARCH_API_KEY", raising=False)

    response = client.post("/api/external-market-quotes/sync")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
    assert "ANYSEARCH_API_KEY" not in response.text
    assert db_session.query(ExternalMarketQuote).count() == 0


def test_manual_sync_returns_a_skipped_run_when_another_sync_holds_lock(client, db_session, monkeypatch):
    """Ignoring the lock status would report an in-progress sync as a completed sync."""
    from app.routers import external_market_router

    class ExplodingSearchClient:
        def search(self, query, max_results=5):
            raise AssertionError("locked sync must not search")

    db_session.add(ExternalMarketSyncLock(name="external_market_sync"))
    db_session.commit()
    monkeypatch.setattr(external_market_router, "AnySearchClient", ExplodingSearchClient)

    response = client.post("/api/external-market-quotes/sync")

    assert response.status_code == 200
    assert response.json()["status"] == "skipped"


def test_accept_quote_creates_market_price_only_after_human_confirmation(client, db_session):
    """Skipping the pending-state transition would let external data enter MarketPrice before review."""
    product = add_product(db_session)
    quote = add_quote(db_session)

    response = client.post(
        f"/api/external-market-quotes/{quote.id}/accept",
        json={
            "product_id": product.id,
            "price": 13.2,
            "unit": "CNY/500ml",
            "trend": "rising",
            "remark": "Verified with buyer",
            "operator": "alice",
        },
    )

    assert response.status_code == 200
    price = db_session.query(MarketPrice).one()
    assert response.json()["id"] == price.id
    assert price.record_date == date(2026, 8, 14)
    assert price.product_id == product.id
    assert price.price_type == "\u7f51\u7edc\u884c\u60c5\u53c2\u8003"
    assert price.competitor_price == 13.2
    assert price.market_trend == "rising"
    assert price.remark == "Verified with buyer"
    assert price.operator == "alice"
    assert json.loads(price.content) == {
        "unit": "CNY/500ml",
        "source_name": "Official bulletin",
        "source_url": "https://source.example.test/quotes/1",
        "source_excerpt": "Reference price from the official bulletin.",
    }
    db_session.refresh(quote)
    assert quote.status == "accepted"
    assert quote.accepted_market_price_id == price.id
    assert quote.accepted_at is not None


def test_accept_sku_quote_uses_original_product_and_quote_defaults(client, db_session):
    """Allowing a SKU quote to be reassigned would attach external evidence to the wrong product."""
    original = add_product(db_session, "Original")
    different = add_product(db_session, "Different")
    quote = add_quote(db_session, product_id=original.id, quote_kind="retail_sku")

    rejected = client.post(f"/api/external-market-quotes/{quote.id}/accept", json={"product_id": different.id})
    accepted = client.post(f"/api/external-market-quotes/{quote.id}/accept", json={})

    assert rejected.status_code == 400
    assert accepted.status_code == 200
    price = db_session.query(MarketPrice).one()
    assert price.product_id == original.id
    assert price.competitor_price == 12.5
    assert price.market_trend == "steady"


def test_accept_requires_existing_product_for_category_quote(client, db_session):
    """Allowing an unlinked category quote into MarketPrice would make the record unusable for pricing."""
    quote = add_quote(db_session)

    missing = client.post(f"/api/external-market-quotes/{quote.id}/accept", json={})
    unknown = client.post(f"/api/external-market-quotes/{quote.id}/accept", json={"product_id": 9999})

    assert missing.status_code == 422
    assert unknown.status_code == 404
    assert db_session.query(MarketPrice).count() == 0


def test_accept_rejects_unknown_or_processed_quote_without_second_market_price(client, db_session):
    """Dropping quote state checks would permit duplicate accepted market-price records."""
    product = add_product(db_session)
    quote = add_quote(db_session)

    unknown = client.post("/api/external-market-quotes/9999/accept", json={"product_id": product.id})
    first = client.post(f"/api/external-market-quotes/{quote.id}/accept", json={"product_id": product.id})
    second = client.post(f"/api/external-market-quotes/{quote.id}/accept", json={"product_id": product.id})

    assert unknown.status_code == 404
    assert first.status_code == 200
    assert second.status_code == 409
    assert db_session.query(MarketPrice).count() == 1


def test_dismiss_quote_records_auditable_remark_and_rejects_processed_quote(client, db_session):
    """Omitting the audit remark or allowing a second transition loses review accountability."""
    quote = add_quote(db_session)

    dismissed = client.post(
        f"/api/external-market-quotes/{quote.id}/dismiss",
        json={"remark": "Not comparable", "operator": "alice"},
    )
    repeated = client.post(f"/api/external-market-quotes/{quote.id}/dismiss", json={"remark": "again"})

    assert dismissed.status_code == 200
    assert repeated.status_code == 409
    db_session.refresh(quote)
    assert quote.status == "dismissed"
    assert quote.dismissed_at is not None
    assert quote.dismissed_remark == "Not comparable"
    assert db_session.query(MarketPrice).count() == 0


def test_sync_status_exposes_configuration_schedule_region_and_latest_run_without_secret(client, db_session, monkeypatch):
    """Returning environment values directly could reveal credentials or omit operational state."""
    monkeypatch.setenv("ANYSEARCH_API_KEY", "super-secret")
    db_session.add(SystemConfig(key="external_market_sync_time", value="02:30"))
    db_session.add(
        ExternalMarketSyncRun(
            trigger="manual",
            region="National",
            status="success",
            finished_at=datetime(2026, 8, 14, 9, 0),
        )
    )
    db_session.commit()

    response = client.get("/api/external-market-sync/status")

    assert response.status_code == 200
    assert response.json() == {
        "is_configured": True,
        "sync_time": "02:30",
        "default_region": "\u4e1c\u839e/\u5e7f\u4e1c",
        "last_run": {
            "id": 1,
            "trigger": "manual",
            "region": "National",
            "started_at": response.json()["last_run"]["started_at"],
            "finished_at": "2026-08-14T09:00:00",
            "status": "success",
            "quotes_created": 0,
            "duplicates_skipped": 0,
            "failure_detail": None,
        },
    }
    assert "super-secret" not in response.text


def test_sync_schedule_validates_and_persists_a_strict_24_hour_time(client, db_session):
    """Accepting malformed times would persist a value an eventual scheduler cannot run."""
    invalid = client.put("/api/external-market-sync/schedule", json={"sync_time": "24:00"})
    valid = client.put("/api/external-market-sync/schedule", json={"sync_time": "18:05"})

    assert invalid.status_code == 422
    assert valid.status_code == 200
    assert valid.json()["sync_time"] == "18:05"
    assert db_session.query(SystemConfig).filter_by(key="external_market_sync_time").one().value == "18:05"
