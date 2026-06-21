"""
logging_utils.py
-----------------
Shared logger + a simple retry decorator. Used across all pipeline stages
so every run produces a timestamped log file under logs/, in addition to
console output. Satisfies the "logging, error handling, retry logic"
requirement (Section 3.5).
"""

import logging
import time
import functools
from datetime import datetime
from pathlib import Path

from . import config


def get_logger(name: str) -> logging.Logger:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOG_DIR / f"pipeline_{datetime.now():%Y%m%d}.log"

    logger = logging.getLogger(name)
    if logger.handlers:  # avoid duplicate handlers if called multiple times
        return logger

    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def retry(max_attempts: int = 3, delay_seconds: float = 2.0):
    """Decorator: retries a function on exception, with linear backoff.
    Used for steps that touch the filesystem/network (e.g. file reads)
    where a transient failure shouldn't kill the whole pipeline run."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - intentional broad catch here
                    last_exc = exc
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s",
                        attempt, max_attempts, func.__name__, exc,
                    )
                    if attempt < max_attempts:
                        time.sleep(delay_seconds * attempt)
            logger.error("All %d attempts failed for %s", max_attempts, func.__name__)
            raise last_exc

        return wrapper

    return decorator
