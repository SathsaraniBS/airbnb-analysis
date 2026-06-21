"""
cleaning.py
-----------
Section 3.2 - Data Cleaning & Standardization.

Every cleaning rule applied here is intentional and documented inline so
the rationale survives in the code itself, not just in the report.
"""

import re
import numpy as np
import pandas as pd

from .logging_utils import get_logger

logger = get_logger(__name__)


def clean_price_column(series: pd.Series) -> pd.Series:
    """Inside Airbnb prices arrive as strings like '$1,595.00'.
    Strips the currency symbol and thousands separator, casts to float.
    Non-parseable / missing values become NaN (explicit null), not 0 -
    a price of 0 would be indistinguishable from a free listing."""
    cleaned = (
        series.astype(str)
        .str.replace(r"[\$,]", "", regex=True)
        .replace("nan", np.nan)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def clean_bathrooms_text(series: pd.Series) -> pd.Series:
    """Extracts a numeric bathroom count from free text like '1.5 baths'
    or 'Half-bath' (treated as 0.5)."""
    def parse(val):
        if pd.isna(val):
            return np.nan
        val = str(val).lower()
        if "half" in val:
            return 0.5
        match = re.search(r"(\d+\.?\d*)", val)
        return float(match.group(1)) if match else np.nan

    return series.apply(parse)


def standardize_dates(df: pd.DataFrame, date_columns: list[str]) -> pd.DataFrame:
    """Parses all known date columns to pandas datetime, coercing
    unparseable values to NaT rather than raising."""
    df = df.copy()
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def validate_listing_row(df: pd.DataFrame) -> pd.DataFrame:
    """Applies domain validation rules (Section 3.1) and flags - not
    silently drops - rows that fail them, so nothing is lost without a
    trace. A `validation_flags` column records every rule a row broke."""
    df = df.copy()
    flags = pd.Series([""] * len(df), index=df.index)

    if "price" in df.columns:
        bad_price = df["price"].notna() & (df["price"] <= 0)
        flags = flags.where(~bad_price, flags + "negative_or_zero_price;")

    if "latitude" in df.columns and "longitude" in df.columns:
        bad_lat = ~df["latitude"].between(-90, 90)
        bad_lon = ~df["longitude"].between(-180, 180)
        flags = flags.where(~bad_lat, flags + "invalid_latitude;")
        flags = flags.where(~bad_lon, flags + "invalid_longitude;")

    if "minimum_nights" in df.columns:
        bad_min_nights = df["minimum_nights"].notna() & (df["minimum_nights"] <= 0)
        flags = flags.where(~bad_min_nights, flags + "invalid_minimum_nights;")

    df["validation_flags"] = flags
    n_flagged = (flags != "").sum()
    logger.info("Validation: %d / %d rows flagged (not dropped) for review",
                n_flagged, len(df))
    return df


def detect_duplicate_listings(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic duplicate check on listing id (should be unique).
    A fuzzy check on (name, host_id, latitude, longitude) catches the
    rarer case of a listing re-posted under a new id."""
    df = df.copy()
    df["is_id_duplicate"] = df.duplicated(subset=["id"], keep=False)

    fuzzy_cols = [c for c in ["name", "host_id", "latitude", "longitude"] if c in df.columns]
    df["is_fuzzy_duplicate"] = df.duplicated(subset=fuzzy_cols, keep=False) if fuzzy_cols else False

    n_id_dupes = df["is_id_duplicate"].sum()
    n_fuzzy_dupes = df["is_fuzzy_duplicate"].sum()
    logger.info("Duplicate check: %d exact id duplicates, %d fuzzy (name+host+geo) duplicates",
                n_id_dupes, n_fuzzy_dupes)
    return df


def clean_listings_detailed(df: pd.DataFrame) -> pd.DataFrame:
    """Main entry point: applies all cleaning steps to the detailed
    listings table in sequence and returns an analytics-ready DataFrame."""
    df = df.copy()
    logger.info("Cleaning listings_detailed: %d rows in", len(df))

    df["price"] = clean_price_column(df["price"])
    if "bathrooms_text" in df.columns and df["bathrooms"].isna().all():
        df["bathrooms"] = clean_bathrooms_text(df["bathrooms_text"])

    df = standardize_dates(df, ["host_since", "first_review", "last_review", "last_scraped"])

    # Normalize categorical text fields: trim whitespace, consistent casing
    for col in ["room_type", "property_type", "neighbourhood_cleansed"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # host_is_superhost / host_identity_verified arrive as 't'/'f' strings
    for col in ["host_is_superhost", "host_identity_verified", "instant_bookable"]:
        if col in df.columns:
            df[col] = df[col].map({"t": True, "f": False})

    df = validate_listing_row(df)
    df = detect_duplicate_listings(df)

    logger.info("Cleaning listings_detailed: %d rows out (no rows dropped, "
                "issues flagged in validation_flags column)", len(df))
    return df


if __name__ == "__main__":
    import pandas as pd
    from . import config

    raw = pd.read_csv(config.DATA_DIR / "listings.csv.gz", compression="gzip", low_memory=False)
    cleaned = clean_listings_detailed(raw)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cleaned.to_parquet(config.OUTPUT_DIR / "listings_cleaned.parquet", index=False)
    logger.info("Saved cleaned listings to %s", config.OUTPUT_DIR / "listings_cleaned.parquet")
