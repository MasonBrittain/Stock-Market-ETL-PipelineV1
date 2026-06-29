"""Migration script: upgrade a Version 1 database to the Version 2 schema.

Run this once if you have an existing stock_market.db from Version 1.
New installations do not need this script — initialize_schema() creates
the full V2 schema automatically on the first pipeline run.

Usage:
    python scripts/migrate_v1_to_v2.py

The script is idempotent: running it more than once is safe.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

from src.config import DATABASE_URL
from src.database import create_db_engine, initialize_schema

FACT_TABLE = "fact_stock_prices"
NEW_COLUMNS = {
    "company_id": "INTEGER",
    "date_id": "INTEGER",
    "batch_id": "VARCHAR(36)",
}


def _existing_columns(engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    return {col["name"] for col in inspector.get_columns(table_name)}


def migrate() -> None:
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_db_engine(DATABASE_URL)

    # Step 1 — Create new tables (dim_company, dim_date, pipeline_runs)
    # and seed dim_date.  Tables that already exist are left untouched.
    print("Step 1: Creating new tables and seeding dim_date…")
    initialize_schema(engine)
    print("  Done.")

    # Step 2 — Add new columns to fact_stock_prices if they are missing.
    print(f"Step 2: Adding new columns to {FACT_TABLE}…")
    existing = _existing_columns(engine, FACT_TABLE)

    with engine.begin() as conn:
        for col_name, col_type in NEW_COLUMNS.items():
            if col_name not in existing:
                conn.execute(
                    text(f"ALTER TABLE {FACT_TABLE} ADD COLUMN {col_name} {col_type}")
                )
                print(f"  Added column: {col_name} ({col_type})")
            else:
                print(f"  Column already exists, skipping: {col_name}")

    # Step 3 — Back-fill date_id from price_date for existing rows.
    print("Step 3: Back-filling date_id for existing rows…")
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE fact_stock_prices "
                "SET date_id = CAST(STRFTIME('%Y%m%d', price_date) AS INTEGER) "
                "WHERE date_id IS NULL"
            )
        )
    print("  Done.")

    # Step 4 — Populate dim_company with distinct tickers already in the fact table.
    print("Step 4: Populating dim_company from existing tickers…")
    with engine.begin() as conn:
        tickers = [
            row[0]
            for row in conn.execute(
                text("SELECT DISTINCT ticker FROM fact_stock_prices")
            ).fetchall()
        ]

    from src.database import upsert_dim_company

    company_id_map = upsert_dim_company(engine, tickers, {})
    print(f"  Upserted {len(company_id_map)} companies.")

    # Step 5 — Back-fill company_id for existing rows.
    print("Step 5: Back-filling company_id for existing rows…")
    with engine.begin() as conn:
        for ticker, company_id in company_id_map.items():
            conn.execute(
                text(
                    "UPDATE fact_stock_prices "
                    "SET company_id = :company_id "
                    "WHERE ticker = :ticker AND company_id IS NULL"
                ),
                {"company_id": company_id, "ticker": ticker},
            )
    print("  Done.")

    print("\nMigration complete. Your database is now on the V2 schema.")


if __name__ == "__main__":
    migrate()
