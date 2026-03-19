"""Tests for news_client module."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import requests

from news_client import NewsItem, SymbolResult, fetch_news, fetch_company_news, search_symbols, get_api_key


SAMPLE_ARTICLE = {
    "category": "general",
    "datetime": 1711900800,
    "headline": "Fed signals rate pause amid inflation concerns",
    "id": 12345,
    "image": "https://example.com/img.jpg",
    "related": "",
    "source": "Reuters",
    "summary": "The Federal Reserve...",
    "url": "https://example.com/article",
}


class TestNewsItemFromApi:
    def test_parse_valid_article(self):
        item = NewsItem.from_api(SAMPLE_ARTICLE)
        assert item.headline == "Fed signals rate pause amid inflation concerns"
        assert item.source == "Reuters"
        assert item.url == "https://example.com/article"
        assert item.category == "general"
        assert item.timestamp == datetime(2024, 3, 31, 16, 0, tzinfo=timezone.utc)

    def test_parse_missing_fields(self):
        item = NewsItem.from_api({})
        assert item.headline == ""
        assert item.source == ""
        assert item.url == ""
        assert item.category == ""
        assert item.timestamp == datetime(1970, 1, 1, tzinfo=timezone.utc)


class TestFetchNews:
    @patch("news_client.requests.get")
    def test_fetch_returns_sorted_items(self, mock_get):
        older = {**SAMPLE_ARTICLE, "datetime": 1000}
        newer = {**SAMPLE_ARTICLE, "datetime": 2000}
        mock_get.return_value.json.return_value = [older, newer]
        mock_get.return_value.raise_for_status.return_value = None

        items = fetch_news("fake-key", "general")
        assert len(items) == 2
        assert items[0].timestamp > items[1].timestamp

    @patch("news_client.requests.get")
    def test_fetch_empty_response(self, mock_get):
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status.return_value = None

        items = fetch_news("fake-key")
        assert items == []

    @patch("news_client.requests.get")
    def test_fetch_http_error(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("403")

        with pytest.raises(requests.HTTPError):
            fetch_news("fake-key")

    @patch("news_client.requests.get")
    def test_fetch_passes_params(self, mock_get):
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status.return_value = None

        fetch_news("my-key", "crypto")
        mock_get.assert_called_once_with(
            "https://finnhub.io/api/v1/news",
            params={"category": "crypto"},
            headers={"X-Finnhub-Token": "my-key"},
            timeout=10,
        )


class TestFetchCompanyNews:
    @patch("news_client.requests.get")
    def test_fetch_returns_sorted_items(self, mock_get):
        older = {**SAMPLE_ARTICLE, "datetime": 1000}
        newer = {**SAMPLE_ARTICLE, "datetime": 2000}
        mock_get.return_value.json.return_value = [older, newer]
        mock_get.return_value.raise_for_status.return_value = None

        items = fetch_company_news("fake-key", "AAPL")
        assert len(items) == 2
        assert items[0].timestamp > items[1].timestamp

    @patch("news_client.requests.get")
    def test_fetch_empty_response(self, mock_get):
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status.return_value = None

        items = fetch_company_news("fake-key", "AAPL")
        assert items == []

    @patch("news_client.requests.get")
    def test_fetch_passes_correct_params(self, mock_get):
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status.return_value = None

        fetch_company_news("my-key", "TSLA", from_date="2026-03-01", to_date="2026-03-15")
        mock_get.assert_called_once_with(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": "TSLA",
                "from": "2026-03-01",
                "to": "2026-03-15",
            },
            headers={"X-Finnhub-Token": "my-key"},
            timeout=10,
        )

    @patch("news_client.requests.get")
    def test_fetch_default_dates(self, mock_get):
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status.return_value = None

        fetch_company_news("my-key", "AAPL")
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["symbol"] == "AAPL"
        assert call_kwargs["headers"]["X-Finnhub-Token"] == "my-key"
        assert "from" in call_kwargs["params"]
        assert "to" in call_kwargs["params"]


SAMPLE_SEARCH_RESPONSE = {
    "count": 4,
    "result": [
        {"symbol": "AAPL", "displaySymbol": "AAPL", "description": "Apple Inc", "type": "Common Stock"},
        {"symbol": "AAPL.TO", "displaySymbol": "AAPL.TO", "description": "Apple Inc (Toronto)", "type": "Common Stock"},
        {"symbol": "APC.F", "displaySymbol": "APC.F", "description": "Apple Inc (Frankfurt)", "type": "Common Stock"},
        {"symbol": "AAPL.MX", "displaySymbol": "AAPL.MX", "description": "Apple Inc (Mexico)", "type": "Common Stock"},
    ],
}


class TestSearchSymbols:
    @patch("news_client.requests.get")
    def test_passes_correct_params(self, mock_get):
        mock_get.return_value.json.return_value = {"count": 0, "result": []}
        mock_get.return_value.raise_for_status.return_value = None

        search_symbols("my-key", "apple")
        mock_get.assert_called_once_with(
            "https://finnhub.io/api/v1/search",
            params={"q": "apple"},
            headers={"X-Finnhub-Token": "my-key"},
            timeout=10,
        )

    @patch("news_client.requests.get")
    def test_parses_results(self, mock_get):
        mock_get.return_value.json.return_value = SAMPLE_SEARCH_RESPONSE
        mock_get.return_value.raise_for_status.return_value = None

        results = search_symbols("fake-key", "apple")
        assert all(isinstance(r, SymbolResult) for r in results)
        assert results[0].symbol == "AAPL"
        assert results[0].description == "Apple Inc"
        assert results[0].display_symbol == "AAPL"
        assert results[0].type == "Common Stock"

    @patch("news_client.requests.get")
    def test_filters_exchanges(self, mock_get):
        mock_get.return_value.json.return_value = SAMPLE_SEARCH_RESPONSE
        mock_get.return_value.raise_for_status.return_value = None

        results = search_symbols("fake-key", "apple")
        symbols = [r.symbol for r in results]
        assert "AAPL" in symbols       # no dot → US
        assert "AAPL.TO" in symbols     # .TO → Toronto
        assert "APC.F" not in symbols   # .F → Frankfurt, filtered out
        assert "AAPL.MX" not in symbols # .MX → Mexico, filtered out

    @patch("news_client.requests.get")
    def test_empty_response(self, mock_get):
        mock_get.return_value.json.return_value = {"count": 0, "result": []}
        mock_get.return_value.raise_for_status.return_value = None

        results = search_symbols("fake-key", "xyznonexistent")
        assert results == []


class TestGetApiKey:
    @patch.dict("os.environ", {"FINNHUB_API_KEY": "env-key"})
    def test_key_from_env(self):
        key = get_api_key()
        assert key == "env-key"

    @patch.dict("os.environ", {}, clear=True)
    def test_key_missing_raises(self):
        with pytest.raises(ValueError, match="FINNHUB_API_KEY not found"):
            get_api_key()
