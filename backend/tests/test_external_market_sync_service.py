import pytest

from app.models.all_models import (
    ExternalMarketQuote,
    ExternalMarketSyncLock,
    MarketPrice,
    Product,
)
from app.services.anysearch_client import AnySearchClient, MarketSearchResponseError, SearchResult
from app.services import anysearch_client
from app.services.market_sync_service import ExternalMarketSyncService


class FakeSearchClient:
    def __init__(self, responder):
        self.responder = responder
        self.queries = []

    def search(self, query, max_results=5):
        self.queries.append(query)
        return self.responder(query)


def quote(title="Price bulletin", url="https://example.test/quote", excerpt="Retail price is ¥12.50 per unit"):
    return SearchResult(title=title, url=url, excerpt=excerpt)


def test_sync_falls_back_to_national_only_after_empty_local_result(db_session):
    client = FakeSearchClient(
        lambda query: [] if "食用油" in query and "东莞/广东" in query else [quote()]
    )

    run = ExternalMarketSyncService(db_session, client).sync(trigger="manual")

    local_query = "食用油 东莞/广东 市场价格 国家发展改革委 粮油信息"
    national_query = "食用油 全国 市场价格 国家发展改革委 粮油信息"
    assert client.queries.index(local_query) < client.queries.index(national_query)
    assert db_session.query(ExternalMarketQuote).filter_by(scope_label="食用油").one().region == "全国"
    assert run.status == "success"


def test_sync_does_not_fall_back_when_local_results_exist(db_session):
    client = FakeSearchClient(lambda query: [quote(url=f"https://example.test/{len(query)}")])

    ExternalMarketSyncService(db_session, client).sync(trigger="manual")

    assert client.queries
    assert not any("全国" in query for query in client.queries)


def test_sync_records_official_and_retail_quotes_in_pending_ledger_only(db_session):
    product = Product(name="示例酱油", spec="500ml", unit="瓶")
    db_session.add(product)
    db_session.commit()
    client = FakeSearchClient(lambda query: [quote(url=f"https://example.test/{len(query)}")])

    ExternalMarketSyncService(db_session, client).sync(trigger="manual")

    quotes = db_session.query(ExternalMarketQuote).all()
    assert {item.quote_kind for item in quotes} == {"official_category", "retail_sku"}
    assert all(item.status == "pending" for item in quotes)
    assert all(item.quote_kind != "retail_sku" or item.product_id == product.id for item in quotes)
    assert db_session.query(MarketPrice).count() == 0


def test_sync_deduplicates_same_source_scope_date_and_price(db_session):
    product = Product(name="示例酱油", spec="500ml", unit="瓶")
    db_session.add(product)
    db_session.commit()
    client = FakeSearchClient(lambda query: [quote()])
    service = ExternalMarketSyncService(db_session, client)

    first = service.sync(trigger="manual")
    count_after_first = db_session.query(ExternalMarketQuote).count()
    second = service.sync(trigger="manual")

    assert first.quotes_created == count_after_first
    assert second.quotes_created == 0
    assert second.duplicates_skipped == count_after_first
    assert db_session.query(ExternalMarketQuote).count() == count_after_first


def test_sync_records_failed_run_without_key_or_network_request(db_session, monkeypatch):
    monkeypatch.delenv("ANYSEARCH_API_KEY", raising=False)
    client = AnySearchClient()

    run = ExternalMarketSyncService(db_session, client).sync(trigger="manual")

    assert run.status == "failed"
    assert "ANYSEARCH_API_KEY" in (run.failure_detail or "")
    assert db_session.query(ExternalMarketQuote).count() == 0
    assert db_session.query(MarketPrice).count() == 0


def test_sync_records_failed_run_when_no_parseable_results_or_network_fails(db_session):
    empty_run = ExternalMarketSyncService(db_session, FakeSearchClient(lambda query: [])).sync(trigger="manual")

    assert empty_run.status == "failed"
    assert db_session.query(ExternalMarketQuote).count() == 0

    class NetworkFailureClient:
        def search(self, query, max_results=5):
            raise RuntimeError("network unavailable")

    failure_run = ExternalMarketSyncService(db_session, NetworkFailureClient()).sync(trigger="manual")

    assert failure_run.status == "failed"
    assert "network unavailable" in (failure_run.failure_detail or "")


def test_sync_returns_skipped_without_search_when_lock_is_held(db_session):
    db_session.add(ExternalMarketSyncLock(name="external_market_sync"))
    db_session.commit()
    client = FakeSearchClient(lambda query: [quote()])

    run = ExternalMarketSyncService(db_session, client).sync(trigger="manual")

    assert run.status == "skipped"
    assert client.queries == []


def test_anysearch_client_parses_structured_results_via_injected_urlopen(monkeypatch):
    class Response:
        def read(self):
            return b'{"result": {"results": [{"title": "Bulletin", "url": "https://source.test/p", "excerpt": "Price is \\u00a56.8"}]}}'

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    calls = []
    monkeypatch.setenv("ANYSEARCH_API_KEY", "test-key")
    monkeypatch.setattr(
        anysearch_client.urllib.request,
        "urlopen",
        lambda request, timeout: calls.append((request, timeout)) or Response(),
    )

    results = AnySearchClient().search("食用油 东莞/广东 市场价格")

    assert results == [SearchResult("Bulletin", "https://source.test/p", "Price is ¥6.8")]
    assert len(calls) == 1


def test_sync_keeps_unmarked_numbers_as_price_none(db_session):
    client = FakeSearchClient(lambda query: [quote(excerpt="Listed as 12.50 per unit")])
    ExternalMarketSyncService(db_session, client).sync(trigger="manual")
    assert all(item.price is None for item in db_session.query(ExternalMarketQuote).all())


def test_anysearch_client_converts_malformed_bytes_to_controlled_error(monkeypatch):

    class Response:
        def read(self):
            return b"\xff"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setenv("ANYSEARCH_API_KEY", "test-key")
    monkeypatch.setattr(anysearch_client.urllib.request, "urlopen", lambda request, timeout: Response())
    with pytest.raises(MarketSearchResponseError):
        AnySearchClient().search("食用油")
