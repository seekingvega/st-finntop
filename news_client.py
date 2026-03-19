"""Finnhub market news API client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import requests

FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/news"
FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"
FINNHUB_SYMBOL_SEARCH_URL = "https://finnhub.io/api/v1/search"

CATEGORIES = ("general", "forex", "crypto", "merger")


@dataclass
class NewsItem:
    """A single news article from Finnhub."""

    headline: str
    source: str
    url: str
    category: str
    timestamp: datetime

    @classmethod
    def from_api(cls, data: dict) -> NewsItem:
        return cls(
            headline=data.get("headline", ""),
            source=data.get("source", ""),
            url=data.get("url", ""),
            category=data.get("category", ""),
            timestamp=datetime.fromtimestamp(data.get("datetime", 0), tz=timezone.utc),
        )


@dataclass
class SymbolResult:
    """A single symbol search result from Finnhub."""

    symbol: str
    description: str
    display_symbol: str
    type: str

    @classmethod
    def from_api(cls, data: dict) -> SymbolResult:
        return cls(
            symbol=data.get("symbol", ""),
            description=data.get("description", ""),
            display_symbol=data.get("displaySymbol", ""),
            type=data.get("type", ""),
        )


def search_symbols(
    api_key: str,
    query: str,
    exchanges: tuple[str, ...] = ("US", "TO"),
) -> list[SymbolResult]:
    """Search for symbols via Finnhub.

    Args:
        api_key: Finnhub API key.
        query: Search query string.
        exchanges: Allowed exchange suffixes. Symbols with no dot are treated
            as US equities. Symbols ending with '.TO' are Toronto.

    Returns:
        Filtered list of SymbolResult objects.
    """
    resp = requests.get(
        FINNHUB_SYMBOL_SEARCH_URL,
        params={"q": query},
        headers={"X-Finnhub-Token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    results = [SymbolResult.from_api(item) for item in resp.json().get("result", [])]
    filtered: list[SymbolResult] = []
    for r in results:
        if "." not in r.symbol:
            filtered.append(r)
        elif any(r.symbol.endswith(f".{ex}") for ex in exchanges):
            filtered.append(r)
    return filtered


def get_api_key() -> str:
    """Resolve Finnhub API key from Streamlit secrets or environment variable."""
    try:
        import streamlit as st

        return st.secrets["FINNHUB_API_KEY"]
    except Exception:
        pass

    key = os.environ.get("FINNHUB_API_KEY", "")
    if not key:
        raise ValueError(
            "FINNHUB_API_KEY not found. Set it in .streamlit/secrets.toml "
            "or as an environment variable."
        )
    return key


def fetch_company_news(
    api_key: str,
    symbol: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[NewsItem]:
    """Fetch company news from Finnhub.

    Args:
        api_key: Finnhub API key.
        symbol: Stock ticker symbol (e.g. "AAPL").
        from_date: Start date in YYYY-MM-DD format. Defaults to 14 days ago.
        to_date: End date in YYYY-MM-DD format. Defaults to today.

    Returns:
        List of NewsItem objects sorted by timestamp descending.
    """
    today = datetime.now(tz=timezone.utc).date()
    if to_date is None:
        to_date = today.isoformat()
    if from_date is None:
        from_date = (today - timedelta(days=14)).isoformat()

    resp = requests.get(
        FINNHUB_COMPANY_NEWS_URL,
        params={
            "symbol": symbol.replace(
                ".", "%2E"
            ),  # can't get canadian tickers e.g. L.TO so try to escape the dot
            "from": from_date,
            "to": to_date,
        },
        headers={"X-Finnhub-Token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    items = [NewsItem.from_api(article) for article in resp.json()]
    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items


def fetch_news(api_key: str, category: str = "general") -> list[NewsItem]:
    """Fetch market news from Finnhub.

    Args:
        api_key: Finnhub API key.
        category: One of 'general', 'forex', 'crypto', 'merger'.

    Returns:
        List of NewsItem objects sorted by timestamp descending.
    """
    resp = requests.get(
        FINNHUB_NEWS_URL,
        params={"category": category},
        headers={"X-Finnhub-Token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    items = [NewsItem.from_api(article) for article in resp.json()]
    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items
