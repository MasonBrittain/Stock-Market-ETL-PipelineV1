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


def test_duplicate_ticker_and_price_date_is_flagged_as_warning() -> None:
    # In V2, duplicate rows are a non-critical check — they are flagged in the
    # quality report but do not abort the pipeline with a ValueError.
    stock_data = _valid_stock_data()
    stock_data.loc[1, "ticker"] = "AAPL"

    results = run_quality_checks(stock_data)

    assert results["checks"]["duplicate_rows"]["passed"] is False
    assert results["checks"]["duplicate_rows"]["failures"] == 2
    # overall_passed is False because a check failed, but no exception is raised
    assert results["overall_passed"] is False


def test_negative_price_raises_critical_error() -> None:
    # negative_prices is a CRITICAL check — it raises ValueError.
    stock_data = _valid_stock_data()
    stock_data.loc[0, "close_price"] = -1.0

    with pytest.raises(ValueError, match="Critical quality checks failed"):
        run_quality_checks(stock_data)
