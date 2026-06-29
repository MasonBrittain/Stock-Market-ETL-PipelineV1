"""Tests for the pipeline_runs audit table."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine

from src.database import pipeline_runs_table, write_audit_row


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _base_audit(batch_id: str, status: str = "SUCCESS") -> dict:
    return {
        "batch_id": batch_id,
        "started_at": _utc_now(),
        "completed_at": _utc_now(),
        "status": status,
        "tickers": "AAPL, MSFT",
        "rows_extracted": 100,
        "rows_inserted": 90,
        "rows_skipped": 10,
        "quality_checks_passed": True,
        "error_message": None,
    }


def test_success_audit_row_is_written(db_engine: Engine) -> None:
    write_audit_row(db_engine, _base_audit("batch-success"))

    with db_engine.connect() as conn:
        rows = conn.execute(
            select(pipeline_runs_table).where(
                pipeline_runs_table.c.batch_id == "batch-success"
            )
        ).fetchall()

    assert len(rows) == 1
    assert rows[0].status == "SUCCESS"
    assert rows[0].rows_inserted == 90
    assert rows[0].error_message is None


def test_failed_audit_row_captures_error_message(db_engine: Engine) -> None:
    audit = _base_audit("batch-fail", status="FAILED")
    audit["quality_checks_passed"] = False
    audit["error_message"] = "Critical quality checks failed: null_tickers"
    write_audit_row(db_engine, audit)

    with db_engine.connect() as conn:
        row = conn.execute(
            select(pipeline_runs_table).where(
                pipeline_runs_table.c.batch_id == "batch-fail"
            )
        ).fetchone()

    assert row is not None
    assert row.status == "FAILED"
    assert "null_tickers" in row.error_message


def test_each_run_produces_a_separate_audit_row(db_engine: Engine) -> None:
    write_audit_row(db_engine, _base_audit("batch-a"))
    write_audit_row(db_engine, _base_audit("batch-b"))

    with db_engine.connect() as conn:
        count = conn.execute(select(pipeline_runs_table)).fetchall()

    assert len(count) == 2
