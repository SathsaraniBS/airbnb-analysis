"""
ingest.py
---------
Section 3.1 - Data Ingestion & Profiling.

Loads the raw Inside Airbnb files for a given city and produces a data
quality report (row counts, null rates, dtypes, duplicates) BEFORE any
cleaning happens. The point of profiling raw data first is so cleaning
decisions later are evidence-based rather than guesses.
"""

import gzip
import shutil
from pathlib import Path

import pandas as pd

from . import config
from .logging_utils import get_logger, retry

logger = get_logger(__name__)


@retry(max_attempts=3, delay_seconds=1.0)
def _read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Expected data file not found: {path}")
    return pd.read_csv(path, **kwargs)


def load_raw_data(city_key: str) -> dict[str, pd.DataFrame]:
    """Loads every raw file for one city into a dict of DataFrames.
    Missing/unusable optional files (e.g. calendar) are logged and skipped
    rather than crashing the pipeline."""
    cfg = config.CITIES[city_key]
    logger.info("Starting ingestion for city=%s (%s)", city_key, cfg.city_name)

    raw = {}
    raw["listings_summary"] = _read_csv(cfg.path(cfg.listings_summary_file))
    logger.info("Loaded listings_summary: %s rows", len(raw["listings_summary"]))

    raw["listings_detailed"] = _read_csv(
        cfg.path(cfg.listings_detailed_file), compression="gzip", low_memory=False
    )
    logger.info("Loaded listings_detailed: %s rows", len(raw["listings_detailed"]))

    raw["neighbourhoods"] = _read_csv(cfg.path(cfg.neighbourhoods_file))
    logger.info("Loaded neighbourhoods: %s rows", len(raw["neighbourhoods"]))

    # Reviews file is large (500k+ rows) - read only the columns we need
    # to keep memory reasonable.
    try:
        raw["reviews"] = _read_csv(
            cfg.path(cfg.reviews_file),
            compression="gzip",
            usecols=["listing_id", "id", "date", "reviewer_id", "comments"],
        )
        logger.info("Loaded reviews: %s rows", len(raw["reviews"]))
    except Exception as exc:
        logger.warning("Reviews file could not be loaded fully (%s); "
                        "downstream steps will skip review-text features.", exc)
        raw["reviews"] = pd.DataFrame()

    return raw


def profile_dataframe(df: pd.DataFrame, name: str) -> dict:
    """Returns a profiling summary dict for one DataFrame: row/col counts,
    null rate per column, dtype, duplicate row count. This is the
    machine-readable form of the "data quality report" (Section 3.1)."""
    n_rows = len(df)
    null_counts = df.isnull().sum()
    profile = {
        "table": name,
        "n_rows": n_rows,
        "n_cols": len(df.columns),
        "n_duplicate_rows": int(df.duplicated().sum()),
        "columns": [],
    }
    for col in df.columns:
        profile["columns"].append({
            "column": col,
            "dtype": str(df[col].dtype),
            "null_count": int(null_counts[col]),
            "null_pct": round(null_counts[col] / n_rows * 100, 2) if n_rows else 0.0,
            "n_unique": int(df[col].nunique(dropna=True)),
        })
    return profile


def generate_data_quality_report(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Flattens profile_dataframe() output for every table into one tidy
    DataFrame so it can be saved as a single CSV / rendered as a table in
    the report."""
    rows = []
    for name, df in raw.items():
        if df.empty:
            continue
        profile = profile_dataframe(df, name)
        for col_info in profile["columns"]:
            rows.append({
                "table": name,
                "column": col_info["column"],
                "dtype": col_info["dtype"],
                "null_count": col_info["null_count"],
                "null_pct": col_info["null_pct"],
                "n_unique": col_info["n_unique"],
                "table_rows": profile["n_rows"],
                "table_duplicate_rows": profile["n_duplicate_rows"],
            })
    report_df = pd.DataFrame(rows)
    logger.info("Generated data quality report: %d column-level rows", len(report_df))
    return report_df


if __name__ == "__main__":
    raw_data = load_raw_data(config.DEFAULT_CITY)
    dq_report = generate_data_quality_report(raw_data)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.OUTPUT_DIR / "data_quality_report.csv"
    dq_report.to_csv(out_path, index=False)
    logger.info("Saved data quality report to %s", out_path)
