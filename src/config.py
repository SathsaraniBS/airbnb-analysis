"""
config.py
---------
Central, config-driven settings for the pipeline. Adding a new city only
requires adding a new CityConfig entry -- no other code changes needed.
This satisfies the "configurable, can process any city with minimal code
changes" requirement (Section 3.5 of the assignment).
"""

from dataclasses import dataclass, field
from pathlib import Path

# Project root = two levels up from this file (src/config.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = PROJECT_ROOT / "data" / "processed" / "airbnb.duckdb"


@dataclass
class CityConfig:
    """All file-path and metadata config for a single city's Inside Airbnb data."""
    city_name: str
    data_date: str  # the date the dataset was scraped, e.g. "2025-09-26"
    listings_summary_file: str       # smaller "listings.csv"
    listings_detailed_file: str      # full "listings.csv.gz"
    reviews_file: str
    neighbourhoods_file: str
    calendar_file: str = ""          # optional - may be missing/unusable

    def path(self, filename: str) -> Path:
        return DATA_DIR / filename


# ---- City registry -----------------------------------------------------
# To add another city: add one more CityConfig entry here, point it at the
# matching downloaded files, and pass --city <key> to run_pipeline.py.
CITIES = {
    "bangkok": CityConfig(
        city_name="Bangkok, Thailand",
        data_date="2025-09-26",
        listings_summary_file="listings.csv",
        listings_detailed_file="listings.csv.gz",
        reviews_file="reviews.csv.gz",
        neighbourhoods_file="neighbourhoods.csv",
        calendar_file="calendar.csv.gz",
    ),
}

DEFAULT_CITY = "bangkok"
