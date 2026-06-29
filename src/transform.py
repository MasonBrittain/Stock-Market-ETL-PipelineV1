"""Transform raw yfinance data into an analytics-ready stock price table."""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "ticker",
    "price_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "adj_close_price",
    "volume",
    "daily_return",
    "loaded_at",
]

YFINANCE_FIELDS = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}


def _convert_multi_index_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Convert a yfinance MultiIndex layout into a long-format DataFrame."""
    first_level = set(raw_data.columns.get_level_values(0))
    field_first = bool(first_level.intersection(YFINANCE_FIELDS))
    ticker_level = 1 if field_first else 0
    tickers = raw_data.columns.get_level_values(ticker_level).unique()

    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        ticker_frame = raw_data.xs(ticker, axis=1, level=ticker_level).copy()
        ticker_frame["Ticker"] = str(ticker)
        frames.append(ticker_frame.reset_index())

    return pd.concat(frames, ignore_index=True)


def _convert_flat_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Convert single-ticker (or pre-concatenated) yfinance data into a plain DataFrame."""
    flat_data = raw_data.copy()
    if "Ticker" not in flat_data.columns and "ticker" not in flat_data.columns:
        raise ValueError(
            "Flat data must include a 'Ticker' column. "
            "Use extract_stock_data() or add the column before transforming."
        )
    return flat_data.reset_index()


def transform_stock_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Clean raw yfinance data and calculate daily returns per ticker.

    Accepts both the MultiIndex format (multiple tickers, V1 style) and the
    flat concatenated format produced by the V2 per-ticker extract loop.
    Returns a DataFrame with exactly the columns in OUTPUT_COLUMNS.
    """
    logger.info("Transformation started — input rows: %d", len(raw_data))

    if raw_data.empty:
        logger.warning("Empty DataFrame passed to transform — returning empty output")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    if isinstance(raw_data.columns, pd.MultiIndex):
        transformed = _convert_multi_index_data(raw_data)
    else:
        transformed = _convert_flat_data(raw_data)

    transformed.columns = [str(col).strip() for col in transformed.columns]

    date_column = next(
        (
            col
            for col in transformed.columns
            if col.lower() in {"date", "datetime", "price_date"}
        ),
        None,
    )
    if date_column is None:
        raise ValueError("Could not locate a date column in the extracted stock data.")

    transformed = transformed.rename(
        columns={
            "Ticker": "ticker",
            "Open": "open_price",
            "High": "high_price",
            "Low": "low_price",
            "Close": "close_price",
            "Adj Close": "adj_close_price",
            "Volume": "volume",
            date_column: "price_date",
        }
    )

    required_columns = {
        "ticker",
        "price_date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "adj_close_price",
        "volume",
    }
    missing = required_columns.difference(transformed.columns)
    if missing:
        raise ValueError(f"Extracted data is missing required columns: {', '.join(sorted(missing))}")

    transformed = transformed[list(required_columns)].copy()
    transformed["ticker"] = transformed["ticker"].astype("string").str.upper()
    transformed["price_date"] = pd.to_datetime(
        transformed["price_date"], errors="coerce", utc=True
    ).dt.tz_localize(None)

    numeric_cols = ["open_price", "high_price", "low_price", "close_price", "adj_close_price", "volume"]
    transformed[numeric_cols] = transformed[numeric_cols].apply(pd.to_numeric, errors="coerce")

    before_dedup = len(transformed)
    transformed = (
        transformed.drop_duplicates(subset=["ticker", "price_date"], keep="last")
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)
    )
    duplicates_dropped = before_dedup - len(transformed)
    if duplicates_dropped:
        logger.info("Removed %d duplicate ticker/date rows", duplicates_dropped)

    transformed["daily_return"] = transformed.groupby("ticker")["close_price"].pct_change(
        fill_method=None
    )
    transformed["loaded_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)

    logger.info("Transformation complete — output rows: %d", len(transformed))
    return transformed[OUTPUT_COLUMNS]
