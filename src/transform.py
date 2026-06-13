"""Transform raw yfinance data into an analytics-ready stock price table."""

from __future__ import annotations

import pandas as pd

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

# Handles multi-ticker data with MultiIndex columns, converting to long format
def _convert_multi_index_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Convert either yfinance MultiIndex layout into a long DataFrame."""
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

# Handles single-ticker flat data, ensuring ticker column exists
def _convert_flat_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Convert single-ticker yfinance data into a regular DataFrame."""
    flat_data = raw_data.copy()
    if "Ticker" not in flat_data.columns and "ticker" not in flat_data.columns:
        raise ValueError(
            "Single-ticker data must include a 'Ticker' column. "
            "Use extract_stock_data() or add the ticker before transforming."
        )
    return flat_data.reset_index()

# Main transformation function that cleans raw stock data and calculates daily returns
def transform_stock_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Clean raw stock data and calculate daily returns per ticker."""
    if raw_data.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    if isinstance(raw_data.columns, pd.MultiIndex):
        transformed = _convert_multi_index_data(raw_data)
    else:
        transformed = _convert_flat_data(raw_data)

    transformed.columns = [str(column).strip() for column in transformed.columns]
    date_column = next(
        (
            column
            for column in transformed.columns
            if column.lower() in {"date", "datetime", "price_date", "index"}
        ),
        None,
    )
    if date_column is None:
        raise ValueError("Could not find a date column in the extracted stock data.")

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
    missing_columns = required_columns.difference(transformed.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Extracted data is missing required columns: {missing}")

    transformed = transformed[list(required_columns)].copy()
    transformed["ticker"] = transformed["ticker"].astype("string").str.upper()
    transformed["price_date"] = pd.to_datetime(
        transformed["price_date"], errors="coerce", utc=True
    ).dt.tz_localize(None)

    numeric_columns = [
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "adj_close_price",
        "volume",
    ]
    transformed[numeric_columns] = transformed[numeric_columns].apply(
        pd.to_numeric, errors="coerce"
    )

    transformed = (
        transformed.drop_duplicates(subset=["ticker", "price_date"], keep="last")
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)
    )
    transformed["daily_return"] = transformed.groupby("ticker")[
        "close_price"
    ].pct_change(fill_method=None)
    transformed["loaded_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)

    return transformed[OUTPUT_COLUMNS]
