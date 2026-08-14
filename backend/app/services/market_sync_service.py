"""Persist externally searched market data as pending, reviewable quotes."""

from datetime import date, datetime
import hashlib
import re
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.all_models import (
    ExternalMarketQuote,
    ExternalMarketSyncLock,
    ExternalMarketSyncRun,
    Product,
)
from .anysearch_client import AnySearchClient, MarketSearchError, SearchResult


OFFICIAL_SCOPES = ("食用油", "调味品", "饮用水")
DEFAULT_REGION = "东莞/广东"
NATIONAL_REGION = "全国"
LOCK_NAME = "external_market_sync"
OFFICIAL_DOMAIN_PRIORITY = ("ndrc.gov.cn", "grain.gov.cn", "gov.cn")
RMB_PRICE_PATTERN = re.compile(r"(?:[\u00a5\uffe5]\s*(\d+(?:\.\d{1,2})?)|(\d+(?:\.\d{1,2})?)\s*\u5143)")


def _official_query(scope: str, region: str) -> str:
    return f"{scope} {region} 市场价格 国家发展改革委 粮油信息"


def _retail_query(product: Product, region: str) -> str:
    spec = f" {product.spec}" if product.spec else ""
    return f"{product.name}{spec} {region} 零售价格"


class ExternalMarketSyncService:
    def __init__(self, db: Session, search_client=None):
        self.db = db
        self.search_client = search_client or AnySearchClient()

    def sync(self, trigger: str) -> ExternalMarketSyncRun:
        lock = ExternalMarketSyncLock(name=LOCK_NAME)
        try:
            self.db.add(lock)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return self._save_skipped_run(trigger)

        run = ExternalMarketSyncRun(trigger=trigger, region=DEFAULT_REGION, status="running")
        self.db.add(run)
        failures = []
        try:
            for scope in OFFICIAL_SCOPES:
                results, region, failure = self._search_with_fallback(_official_query(scope, DEFAULT_REGION), _official_query(scope, NATIONAL_REGION))
                if failure:
                    failures.append(f"{scope}: {failure}")
                    continue
                self._save_quotes(run, results, region, "official_category", scope, None)

            products = self.db.query(Product).filter(Product.is_active == True).all()
            for product in products:
                scope_label = f"{product.name} {product.spec}".strip() if product.spec else product.name
                results, region, failure = self._search_with_fallback(
                    _retail_query(product, DEFAULT_REGION), _retail_query(product, NATIONAL_REGION)
                )
                if failure:
                    failures.append(f"{scope_label}: {failure}")
                    continue
                self._save_quotes(run, results, region, "retail_sku", scope_label, product.id)

            run.status = "success" if not failures else "partial" if run.quotes_created or run.duplicates_skipped else "failed"
            run.failure_detail = "; ".join(failures) or None
        except Exception as exc:
            failures.append(self._safe_error(exc))
            run.status = "partial" if run.quotes_created or run.duplicates_skipped else "failed"
            run.failure_detail = "; ".join(failures)
        finally:
            run.finished_at = datetime.now()
            self.db.delete(lock)
            self.db.commit()
        return run

    def _save_skipped_run(self, trigger: str) -> ExternalMarketSyncRun:
        run = ExternalMarketSyncRun(
            trigger=trigger,
            region=DEFAULT_REGION,
            status="skipped",
            finished_at=datetime.now(),
        )
        self.db.add(run)
        self.db.commit()
        return run

    def _search_with_fallback(self, local_query: str, national_query: str):
        try:
            local_results = self._valid_results(self.search_client.search(local_query))
        except Exception as exc:
            return [], DEFAULT_REGION, self._safe_error(exc)
        if local_results:
            return local_results, DEFAULT_REGION, None
        try:
            national_results = self._valid_results(self.search_client.search(national_query))
        except Exception as exc:
            return [], NATIONAL_REGION, self._safe_error(exc)
        if national_results:
            return national_results, NATIONAL_REGION, None
        return [], NATIONAL_REGION, "No parseable search results"

    @staticmethod
    def _valid_results(results):
        if not isinstance(results, list):
            raise MarketSearchError("AnySearch returned an unexpected response")
        return [item for item in results if isinstance(item, SearchResult) and item.url.strip()]

    def _save_quotes(self, run, results, region, quote_kind, scope_label, product_id):
        observed_at = date.today()
        ordered_results = self._order_results(results, quote_kind)
        for result in ordered_results:
            price = self._parse_rmb_price(f"{result.title} {result.excerpt}")
            quote = ExternalMarketQuote(
                product_id=product_id,
                scope_label=scope_label,
                region=region,
                quote_kind=quote_kind,
                source_name=self._source_name(result),
                source_url=result.url,
                source_excerpt=result.excerpt,
                observed_at=observed_at,
                price=price,
                status="pending",
                quote_key=self._quote_key(quote_kind, scope_label, region, result.url, observed_at, price),
            )
            try:
                with self.db.begin_nested():
                    self.db.add(quote)
                    self.db.flush()
            except IntegrityError:
                run.duplicates_skipped += 1
            else:
                run.quotes_created += 1

    @staticmethod
    def _parse_rmb_price(text: str):
        match = RMB_PRICE_PATTERN.search(text)
        if not match:
            return None
        return float(match.group(1) or match.group(2))

    @staticmethod
    def _quote_key(quote_kind, scope_label, region, source_url, observed_at, price):
        value = "|".join((quote_kind, scope_label, region, source_url, observed_at.isoformat(), "" if price is None else str(price)))
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _source_name(result: SearchResult) -> str:
        return result.title or urlparse(result.url).netloc or result.url

    @staticmethod
    def _order_results(results, quote_kind):
        if quote_kind != "official_category":
            return results

        def domain_rank(result):
            host = urlparse(result.url).netloc.lower()
            for rank, domain in enumerate(OFFICIAL_DOMAIN_PRIORITY):
                if host == domain or host.endswith(f".{domain}"):
                    return rank
            return len(OFFICIAL_DOMAIN_PRIORITY)

        return sorted(results, key=domain_rank)

    def _safe_error(self, exc: Exception) -> str:
        detail = str(exc) or "Market search failed"
        api_key = getattr(self.search_client, "api_key", None)
        if api_key:
            detail = detail.replace(api_key, "[redacted]")
        return detail
