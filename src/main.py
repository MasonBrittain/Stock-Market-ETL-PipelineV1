"""Command-line entry point for the stock market ETL pipeline."""

from __future__ import annotations

from src.config import (
    DATABASE_URL,
    INTERVAL,
    PERIOD,
    TICKERS,
    get_database_location,
)
from src.extract import extract_stock_data
from src.load import load_stock_data
from src.quality_checks import run_quality_checks
from src.transform import transform_stock_data


def main() -> None:
    """Run extraction, transformation, validation, and loading."""
    raw_data = extract_stock_data(TICKERS, PERIOD, INTERVAL)
    clean_data = transform_stock_data(raw_data)
    run_quality_checks(clean_data)
    rows_loaded = load_stock_data(clean_data, DATABASE_URL)

    print("ETL pipeline completed successfully.")
    print(f"Tickers processed: {', '.join(TICKERS)}")
    print(f"Rows extracted: {len(clean_data)}")
    print(f"Rows loaded: {rows_loaded}")
    print(f"Database: {get_database_location()}")
    print("Pipeline status: SUCCESS")


if __name__ == "__main__":
    main()
