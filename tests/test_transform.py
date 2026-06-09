"""Tests for stock data transformations."""

import pandas as pd
import pytest

from src.transform import transform_stock_data


def test_daily_return_is_calculated_per_ticker() -> None:
    raw_data = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-01", "2026-01-02"]
            ),
            "Ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "Open": [100.0, 110.0, 200.0, 190.0],
            "High": [102.0, 112.0, 202.0, 192.0],
            "Low": [99.0, 109.0, 199.0, 189.0],
            "Close": [100.0, 110.0, 200.0, 190.0],
            "Adj Close": [100.0, 110.0, 200.0, 190.0],
            "Volume": [1000, 1200, 2000, 2200],
        }
    ).set_index("Date")

    result = transform_stock_data(raw_data)

    aapl_returns = result.loc[result["ticker"] == "AAPL", "daily_return"]
    msft_returns = result.loc[result["ticker"] == "MSFT", "daily_return"]

    assert pd.isna(aapl_returns.iloc[0])
    assert aapl_returns.iloc[1] == pytest.approx(0.10)
    assert pd.isna(msft_returns.iloc[0])
    assert msft_returns.iloc[1] == pytest.approx(-0.05)


def test_transform_removes_duplicate_ticker_dates() -> None:
    raw_data = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-01-01"]),
            "Ticker": ["AAPL", "AAPL"],
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Adj Close": [101.0, 102.0],
            "Volume": [1000, 1100],
        }
    ).set_index("Date")

    result = transform_stock_data(raw_data)

    assert len(result) == 1
    assert result.iloc[0]["close_price"] == 102.0
