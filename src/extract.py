"""Extract historical daily stock prices from Yahoo Finance."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import yfinance as yf


def extract_stock_data(
    tickers: Sequence[str],
    period: str,
    interval: str,
) -> pd.DataFrame:
    """Download historical price data for the requested ticker symbols.

    The returned DataFrame is the raw yfinance result. Transformation and
    business rules are intentionally handled in ``transform.py``.
    """
    normalized_tickers = [ticker.strip().upper() for ticker in tickers if ticker.strip()]
    if not normalized_tickers:
        raise ValueError("At least one ticker is required for extraction.")

    raw_data = yf.download(
        tickers=normalized_tickers,
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    if raw_data is None or raw_data.empty:
        raise ValueError(
            "No stock data was returned. Check the ticker symbols, date period, "
            "and internet connection."
        )

    # Ensures each row has a Ticker column for consistent processing in later stages by adding a Ticker column when only one ticker is requested.
    # yfinance uses flat columns when only one ticker is requested.
    if not isinstance(raw_data.columns, pd.MultiIndex):
        raw_data = raw_data.copy()
        raw_data["Ticker"] = normalized_tickers[0]

    return raw_data
