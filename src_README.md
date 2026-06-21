# Data Engineering Pipeline — `src/`

This is the Section 3 (Data Engineering) deliverable: a config-driven
pipeline that ingests, profiles, cleans, enriches, and models the Inside
Airbnb data into a DuckDB star schema.

## How to run

```bash
# from the project root (one level above src/)
python -m src.run_pipeline --city bangkok
```

That single command runs all four stages:
1. **Ingest & profile** raw files → `data/processed/data_quality_report.csv`
2. **Clean & standardize** the detailed listings table
3. **Enrich**: join with review summaries + neighbourhood aggregates, derive
   `host_tenure_years`, `review_frequency_derived`, `price_per_bedroom`
4. **Model**: build the star schema and load it into
   `data/processed/airbnb.duckdb`

A timestamped log of the run is written to `logs/pipeline_YYYYMMDD.log`.

## Module map

| File | Section | What it does |
|---|---|---|
| `config.py` | 3.5 | City registry — add a new city by adding one entry here |
| `logging_utils.py` | 3.5 | Shared logger + retry decorator |
| `ingest.py` | 3.1 | Loads raw files, generates the data quality / profiling report |
| `cleaning.py` | 3.2 | Price/date/text standardization, validation flags, duplicate detection |
| `enrichment.py` | 3.3 | Joins listings + reviews + neighbourhood aggregates, derived fields |
| `star_schema.py` | 3.4 | Builds `dim_host`, `dim_neighbourhood`, `dim_room_type`, `fact_listing` in DuckDB |
| `run_pipeline.py` | 3.5 | Single entry point that runs all of the above in order |

## Star schema

```
        dim_host ──┐
                    │
dim_neighbourhood ──┼──> fact_listing
                    │
   dim_room_type ───┘
```

`fact_listing` grain = one row per listing. See `decision_log.md` for why
DuckDB was chosen and other key trade-offs.

## Inspecting the output database

```python
import duckdb
con = duckdb.connect("data/processed/airbnb.duckdb")
con.sql("SELECT * FROM fact_listing LIMIT 5").show()
con.sql("SELECT * FROM pipeline_metadata").show()  # run history
```

## Known limitation

`calendar.csv.gz`'s `price` and `adjusted_price` columns are 100% null for
this city's scrape — calendar-based occupancy/revenue features could not be
built. See `decision_log.md` item 6 and the H5 section of the notebook for
the full investigation.
