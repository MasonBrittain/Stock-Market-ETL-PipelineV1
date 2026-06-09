"""Load transformed stock price data into SQLite with duplicate prevention."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.engine import Engine

TABLE_NAME = "fact_stock_prices"


def _create_stock_prices_table(engine: Engine) -> Table:
    """Create the target table when it does not already exist."""
    metadata = MetaData()
    table = Table(
        TABLE_NAME,
        metadata,
        Column("ticker", String(10), nullable=False),
        Column("price_date", DateTime, nullable=False),
        Column("open_price", Float),
        Column("high_price", Float),
        Column("low_price", Float),
        Column("close_price", Float),
        Column("adj_close_price", Float),
        Column("volume", BigInteger),
        Column("daily_return", Float),
        Column("loaded_at", DateTime, nullable=False),
        UniqueConstraint("ticker", "price_date", name="uq_stock_ticker_price_date"),
    )
    metadata.create_all(engine)
    return table


def _existing_keys(engine: Engine, table: Table, tickers: list[str]) -> set[tuple[str, pd.Timestamp]]:
    """Read existing ticker/date keys for the current batch."""
    if not tickers:
        return set()

    query = select(table.c.ticker, table.c.price_date).where(
        table.c.ticker.in_(tickers)
    )
    existing = pd.read_sql(query, engine)
    if existing.empty:
        return set()

    existing["price_date"] = pd.to_datetime(existing["price_date"]).dt.normalize()
    return set(existing.itertuples(index=False, name=None))


def load_stock_data(stock_data: pd.DataFrame, database_url: str) -> int:
    """Append only new ticker/date records and return the inserted row count."""
    if stock_data.empty:
        return 0

    engine = create_engine(database_url)
    try:
        table = _create_stock_prices_table(engine)
        rows_to_load = stock_data.copy()
        rows_to_load["price_date"] = pd.to_datetime(
            rows_to_load["price_date"]
        ).dt.normalize()
        rows_to_load = rows_to_load.drop_duplicates(
            subset=["ticker", "price_date"], keep="last"
        )

        existing = _existing_keys(
            engine,
            table,
            rows_to_load["ticker"].dropna().unique().tolist(),
        )
        is_new = [
            (row.ticker, row.price_date) not in existing
            for row in rows_to_load[["ticker", "price_date"]].itertuples(index=False)
        ]
        rows_to_load = rows_to_load.loc[is_new]

        if rows_to_load.empty:
            return 0

        rows_to_load.to_sql(
            TABLE_NAME,
            engine,
            if_exists="append",
            index=False,
            method="multi",
        )
        return len(rows_to_load)
    finally:
        engine.dispose()
