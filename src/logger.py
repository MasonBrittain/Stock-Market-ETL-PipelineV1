"""Shared logging configuration for the stock market ETL pipeline.

Call configure_logging() once at the start of main() before importing
any other pipeline modules so every logger inherits the same handlers.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | batch=%(batch_id)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_configured = False


class _BatchIdFilter(logging.Filter):
    """Injects batch_id into every LogRecord so it appears in every line."""

    def __init__(self, batch_id: str) -> None:
        super().__init__()
        self.batch_id = batch_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.batch_id = self.batch_id  # type: ignore[attr-defined]
        return True


def configure_logging(batch_id: str, log_dir: Path, log_level: str = "INFO") -> None:
    """Set up the root logger with a rotating file handler and a console handler.

    Safe to call multiple times — only configures on the first call.
    """
    global _configured
    if _configured:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pipeline.log"

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    batch_filter = _BatchIdFilter(batch_id)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(batch_filter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(batch_filter)

    root = logging.getLogger()
    root.setLevel(log_level.upper())
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configured = True
