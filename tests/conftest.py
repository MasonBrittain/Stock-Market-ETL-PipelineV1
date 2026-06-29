"""Shared pytest fixtures for the stock market ETL pipeline test suite."""

from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.database import initialize_schema


@pytest.fixture()
def db_engine() -> Engine:
    """In-memory SQLite engine with the full V2 schema pre-initialised."""
    engine = create_engine("sqlite:///:memory:")
    initialize_schema(engine)
    return engine


@pytest.fixture()
def sample_stock_data() -> pd.DataFrame:
    """Minimal valid transformed DataFrame matching OUTPUT_COLUMNS."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "price_date": pd.to_datetime(
                ["2026-01-02", "2026-01-03", "2026-01-02", "2026-01-03"]
            ),
            "open_price": [150.0, 152.0, 300.0, 298.0],
            "high_price": [155.0, 157.0, 305.0, 303.0],
            "low_price": [149.0, 151.0, 298.0, 296.0],
            "close_price": [153.0, 156.0, 302.0, 299.0],
            "adj_close_price": [153.0, 156.0, 302.0, 299.0],
            "volume": [10_000_000, 11_000_000, 8_000_000, 9_000_000],
            "daily_return": [None, 0.0196, None, -0.0099],
            "loaded_at": pd.Timestamp.now(),
        }
    )
