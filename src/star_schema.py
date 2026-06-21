"""
star_schema.py
---------------
Section 3.4 - Data Modeling.

Implements a dimensional (star) model in DuckDB:
    dim_host, dim_neighbourhood, dim_room_type  -->  fact_listing

DuckDB was chosen over SQLite/Postgres because it is a single embedded
file (zero setup for whoever reviews this repo), reads parquet/pandas
natively, and is fast enough for analytical (OLAP-style) queries on a
~29k row table without needing a running server process. See the
Decision Log in the report for the full trade-off discussion.
"""

import duckdb
import pandas as pd

from . import config
from .logging_utils import get_logger

logger = get_logger(__name__)


def build_dim_host(enriched: pd.DataFrame) -> pd.DataFrame:
    cols = ["host_id", "host_name", "host_since", "host_tenure_years",
            "host_is_superhost", "host_identity_verified",
            "host_total_listings_count", "host_response_rate"]
    cols = [c for c in cols if c in enriched.columns]
    dim = enriched[cols].drop_duplicates(subset=["host_id"]).reset_index(drop=True)
    logger.info("dim_host: %d unique hosts", len(dim))
    return dim


def build_dim_neighbourhood(enriched: pd.DataFrame) -> pd.DataFrame:
    cols = ["neighbourhood_cleansed", "neighbourhood_group_cleansed",
            "nbhd_median_price", "nbhd_listing_count", "nbhd_avg_review_score"]
    cols = [c for c in cols if c in enriched.columns]
    dim = enriched[cols].drop_duplicates(subset=["neighbourhood_cleansed"]).reset_index(drop=True)
    dim.insert(0, "neighbourhood_id", range(1, len(dim) + 1))
    logger.info("dim_neighbourhood: %d unique neighbourhoods", len(dim))
    return dim


def build_dim_room_type(enriched: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["room_type", "property_type"] if c in enriched.columns]
    dim = enriched[cols].drop_duplicates().reset_index(drop=True)
    dim.insert(0, "room_type_id", range(1, len(dim) + 1))
    logger.info("dim_room_type: %d unique room/property type combinations", len(dim))
    return dim


def build_fact_listing(
    enriched: pd.DataFrame,
    dim_neighbourhood: pd.DataFrame,
    dim_room_type: pd.DataFrame,
) -> pd.DataFrame:
    fact = enriched.merge(
        dim_neighbourhood[["neighbourhood_id", "neighbourhood_cleansed"]],
        on="neighbourhood_cleansed", how="left",
    )
    room_join_cols = [c for c in ["room_type", "property_type"] if c in enriched.columns]
    fact = fact.merge(dim_room_type, on=room_join_cols, how="left")

    fact_cols = [
        "id", "host_id", "neighbourhood_id", "room_type_id",
        "price", "accommodates", "bedrooms", "bathrooms",
        "minimum_nights", "number_of_reviews", "review_scores_rating",
        "availability_365", "price_per_bedroom", "review_frequency_derived",
        "latitude", "longitude", "validation_flags",
    ]
    fact_cols = [c for c in fact_cols if c in fact.columns]
    fact = fact[fact_cols].rename(columns={"id": "listing_id"})
    logger.info("fact_listing: %d rows, %d columns", len(fact), len(fact.columns))
    return fact


def load_star_schema(enriched: pd.DataFrame, db_path=None) -> None:
    """Builds all dim/fact tables and loads them into a DuckDB file,
    overwriting any existing tables of the same name (idempotent run)."""
    db_path = db_path or config.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    dim_host = build_dim_host(enriched)
    dim_neighbourhood = build_dim_neighbourhood(enriched)
    dim_room_type = build_dim_room_type(enriched)
    fact_listing = build_fact_listing(enriched, dim_neighbourhood, dim_room_type)

    con = duckdb.connect(str(db_path))
    con.execute("CREATE OR REPLACE TABLE dim_host AS SELECT * FROM dim_host")
    con.execute("CREATE OR REPLACE TABLE dim_neighbourhood AS SELECT * FROM dim_neighbourhood")
    con.execute("CREATE OR REPLACE TABLE dim_room_type AS SELECT * FROM dim_room_type")
    con.execute("CREATE OR REPLACE TABLE fact_listing AS SELECT * FROM fact_listing")

    # Metadata management layer (Section 3.5): track when this table was built
    con.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_metadata (
            run_timestamp TIMESTAMP, stage VARCHAR, table_name VARCHAR, row_count INTEGER
        )
    """)
    for tbl_name, tbl_df in [("dim_host", dim_host), ("dim_neighbourhood", dim_neighbourhood),
                              ("dim_room_type", dim_room_type), ("fact_listing", fact_listing)]:
        con.execute(
            "INSERT INTO pipeline_metadata VALUES (current_timestamp, 'load_star_schema', ?, ?)",
            [tbl_name, len(tbl_df)],
        )

    con.close()
    logger.info("Star schema loaded into DuckDB at %s", db_path)


EXAMPLE_QUERIES = {
    "avg_price_by_neighbourhood": """
        SELECT n.neighbourhood_cleansed, n.nbhd_listing_count,
               ROUND(AVG(f.price), 2) AS avg_price
        FROM fact_listing f
        JOIN dim_neighbourhood n ON f.neighbourhood_id = n.neighbourhood_id
        GROUP BY 1, 2
        ORDER BY avg_price DESC
        LIMIT 10
    """,
    "superhost_price_premium": """
        SELECT h.host_is_superhost, ROUND(AVG(f.price), 2) AS avg_price,
               COUNT(*) AS n_listings
        FROM fact_listing f
        JOIN dim_host h ON f.host_id = h.host_id
        GROUP BY 1
    """,
    "room_type_distribution": """
        SELECT r.room_type, COUNT(*) AS n_listings,
               ROUND(AVG(f.price), 2) AS avg_price
        FROM fact_listing f
        JOIN dim_room_type r ON f.room_type_id = r.room_type_id
        GROUP BY 1
        ORDER BY n_listings DESC
    """,
}


if __name__ == "__main__":
    enriched = pd.read_parquet(config.OUTPUT_DIR / "listings_enriched.parquet")
    load_star_schema(enriched)

    con = duckdb.connect(str(config.DB_PATH))
    for query_name, sql in EXAMPLE_QUERIES.items():
        logger.info("--- Example query: %s ---", query_name)
        print(con.execute(sql).fetchdf())
    con.close()
