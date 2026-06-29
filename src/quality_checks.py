"""Data quality checks and reporting for the stock market ETL pipeline.

V2 changes:
- Checks are non-fatal by default: all checks run and results are collected.
- Only CRITICAL checks (null tickers, null dates, negative prices) raise ValueError.
- write_quality_report() produces a JSON file in reports/ after every run.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

PRICE_COLUMNS = ["open_price", "high_price", "low_price", "close_price", "adj_close_price"]

# Checks in this set raise ValueError when they fail.
CRITICAL_CHECKS = {"null_tickers", "null_dates", "negative_prices"}

_TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")


# ---------------------------------------------------------------------------
# Individual check functions — each returns a result dict
# ---------------------------------------------------------------------------


def _check_null_tickers(df: pd.DataFrame) -> dict[str, Any]:
    failures = int(
        df["ticker"].isna().sum()
        + df["ticker"].astype(str).str.strip().eq("").sum()
    )
    return {"passed": failures == 0, "failures": failures}


def _check_null_dates(df: pd.DataFrame) -> dict[str, Any]:
    failures = int(df["price_date"].isna().sum())
    return {"passed": failures == 0, "failures": failures}


def _check_negative_prices(df: pd.DataFrame) -> dict[str, Any]:
    bad_cols = [col for col in PRICE_COLUMNS if df[col].lt(0).any()]
    failures = int(sum(df[col].lt(0).sum() for col in bad_cols))
    result: dict[str, Any] = {"passed": not bad_cols, "failures": failures}
    if bad_cols:
        result["columns"] = bad_cols
    return result


def _check_negative_volume(df: pd.DataFrame) -> dict[str, Any]:
    failures = int(df["volume"].lt(0).sum())
    return {"passed": failures == 0, "failures": failures}


def _check_duplicate_rows(df: pd.DataFrame) -> dict[str, Any]:
    failures = int(df.duplicated(subset=["ticker", "price_date"], keep=False).sum())
    return {"passed": failures == 0, "failures": failures}


def _check_price_relationships(df: pd.DataFrame) -> dict[str, Any]:
    """Verify low <= open/close <= high for every row."""
    bad = df[
        (df["low_price"] > df["open_price"])
        | (df["low_price"] > df["close_price"])
        | (df["open_price"] > df["high_price"])
        | (df["close_price"] > df["high_price"])
    ]
    failures = len(bad)
    return {"passed": failures == 0, "failures": failures}


def _check_invalid_ticker_format(df: pd.DataFrame) -> dict[str, Any]:
    # Drop nulls first — null tickers are separately caught by _check_null_tickers.
    non_null = df["ticker"].dropna().astype(str)
    invalid_mask = non_null.apply(lambda t: not bool(_TICKER_PATTERN.match(t)))
    failures = int(invalid_mask.sum())
    result: dict[str, Any] = {"passed": failures == 0, "failures": failures}
    if failures:
        result["examples"] = non_null[invalid_mask].unique()[:5].tolist()
    return result


def _check_date_gaps(df: pd.DataFrame) -> dict[str, Any]:
    """Flag tickers with more than 5 consecutive missing calendar days."""
    details: list[dict[str, Any]] = []
    for ticker, group in df.groupby("ticker"):
        dates = pd.to_datetime(group["price_date"]).sort_values()
        if len(dates) < 2:
            continue
        gaps = dates.diff().dt.days.dropna()
        large_gaps = gaps[gaps > 5]
        for gap_date, gap_size in zip(large_gaps.index, large_gaps.values):
            details.append(
                {
                    "ticker": ticker,
                    "gap_after": str(dates.loc[gap_date - 1] if gap_date > 0 else "N/A"),
                    "gap_calendar_days": int(gap_size),
                }
            )
    return {"passed": len(details) == 0, "details": details}


def _check_column_types(df: pd.DataFrame) -> dict[str, Any]:
    """Warn when volume is stored as float instead of integer-compatible values."""
    issues: list[str] = []
    if pd.api.types.is_float_dtype(df["volume"]):
        non_integer = df["volume"].dropna()
        non_integer = non_integer[non_integer != non_integer.astype("int64", errors="ignore")]
        if len(non_integer) > 0:
            issues.append("volume contains non-integer float values")
    failures = len(issues)
    result: dict[str, Any] = {"passed": failures == 0, "failures": failures}
    if issues:
        result["issues"] = issues
    return result


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def run_quality_checks(stock_data: pd.DataFrame) -> dict[str, Any]:
    """Run all quality checks against the transformed stock data.

    All checks are executed regardless of earlier failures so the report
    captures the full picture. Raises ValueError only when a CRITICAL check
    (null_tickers, null_dates, negative_prices) fails.

    Returns:
        A dict with "checks" (per-check results) and "overall_passed" keys,
        suitable for passing to write_quality_report().
    """
    required_columns = {"ticker", "price_date", "volume", *PRICE_COLUMNS}
    missing = required_columns.difference(stock_data.columns)
    if missing:
        raise ValueError(f"Quality check failed: missing required columns: {', '.join(sorted(missing))}")

    logger.info("Running quality checks on %d rows…", len(stock_data))

    checks: dict[str, Any] = {
        "null_tickers": _check_null_tickers(stock_data),
        "null_dates": _check_null_dates(stock_data),
        "negative_prices": _check_negative_prices(stock_data),
        "negative_volume": _check_negative_volume(stock_data),
        "duplicate_rows": _check_duplicate_rows(stock_data),
        "price_relationships": _check_price_relationships(stock_data),
        "invalid_ticker_format": _check_invalid_ticker_format(stock_data),
        "date_gaps": _check_date_gaps(stock_data),
        "column_types": _check_column_types(stock_data),
    }

    failed_checks = [name for name, result in checks.items() if not result["passed"]]
    overall_passed = len(failed_checks) == 0

    for name in failed_checks:
        severity = "CRITICAL" if name in CRITICAL_CHECKS else "WARNING"
        logger.log(
            logging.ERROR if severity == "CRITICAL" else logging.WARNING,
            "Quality check %s [%s]: %s",
            name,
            severity,
            checks[name],
        )

    if overall_passed:
        logger.info("All quality checks passed")
    else:
        logger.warning(
            "%d quality check(s) failed: %s",
            len(failed_checks),
            ", ".join(failed_checks),
        )

    critical_failures = [c for c in failed_checks if c in CRITICAL_CHECKS]
    if critical_failures:
        raise ValueError(
            f"Critical quality checks failed: {', '.join(critical_failures)}. "
            "Pipeline aborted — see quality report for details."
        )

    return {"checks": checks, "overall_passed": overall_passed}


def write_quality_report(
    quality_results: dict[str, Any],
    batch_id: str,
    reports_dir: Path,
    rows_extracted: int,
    rows_inserted: int,
    rows_skipped: int,
    execution_time_seconds: float,
) -> Path:
    """Write a JSON quality report to reports/quality_report_{batch_id}.json.

    Returns the path to the written file.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "batch_id": batch_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "rows_extracted": rows_extracted,
        "rows_inserted": rows_inserted,
        "rows_skipped": rows_skipped,
        "checks": quality_results.get("checks", {}),
        "overall_passed": quality_results.get("overall_passed", False),
        "execution_time_seconds": round(execution_time_seconds, 3),
    }

    report_path = reports_dir / f"quality_report_{batch_id}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Quality report written → %s", report_path)
    return report_path
