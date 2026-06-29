"""Tests for the expanded quality checks and JSON report writing."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.quality_checks import run_quality_checks, write_quality_report


def _valid_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "price_date": pd.to_datetime(["2026-01-02", "2026-01-02"]),
            "open_price": [150.0, 300.0],
            "high_price": [155.0, 305.0],
            "low_price": [149.0, 298.0],
            "close_price": [153.0, 302.0],
            "adj_close_price": [153.0, 302.0],
            "volume": [10_000_000, 8_000_000],
        }
    )


def test_valid_data_passes_all_checks() -> None:
    results = run_quality_checks(_valid_data())
    assert results["overall_passed"] is True
    assert all(v["passed"] for k, v in results["checks"].items() if k != "date_gaps")


def test_price_relationship_violation_is_flagged() -> None:
    data = _valid_data()
    # low > close — violates the low <= close <= high rule
    data.loc[0, "low_price"] = 999.0

    results = run_quality_checks(data)

    assert results["overall_passed"] is False
    assert results["checks"]["price_relationships"]["passed"] is False
    assert results["checks"]["price_relationships"]["failures"] >= 1


def test_invalid_ticker_format_is_flagged() -> None:
    data = _valid_data()
    data.loc[0, "ticker"] = "aapl"  # lowercase not valid

    results = run_quality_checks(data)

    assert results["checks"]["invalid_ticker_format"]["passed"] is False


def test_critical_check_raises_on_null_ticker() -> None:
    data = _valid_data()
    data.loc[0, "ticker"] = None

    with pytest.raises(ValueError, match="Critical quality checks failed"):
        run_quality_checks(data)


def test_quality_report_is_written_as_json(tmp_path: Path) -> None:
    results = run_quality_checks(_valid_data())
    report_path = write_quality_report(
        quality_results=results,
        batch_id="test-batch-123",
        reports_dir=tmp_path,
        rows_extracted=2,
        rows_inserted=2,
        rows_skipped=0,
        execution_time_seconds=1.23,
    )

    assert report_path.exists()
    payload = json.loads(report_path.read_text())
    assert payload["batch_id"] == "test-batch-123"
    assert payload["rows_extracted"] == 2
    assert payload["overall_passed"] is True
    assert "checks" in payload
    assert payload["execution_time_seconds"] == pytest.approx(1.23, abs=0.01)


def test_quality_report_filename_contains_batch_id(tmp_path: Path) -> None:
    results = run_quality_checks(_valid_data())
    report_path = write_quality_report(
        quality_results=results,
        batch_id="abc-123",
        reports_dir=tmp_path,
        rows_extracted=2,
        rows_inserted=2,
        rows_skipped=0,
        execution_time_seconds=0.5,
    )
    assert "abc-123" in report_path.name
