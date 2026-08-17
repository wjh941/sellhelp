import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.all_models import Base, MarketPrice, PricingReference, Product
from app.services.pricing_service import PricingService


def test_pricing_reference_commits_and_rolls_back_failed_commit(tmp_path, monkeypatch):
    """Removing either transaction boundary loses or strands a pricing reference."""
    engine = create_engine(f"sqlite:///{(tmp_path / 'pricing.db').as_posix()}")
    session_local = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    try:
        writer = session_local()
        product = Product(name="Cooking oil", unit="bottle", purchase_price=10)
        writer.add(product)
        writer.commit()
        product_id = product.id

        PricingService(writer).calculate_pricing(product_id)
        writer.close()

        reader = session_local()
        reference = reader.query(PricingReference).filter_by(product_id=product_id).one()
        assert reference.confirmed is False
        reference_id = reference.id
        reader.close()

        confirmer = session_local()
        assert PricingService(confirmer).confirm_pricing(reference_id, "alice") is True
        confirmer.close()

        reader = session_local()
        assert reader.query(PricingReference).filter_by(id=reference_id).one().confirmed is True
        reader.close()

        failing_session = session_local()
        rollback_called = False
        original_rollback = failing_session.rollback

        def fail_commit():
            raise RuntimeError("simulated pricing commit failure")

        def track_rollback():
            nonlocal rollback_called
            rollback_called = True
            original_rollback()

        monkeypatch.setattr(failing_session, "commit", fail_commit)
        monkeypatch.setattr(failing_session, "rollback", track_rollback)

        with pytest.raises(RuntimeError, match="simulated pricing commit failure"):
            PricingService(failing_session).calculate_pricing(product_id)

        assert rollback_called is True
        failing_session.close()

        reader = session_local()
        assert reader.query(PricingReference).filter_by(product_id=product_id).count() == 1
        reader.close()
    finally:
        engine.dispose()


def test_market_price_route_rolls_back_failed_commit(client, db_session, monkeypatch):
    """A failed market-price write must not leave the shared request session dirty."""
    rollback_called = False
    original_rollback = db_session.rollback

    def fail_commit():
        raise RuntimeError("simulated market price commit failure")

    def track_rollback():
        nonlocal rollback_called
        rollback_called = True
        original_rollback()

    monkeypatch.setattr(db_session, "commit", fail_commit)
    monkeypatch.setattr(db_session, "rollback", track_rollback)

    with pytest.raises(RuntimeError, match="simulated market price commit failure"):
        client.post(
            "/api/market-prices",
            json={
                "record_date": "2026-08-17",
                "price_type": "manual",
                "competitor_price": 12.5,
            },
        )

    assert rollback_called is True
    assert db_session.query(MarketPrice).count() == 0
