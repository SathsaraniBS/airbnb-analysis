"""
run_pipeline.py
----------------
Single entry point that runs the full pipeline end-to-end for one city:

    ingest -> profile -> clean -> enrich -> load star schema

Usage:
    python -m src.run_pipeline --city bangkok

Adding a new city requires ONLY adding a CityConfig entry in config.py and
downloading its files into data/ - no changes to this script.
"""

import argparse
import sys
import time

import pandas as pd

from . import config, ingest, cleaning, enrichment, star_schema
from .logging_utils import get_logger

logger = get_logger(__name__)


def run(city_key: str) -> None:
    start = time.time()
    logger.info("=" * 60)
    logger.info("PIPELINE RUN START | city=%s", city_key)
    logger.info("=" * 60)

    if city_key not in config.CITIES:
        logger.error("Unknown city '%s'. Available: %s", city_key, list(config.CITIES))
        sys.exit(1)

    try:
        # ---- Stage 1: Ingestion & Profiling ----
        raw = ingest.load_raw_data(city_key)
        dq_report = ingest.generate_data_quality_report(raw)
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        dq_report.to_csv(config.OUTPUT_DIR / "data_quality_report.csv", index=False)

        # ---- Stage 2: Cleaning & Standardization ----
        cleaned_listings = cleaning.clean_listings_detailed(raw["listings_detailed"])

        # ---- Stage 3: Enrichment & Joining ----
        enriched = enrichment.build_enriched_master_table(cleaned_listings, raw["reviews"])
        enriched.to_parquet(config.OUTPUT_DIR / "listings_enriched.parquet", index=False)

        # ---- Stage 4: Data Modeling (star schema in DuckDB) ----
        star_schema.load_star_schema(enriched)

    except Exception:
        logger.exception("PIPELINE RUN FAILED for city=%s", city_key)
        raise

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info("PIPELINE RUN COMPLETE | city=%s | elapsed=%.1fs", city_key, elapsed)
    logger.info("Outputs written to: %s", config.OUTPUT_DIR)
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Inside Airbnb data pipeline for one city.")
    parser.add_argument("--city", default=config.DEFAULT_CITY,
                         help=f"City key from config.CITIES (default: {config.DEFAULT_CITY})")
    args = parser.parse_args()
    run(args.city)
