"""Tests for dim_date seeding and date attribute correctness."""

from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine

from src.database import dim_date_table


def test_dim_date_is_populated(db_engine: Engine) -> None:
    with db_engine.connect() as conn:
        count = conn.execute(
            select(dim_date_table)
        ).fetchall()
    # 2000-01-01 to 2035-12-31 is 13,149 days
    assert len(count) == 13149


def test_dim_date_known_saturday(db_engine: Engine) -> None:
    # 2026-01-03 is a Saturday
    with db_engine.connect() as conn:
        row = conn.execute(
            select(dim_date_table).where(dim_date_table.c.date_id == 20260103)
        ).fetchone()

    assert row is not None
    assert row.day_name == "Saturday"
    assert row.is_weekend is True
    assert row.day_of_week == 5


def test_dim_date_known_monday(db_engine: Engine) -> None:
    # 2026-01-05 is a Monday
    with db_engine.connect() as conn:
        row = conn.execute(
            select(dim_date_table).where(dim_date_table.c.date_id == 20260105)
        ).fetchone()

    assert row is not None
    assert row.day_name == "Monday"
    assert row.is_weekend is False
    assert row.day_of_week == 0


def test_dim_date_quarter_assignment(db_engine: Engine) -> None:
    with db_engine.connect() as conn:
        q1 = conn.execute(
            select(dim_date_table).where(dim_date_table.c.date_id == 20260101)
        ).fetchone()
        q3 = conn.execute(
            select(dim_date_table).where(dim_date_table.c.date_id == 20260801)
        ).fetchone()

    assert q1 is not None and q1.quarter == 1
    assert q3 is not None and q3.quarter == 3
