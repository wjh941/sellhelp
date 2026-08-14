from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import pytest

import app.models.all_models as models
import app.schemas.all_schemas as schemas


def test_pending_external_quotes_stay_in_their_own_traceable_ledger():
    """Removing the external ledger or its quote-key constraint breaks this contract."""
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    try:
        assert {
            "external_market_quotes",
            "external_market_sync_runs",
            "external_market_sync_locks",
        }.issubset(inspect(engine).get_table_names())

        quote = models.ExternalMarketQuote(
            scope_label="edible oil",
            region="Dongguan/Guangdong",
            quote_kind="official_category",
            source_name="Official source",
            source_url="https://example.test/quote",
            source_excerpt="Price could not be reliably parsed.",
            quote_key="a" * 64,
        )
        session.add(quote)
        session.commit()

        assert quote.status == "pending"
        assert quote.price is None
        assert session.query(models.MarketPrice).count() == 0

        session.add(
            models.ExternalMarketQuote(
                scope_label="edible oil",
                region="Dongguan/Guangdong",
                quote_kind="official_category",
                source_name="Official source",
                source_url="https://example.test/quote",
                source_excerpt="Duplicate source data.",
                quote_key="a" * 64,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("duplicate external quote keys must be rejected")
    finally:
        session.close()
        engine.dispose()


def test_external_market_schema_keeps_human_confirmation_and_key_status_explicit():
    """Removing manual confirmation fields or exposing a key in status breaks the API contract."""
    accepted = schemas.ExternalMarketQuoteAcceptCreate(
        price=12.5,
        unit="CNY/L",
        trend="steady",
        remark="confirmed against source",
        operator="operator-a",
    )

    assert accepted.price == 12.5
    assert accepted.unit == "CNY/L"
    assert accepted.trend == "steady"
    assert accepted.remark == "confirmed against source"
    assert accepted.operator == "operator-a"
    assert schemas.ExternalMarketSyncStatusResponse.model_fields.keys() == {
        "is_configured", "sync_time", "default_region", "last_run"
    }


def test_external_market_schedule_accepts_only_24_hour_times():
    """Changing the schedule pattern to accept invalid times breaks scheduler input validation."""
    assert schemas.ExternalMarketSyncScheduleUpdate(sync_time="02:00").sync_time == "02:00"

    with pytest.raises(ValueError):
        schemas.ExternalMarketSyncScheduleUpdate(sync_time="25:00")
