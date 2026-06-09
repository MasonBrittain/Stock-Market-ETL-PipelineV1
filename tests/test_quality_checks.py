"""Tests for stock data quality rules."""

import pandas as pd
import pytest

from src.quality_checks import run_quality_checks


def _valid_stock_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "price_date": pd.to_datetime(["2026-01-01", "2026-01-01"]),
            "open_price": [100.0, 200.0],
            "high_price": [102.0, 202.0],
            "low_price": [99.0, 199.0],
            "close_price": [101.0, 201.0],
            "adj_close_price": [101.0, 201.0],
            "volume": [1000, 2000],
        }
    )


def test_duplicate_ticker_and_price_date_is_rejected() -> None:
    stock_data = _valid_stock_data()
    stock_data.loc[1, "ticker"] = "AAPL"

    with pytest.raises(ValueError, match="duplicate ticker and price_date"):
        run_quality_checks(stock_data)


def test_negative_price_is_rejected() -> None:
    stock_data = _valid_stock_data()
    stock_data.loc[0, "close_price"] = -1.0

    with pytest.raises(ValueError, match="negative prices"):
        run_quality_checks(stock_data)
