"""MKTNEWS Terminal — Bloomberg-style market news viewer."""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from news_client import (
    NewsItem,
    fetch_news,
    fetch_company_news,
    search_symbols,
    get_api_key,
    CATEGORIES,
)

REFRESH_INTERVAL = os.getenv("REFRESH_INTERVAL", 300)

# --- news_panel's Tab labels ---
TAB_MAP = {
    "ALL": None,
    "TOP": "general",  # same as "top news" and "business"
    "FOREX": "forex",
    "CRYPTO": "crypto",
    "M&A": "merger",
}

# --- Resolve API key ---
try:
    api_key = get_api_key()
except ValueError as e:
    st.error(str(e))
    st.stop()


def hide_streamlit_elements():
    # --- Minimal CSS: hide Streamlit chrome for terminal look ---
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding-top: 1rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- Cached fetch ---
@st.cache_data(ttl=300)
def _fetch(
    api_key: str, category: str, tz_name: str = "America/New_York"
) -> list[dict]:
    _tz = ZoneInfo(tz_name)
    items = fetch_news(api_key, category)
    return [
        {
            "time": item.timestamp.astimezone(_tz).strftime("%b %d, %a, %H:%M"),
            "source": item.source,
            "headline": item.headline,
            "url": item.url,
            "category": item.category.upper(),
            "_timestamp": item.timestamp,
        }
        for item in items
    ]


@st.cache_data(ttl=300)
def _fetch_company(api_key: str, symbol: str, tz_name: str) -> list[dict]:
    _tz = ZoneInfo(tz_name)
    items = fetch_company_news(api_key, symbol)
    return [
        {
            "time": item.timestamp.astimezone(_tz).strftime("%a, %b %d %Y %H:%M"),
            "source": item.source,
            "headline": item.headline,
            "url": item.url,
            "_timestamp": item.timestamp,
        }
        for item in items
    ]


@st.cache_data(ttl=300)
def _search_symbols(api_key: str, query: str) -> list[dict]:
    results = search_symbols(api_key, query)
    return [
        {
            "symbol": r.symbol,
            "name": r.description,
            "type": r.type,
        }
        for r in results
    ]


def _build_df(rows: list[dict], query: str) -> pd.DataFrame:
    df = (
        pd.DataFrame(rows)
        if rows
        else pd.DataFrame(columns=["time", "source", "headline", "url", "category"])
    )
    if query:
        mask = df["headline"].str.contains(query, case=False, na=False)
        df = df[mask]
    return df


# --- Auto-refreshing news fragment ---
@st.fragment(run_every=REFRESH_INTERVAL)
def news_panel(tz: ZoneInfo, mode: str, search_query: str = None):
    cols = st.columns((1, 1, 3))
    now_time = datetime.now(tz)
    tz_name = tz.key
    cols[0].markdown(
        f"**Last updated: {now_time.strftime('%H:%M:%S')} {now_time.tzname()}**"
    )
    cols[1].caption(f"refreshes every: {REFRESH_INTERVAL/60} minutes")

    if mode == "Lookup":
        if not search_query:
            st.info("Enter a company name or keyword to search for symbols.")
            return

        rows = _search_symbols(api_key, search_query.strip())
        if not rows:
            st.info(f"No symbols found for **{search_query.strip()}**.")
        else:
            df = pd.DataFrame(rows)
            st.dataframe(
                df,
                column_config={
                    "symbol": st.column_config.TextColumn("SYMBOL", width="small"),
                    "name": st.column_config.TextColumn("NAME", width="large"),
                    "type": st.column_config.TextColumn("TYPE", width="small"),
                },
                hide_index=True,
                width="stretch",
                # height=600,
            )
    elif mode == "Company":
        # Company news mode: single table, no category tabs
        if not search_query:
            st.info("Enter a ticker symbol above to search for company news.")
            return

        symbol = search_query.strip().upper()
        rows = _fetch_company(api_key, symbol, tz_name)
        df = _build_df(rows, "")

        if df.empty:
            st.info(f"No articles found for **{symbol}**.")
        else:
            display_cols = ["time", "source", "headline", "url"]
            st.dataframe(
                df[display_cols],
                column_config={
                    "time": st.column_config.TextColumn("TIME", width="small"),
                    "source": st.column_config.TextColumn("SOURCE", width="small"),
                    "headline": st.column_config.TextColumn("HEADLINE", width="large"),
                    "url": st.column_config.LinkColumn(
                        "LINK",
                        display_text="Open",
                        width="small",
                    ),
                },
                hide_index=True,
                width="stretch",
                height=800,
            )
    else:
        # Market news mode: tabs with category filtering
        tabs = st.tabs(list(TAB_MAP.keys()))

        for tab, (label, category) in zip(tabs, TAB_MAP.items()):
            with tab:
                if category is None:
                    all_rows: list[dict] = []
                    for cat in CATEGORIES:
                        all_rows.extend(_fetch(api_key, cat, tz_name))
                    all_rows.sort(key=lambda r: r["_timestamp"], reverse=True)
                    df = _build_df(all_rows, search_query)
                else:
                    rows = _fetch(api_key, category, tz_name)
                    df = _build_df(rows, search_query)

                if df.empty:
                    st.info("No articles found.")
                else:
                    display_cols = ["time", "source", "headline", "url"]
                    if category is None:
                        display_cols.insert(3, "category")

                    st.dataframe(
                        df[display_cols],
                        column_config={
                            "time": st.column_config.TextColumn("TIME", width="small"),
                            "source": st.column_config.TextColumn(
                                "SOURCE", width="small"
                            ),
                            "headline": st.column_config.TextColumn(
                                "HEADLINE", width="large"
                            ),
                            "url": st.column_config.LinkColumn(
                                "LINK",
                                display_text="Open",
                                width="small",
                            ),
                            "category": st.column_config.TextColumn(
                                "CAT", width="small"
                            ),
                        },
                        hide_index=True,
                        width="stretch",
                        height=800,
                    )


def main():
    # --- Page config ---
    st.set_page_config(
        page_title="FINNTOP",
        page_icon=":material/breaking_news:",
        layout="wide",
    )

    # --- Timezone options ---
    TIMEZONE_OPTIONS = {
        "ET": "America/New_York",
        "CT": "America/Chicago",
        "PT": "America/Los_Angeles",
        "UTC": "UTC",
        "GMT": "Europe/London",
        "CET": "Europe/Berlin",
        "JST": "Asia/Tokyo",
        "HKT": "Asia/Hong_Kong",
    }

    # --- Header row ---
    col_title, col_mode, col_search, col_tz = st.columns([2, 2, 3, 1.5])
    with col_title:
        st.markdown("### [FINNTOP](https://github.com/seekingvega/st-finntop)")
    with col_mode:
        mode = st.segmented_control(
            "Mode",
            ["Market", "Company", "Lookup"],
            default="Market",
            label_visibility="collapsed",
        )
    with col_search:
        placeholders = {
            "Market": "Filter headlines...",
            "Company": "Enter ticker (e.g. AAPL)...",
            "Lookup": "Search symbol (e.g. Apple)...",
        }
        search_query = st.text_input(
            "Search",
            placeholder=placeholders.get(mode, "Filter headlines..."),
            label_visibility="collapsed",
        )
    with col_tz:
        tz_label = st.selectbox(
            "Timezone",
            options=list(TIMEZONE_OPTIONS.keys()),
            index=0,
            label_visibility="collapsed",
        )
    tz_name = TIMEZONE_OPTIONS[tz_label]
    tz = ZoneInfo(tz_name)

    news_panel(tz=tz, mode=mode, search_query=search_query)


if __name__ == "__main__":
    main()
