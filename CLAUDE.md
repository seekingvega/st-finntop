# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

st-finntop is a Bloomberg-style market news terminal built with Streamlit and Finnhub API. Python 3.10+, managed with [uv](https://docs.astral.sh/uv/).

## Architecture

- `streamlit_app.py` — Streamlit app: layout, tabs, search, Market/Company/Lookup mode selector, auto-refresh
- `news_client.py` — Finnhub API client: `NewsItem`/`SymbolResult` dataclasses, `fetch_news()`, `fetch_company_news()`, `search_symbols()`, `get_api_key()`
- `tests/test_news_client.py` — Unit tests for API client (mocked requests)
- `.streamlit/config.toml` — Dark theme config (Bloomberg aesthetic)
- `.streamlit/secrets.toml` — API key (gitignored)

## Commands

- **Run app**: `uv run streamlit run streamlit_app.py`
- **Run tests**: `uv run python -m pytest tests/`
- **Add dependency**: `uv add <package>`
- **Sync environment**: `uv sync`

## API Key Setup

Set `FINNHUB_API_KEY` in `.streamlit/secrets.toml` or as an environment variable:

```toml
# .streamlit/secrets.toml
FINNHUB_API_KEY = "your_key_here"
```

## Guidelines

- Create tests and update CLAUDE.md for each new feature
- Use `requests` directly for Finnhub API (no finnhub-python)
- Prefer native Streamlit features over custom CSS
- Keep minimal CSS only for hiding Streamlit chrome
