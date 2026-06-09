"""Configuration values for the stock market ETL pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

TICKERS = [
    ticker.strip().upper()
    for ticker in os.getenv("TICKERS", "AAPL,MSFT,NVDA,GOOGL,AMZN").split(",")
    if ticker.strip()
]
PERIOD = os.getenv("PERIOD", "6mo")
INTERVAL = os.getenv("INTERVAL", "1d")

DATABASE_PATH = PROJECT_ROOT / "data" / "stock_market.db"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATABASE_PATH.as_posix()}",
)


def get_database_location() -> str:
    """Return a readable database location for pipeline logging."""
    if DATABASE_URL.startswith("sqlite:///"):
        database_value = DATABASE_URL.removeprefix("sqlite:///")
        database_path = Path(database_value)
        if database_path.is_absolute():
            try:
                return str(database_path.relative_to(PROJECT_ROOT))
            except ValueError:
                return str(database_path)
        return str(database_path)
    return DATABASE_URL
