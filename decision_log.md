# Engineering Decision Log

This log documents the significant engineering decisions made while building
the `src/` data pipeline, as required by Section 3 of the assignment brief.

---

## 1. Tool choice: DuckDB over SQLite / PostgreSQL

**Options considered:** SQLite, PostgreSQL, DuckDB.

**Decision:** DuckDB.

**Why:** The dataset is ~29k listings / ~580k reviews — fully analytical
(OLAP-style aggregations: GROUP BY neighbourhood, AVG price, etc.), not
transactional. DuckDB is column-oriented and built for exactly this query
pattern, while SQLite is row-oriented and PostgreSQL requires a running
server process that whoever reviews this repo would need to install and
configure. DuckDB ships as a single embedded `.duckdb` file with zero setup.

**Trade-off accepted:** DuckDB has a smaller ecosystem/community than
PostgreSQL and isn't suitable for a multi-user production write workload.
For this assignment's single-analyst, read-heavy use case that trade-off
is acceptable.

---

## 2. Flag-and-keep, not drop, for validation failures

**Options considered:** (a) drop any row failing a validation rule
(negative price, invalid lat/long, etc.), (b) flag rows in a new column
and keep all of them.

**Decision:** (b) — added a `validation_flags` column.

**Why:** Silently dropping rows destroys information and makes the
pipeline's behavior invisible to anyone re-running it. Keeping all rows
with an explicit flag lets downstream analysis (or a human reviewer)
decide whether to exclude flagged rows per-analysis, and the flag count is
itself a useful data-quality metric to report.

**Trade-off accepted:** Slightly more complex downstream filtering
(`WHERE validation_flags = ''` instead of assuming the table is already
clean) — judged worth it for traceability.

---

## 3. Reviews loaded with `usecols`, not all columns

**Options considered:** Load the full `reviews.csv.gz` (which includes the
full comment text for 580k+ rows), or load only the columns the pipeline
actually needs (`listing_id`, `id`, `date`, `reviewer_id`).

**Decision:** Restrict to the needed columns at read time.

**Why:** The full reviews file is ~75MB compressed and review text isn't
used anywhere in the engineering/EDA/statistics sections — only count and
date are needed for the enrichment join. Reading only 4 columns instead of
6 noticeably reduces memory and load time, which matters when iterating
repeatedly during development under a tight deadline.

**Trade-off accepted:** If a future NLP section needs review text, the
ingestion call will need `usecols` widened — this is a 1-line change,
documented here for that future reader.

---

## 4. Host tenure computed relative to the dataset's scrape date, not "today"

**Options considered:** `host_tenure_years = (today - host_since)`, or
`host_tenure_years = (scrape_date - host_since)`.

**Decision:** Used the dataset's documented scrape date (2025-09-26) as
the reference point.

**Why:** Using `today`'s date would make the computed tenure value silently
change every time the pipeline is re-run on a different day, breaking
reproducibility — running the pipeline today vs. next week would give two
different "correct" answers for the same row. Anchoring to the scrape date
makes the output deterministic and matches what the data actually
describes (host tenure *as of the scrape*, not as of right now).

**Trade-off accepted:** The reference date is currently hardcoded as a
constant in `enrichment.py`; for true multi-city support it should be
pulled from `CityConfig.data_date` per city (noted as a future improvement).

---

## 5. Config-driven city registry instead of hardcoded paths

**Options considered:** Hardcode "bangkok" file paths directly in the
ingestion script, or define a `CityConfig` dataclass + registry dict.

**Decision:** `CityConfig` + `CITIES` registry in `config.py`.

**Why:** Section 3.5 explicitly requires the pipeline to "process any city
with minimal code changes." With a registry, adding a second city is one
new dict entry — every other module (`ingest`, `cleaning`, `enrichment`,
`star_schema`) is already city-agnostic and reads the active config object.

**Trade-off accepted:** Slight upfront complexity (a dataclass instead of
plain constants) for a single-city run — accepted because it costs nothing
extra to run for one city and avoids a rewrite if more cities are added later.

---

## 6. No calendar-based features (price/availability forecasting) implemented

**Options considered:** Build calendar-based features anyway using
`adjusted_price`, or skip calendar-derived features and document why.

**Decision:** Skipped. Documented as a confirmed data limitation (see H5 in
the notebook): `price` and `adjusted_price` in `calendar.csv.gz` are 100%
null across all 10.5M rows for this city's scrape.

**Why:** Building features on a 100% null column would either produce
all-NaN output (useless) or require fabricating values, which would be
scientifically dishonest. The assignment brief explicitly asks candidates
to identify and document "coverage gaps, scraping artifacts" rather than
work around them silently.

**Trade-off accepted:** Section 3.3's "integrate calendar data to compute
occupancy/revenue estimates" bullet is therefore not completed for this
city. This is disclosed in the Incomplete Work Summary.
