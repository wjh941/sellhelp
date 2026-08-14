"""Small, stdlib-only AnySearch MCP client for server-side market lookups."""

from dataclasses import dataclass
import json
import os
from typing import Any
import urllib.error
import urllib.request


class MarketSearchError(RuntimeError):
    """A controlled error that is safe to persist in a sync-run record."""


class MarketSearchConfigurationError(MarketSearchError):
    pass


class MarketSearchResponseError(MarketSearchError):
    pass


class MarketSearchNetworkError(MarketSearchError):
    pass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    excerpt: str


class AnySearchClient:
    endpoint = "https://api.anysearch.com/mcp"

    def __init__(self, api_key=None, timeout_seconds=15):
        # Credentials belong only in the process environment, never application state.
        if api_key is not None:
            raise ValueError("Configure ANYSEARCH_API_KEY through the environment")
        self.api_key = os.getenv("ANYSEARCH_API_KEY")
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.api_key:
            raise MarketSearchConfigurationError("ANYSEARCH_API_KEY is not configured")

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": query, "max_results": max_results}},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-Anysearch-Client": "sellhelp",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except UnicodeDecodeError:
            raise MarketSearchResponseError("AnySearch returned an unexpected response") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise MarketSearchNetworkError("AnySearch request failed") from None

        try:
            response_data = json.loads(body)
            items = self._extract_items(response_data)
            return [self._to_search_result(item) for item in items]
        except MarketSearchError:
            raise
        except (TypeError, ValueError, json.JSONDecodeError):
            raise MarketSearchResponseError("AnySearch returned an unexpected response") from None

    @classmethod
    def _extract_items(cls, response_data: Any) -> list[dict[str, Any]]:
        if not isinstance(response_data, dict) or response_data.get("error") is not None:
            raise MarketSearchResponseError("AnySearch returned an unexpected response")
        result = response_data.get("result")
        if not isinstance(result, dict):
            raise MarketSearchResponseError("AnySearch returned an unexpected response")
        for key in ("results", "data"):
            if isinstance(result.get(key), list):
                return result[key]
        content = result.get("content")
        if isinstance(content, list) and content and isinstance(content[0], dict):
            text = content[0].get("text")
            if isinstance(text, str):
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    for key in ("results", "data"):
                        if isinstance(parsed.get(key), list):
                            return parsed[key]
        raise MarketSearchResponseError("AnySearch returned an unexpected response")

    @staticmethod
    def _to_search_result(item: Any) -> SearchResult:
        if not isinstance(item, dict):
            raise MarketSearchResponseError("AnySearch returned an unexpected response")
        title = item.get("title", "")
        url = item.get("url")
        excerpt = item.get("excerpt", item.get("snippet", item.get("content", "")))
        if not isinstance(title, str) or not isinstance(url, str) or not isinstance(excerpt, str) or not url.strip():
            raise MarketSearchResponseError("AnySearch returned an unexpected response")
        return SearchResult(title=title.strip(), url=url.strip(), excerpt=excerpt.strip())
