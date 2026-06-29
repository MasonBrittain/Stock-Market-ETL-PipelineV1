"""Tests for incremental loading behaviour."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from sqlalchemy.engine import Engine

from src.database import get_last_stored_dates
from src.load import load_stock_data


def _make_rows(ticker: str, dates: list[str], base_price: float = 100.0) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame(
        {
            "ticker": [ticker] * n,
            "price_date": pd.to_datetime(dates),
            "open_price": [base_price] * n,
            "high_price": [base_price + 2] * n,
            "low_price": [base_price - 1] * n,
            "close_price": [base_price + 1] * n,
            "adj_close_price": [base_price + 1] * n,
            "volume": [1_000_000] * n,
            "daily_return": [None] + [0.01] * (n - 1),
            "loaded_at": pd.Timestamp.now(),
        }
    )


def test_get_last_stored_dates_returns_empty_for_new_db(db_engine: Engine) -> None:
    result = get_last_stored_dates(db_engine, ["AAPL", "MSFT"])
    assert result == {}


def test_get_last_stored_dates_after_initial_load(db_engine: Engine) -> None:
    rows = _make_rows("AAPL", ["2026-01-02", "2026-01-03", "2026-01-05"])
    load_stock_data(rows, db_engine, {"AAPL": 1}, batch_id="test-batch")

    result = get_last_stored_dates(db_engine, ["AAPL"])
    assert "AAPL" in result
    assert result["AAPL"] == date(2026, 1, 5)


def test_second_run_inserts_only_new_rows(db_engine: Engine) -> None:
    first_batch = _make_rows("AAPL", ["2026-01-02", "2026-01-03"])
    inserted_first, _ = load_stock_data(
        first_batch, db_engine, {"AAPL": 1}, batch_id="batch-1"
    )
    assert inserted_first == 2

    # Overlap on 2026-01-03, new row on 2026-01-06
    second_batch = _make_rows("AAPL", ["2026-01-03", "2026-01-06"])
    inserted_second, skipped = load_stock_data(
        second_batch, db_engine, {"AAPL": 1}, batch_id="batch-2"
    )
    assert inserted_second == 1
    assert skipped == 1


def test_rerunning_same_data_inserts_nothing(db_engine: Engine) -> None:
    rows = _make_rows("MSFT", ["2026-01-02", "2026-01-03"])
    load_stock_data(rows, db_engine, {"MSFT": 1}, batch_id="batch-1")

    inserted, skipped = load_stock_data(rows, db_engine, {"MSFT": 1}, batch_id="batch-2")
    assert inserted == 0
    assert skipped == 2
