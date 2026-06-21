"""
enrichment.py
-------------
Section 3.3 - Data Enrichment & Joining.

Builds the "enriched listing master table": joins cleaned listings with
review summary stats and neighbourhood-level aggregates, and derives
calculated fields (host tenure, review frequency, price-per-bedroom).
"""

import numpy as np
import pandas as pd

from .logging_utils import get_logger

logger = get_logger(__name__)

REFERENCE_DATE = pd.Timestamp("2025-09-26")  # the dataset's scrape date


def summarize_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """Aggregates the raw reviews table down to one row per listing:
    review count and date range. (The detailed listings file already has
    review_scores_rating etc, so we don't recompute those here -- this
    just adds count/recency, which detailed listings doesn't give directly
    derived from the reviews table itself.)"""
    if reviews.empty:
        return pd.DataFrame(columns=["listing_id", "review_count_raw", "first_review_date", "last_review_date"])

    reviews = reviews.copy()
    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    summary = reviews.groupby("listing_id").agg(
        review_count_raw=("id", "count"),
        first_review_date=("date", "min"),
        last_review_date=("date", "max"),
    ).reset_index()
    logger.info("Summarized reviews for %d listings", len(summary))
    return summary


def compute_neighbourhood_aggregates(listings: pd.DataFrame) -> pd.DataFrame:
    """Section 3.3: 'enrich listings with neighbourhood-level aggregates
    (median price, listing density, average rating)'."""
    agg = listings.groupby("neighbourhood_cleansed").agg(
        nbhd_median_price=("price", "median"),
        nbhd_listing_count=("id", "count"),
        nbhd_avg_review_score=("review_scores_rating", "mean"),
    ).reset_index()
    logger.info("Computed neighbourhood aggregates for %d neighbourhoods", len(agg))
    return agg


def derive_calculated_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Section 3.3: 'host tenure, review frequency, price-per-bedroom'."""
    df = df.copy()

    # Host tenure in years (relative to the dataset's scrape date, not
    # today's date - using today's date would make tenure depend on when
    # this pipeline happens to be run, which isn't reproducible).
    if "host_since" in df.columns:
        df["host_tenure_years"] = (
            (REFERENCE_DATE - df["host_since"]).dt.days / 365.25
        ).round(2)

    # Review frequency: reviews per month already exists in the raw file
    # (reviews_per_month) - we keep it but also derive a sanity-checked
    # version from review_count / listing age in months, for comparison.
    if "first_review" in df.columns and "number_of_reviews" in df.columns:
        months_active = ((REFERENCE_DATE - df["first_review"]).dt.days / 30.44).clip(lower=1)
        df["review_frequency_derived"] = (df["number_of_reviews"] / months_active).round(3)

    # Price per bedroom (NaN-safe: 0 bedrooms or missing -> NaN, not inf)
    if "price" in df.columns and "bedrooms" in df.columns:
        safe_bedrooms = df["bedrooms"].replace(0, np.nan)
        df["price_per_bedroom"] = (df["price"] / safe_bedrooms).round(2)

    logger.info("Derived calculated fields: host_tenure_years, "
                "review_frequency_derived, price_per_bedroom")
    return df


def build_enriched_master_table(
    listings: pd.DataFrame,
    reviews: pd.DataFrame,
) -> pd.DataFrame:
    """Orchestrates the full enrichment pipeline and returns one wide,
    analytics-ready table: one row per listing."""
    review_summary = summarize_reviews(reviews)

    enriched = listings.merge(review_summary, left_on="id", right_on="listing_id", how="left")
    enriched = derive_calculated_fields(enriched)

    nbhd_agg = compute_neighbourhood_aggregates(enriched)
    enriched = enriched.merge(nbhd_agg, on="neighbourhood_cleansed", how="left")

    logger.info("Built enriched master table: %d rows, %d columns",
                len(enriched), len(enriched.columns))
    return enriched


if __name__ == "__main__":
    from . import config

    listings = pd.read_parquet(config.OUTPUT_DIR / "listings_cleaned.parquet")
    reviews = pd.read_csv(
        config.DATA_DIR / "reviews.csv.gz", compression="gzip",
        usecols=["listing_id", "id", "date", "reviewer_id"],
    )
    enriched = build_enriched_master_table(listings, reviews)
    enriched.to_parquet(config.OUTPUT_DIR / "listings_enriched.parquet", index=False)
    logger.info("Saved enriched master table to %s",
                config.OUTPUT_DIR / "listings_enriched.parquet")
