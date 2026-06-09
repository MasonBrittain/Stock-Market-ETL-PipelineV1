"""Data quality rules for transformed stock market data."""

from __future__ import annotations

import pandas as pd

PRICE_COLUMNS = [
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "adj_close_price",
]


def run_quality_checks(stock_data: pd.DataFrame) -> None:
    """Validate stock data and raise a clear ValueError for invalid records."""
    required_columns = {"ticker", "price_date", "volume", *PRICE_COLUMNS}
    missing_columns = required_columns.difference(stock_data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Quality check failed: missing required columns: {missing}.")

    if stock_data["ticker"].isna().any() or stock_data["ticker"].astype(str).str.strip().eq("").any():
        raise ValueError("Quality check failed: ticker contains missing or blank values.")

    if stock_data["price_date"].isna().any():
        raise ValueError("Quality check failed: price_date contains missing values.")

    negative_price_columns = [
        column for column in PRICE_COLUMNS if stock_data[column].lt(0).any()
    ]
    if negative_price_columns:
        columns = ", ".join(negative_price_columns)
        raise ValueError(f"Quality check failed: negative prices found in {columns}.")

    if stock_data["volume"].lt(0).any():
        raise ValueError("Quality check failed: volume contains negative values.")

    duplicate_count = stock_data.duplicated(
        subset=["ticker", "price_date"], keep=False
    ).sum()
    if duplicate_count:
        raise ValueError(
            "Quality check failed: "
            f"found {duplicate_count} rows with duplicate ticker and price_date values."
        )
# 