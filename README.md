# 🏠 Bangkok Airbnb Market Intelligence Analysis

**Expernetic (Pvt) Ltd — Data Engineer Intern Technical Assessment**

> Submitted by: **Sanduni Sathsarani** | sbatarenage@gmail.com | [GitHub: SathsaraniBS](https://github.com/SathsaraniBS) | [LinkedIn](https://linkedin.com/in/sanduni-sathsarani-998a74316)
>
> City: Bangkok, Thailand | Dataset: Inside Airbnb (Scrape Date: 26 September 2025)

---

## 📋 Project Overview

A production-quality data engineering pipeline and market intelligence analysis of Bangkok's Airbnb short-term rental market, built on the publicly available [Inside Airbnb](https://insideairbnb.com/) dataset.

**Dataset scale:** 28,806 listings · 50 neighbourhoods · 583,333 reviews · 10.5M calendar rows

---

## 📁 Project Structure

```
airbnb-analysis/
├── data/
│   ├── listings.csv                 # Summary listings (28,806 rows)
│   ├── listings.csv.gz              # Detailed listings (79 columns)
│   ├── reviews.csv.gz               # Guest reviews (583,333 rows)
│   ├── calendar.csv.gz              # Daily availability (10.5M rows)
│   ├── neighbourhoods.csv           # 50 Bangkok neighbourhoods
│   ├── neighbourhoods.geojson       # GeoJSON boundary polygons
│   └── processed/                   # Pipeline outputs (gitignored)
│       ├── data_quality_report.csv
│       ├── listings_enriched.parquet
│       └── airbnb.duckdb
│
├── notebooks/
│   └── 01_data_exploration.ipynb    # EDA + Statistical Analysis + ML
│
├── src/                             # Data Engineering Pipeline
│   ├── __init__.py
│   ├── config.py                    # City registry
│   ├── logging_utils.py             # Shared logger + retry decorator
│   ├── ingest.py                    # Stage 1: Ingest + data quality report
│   ├── cleaning.py                  # Stage 2: Clean + validate
│   ├── enrichment.py                # Stage 3: Enrich + join
│   ├── star_schema.py               # Stage 4: DuckDB star schema
│   └── run_pipeline.py              # Single entry point
│
├── report/
│   └── Bangkok_Airbnb_Analysis_Report.pdf
│
├── logs/                            # Pipeline run logs (gitignored)
├── decision_log.md                  # Engineering Decision Log
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/SathsaraniBS/airbnb-analysis.git
cd airbnb-analysis

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 2. Download Data

Visit [https://insideairbnb.com/get-the-data/](https://insideairbnb.com/get-the-data/), select **Bangkok**, download all files into `data/` folder.

Required: `listings.csv`, `listings.csv.gz`, `reviews.csv.gz`, `calendar.csv.gz`, `neighbourhoods.csv`, `neighbourhoods.geojson`

### 3. Run the Pipeline

```bash
python -m src.run_pipeline --city bangkok
```

Completes in 43 seconds. Outputs written to `data/processed/`.

### 4. Run the Notebook

```bash
jupyter notebook notebooks/01_data_exploration.ipynb
```

---

## 📊 Sections Completed

| Section | Status | What Was Built |
|---|---|---|
| **02 — Dataset Familiarisation** | ✅ Complete | Schema, relationships, data quality, limitations |
| **03 — Data Engineering** | ✅ Complete | 4-stage pipeline + DuckDB star schema |
| **04 — EDA** | ✅ Complete | Price, geographic maps, host, review analysis |
| **05 — Statistical Analysis** | ✅ Complete | H1–H5 with Cohen's d and eta-squared |
| **06 — Data Science / ML** | ✅ Complete | Linear, Random Forest, XGBoost + SHAP |
| 07 — AI / NLP | ⬜ Not attempted | Scoped out |
| 08 — Open Innovation | ⬜ Not attempted | Scoped out |

---

## 📈 Key Findings

| Finding | Result |
|---|---|
| Median listing price | **1,379 THB/night** |
| Top neighbourhood (supply) | **Vadhana** — 4,305 listings |
| Top neighbourhood (price) | **Parthum Wan** — 2,248 THB median |
| Superhost quality signal | **Cohen's d = 0.536** (medium effect) |
| Neighbourhood price variance | **0.2% explained** (ANOVA p=0.44) |
| Best ML model | **XGBoost — MAE=800 THB, R²=0.438** |
| Strongest price predictor | **Bedrooms** (SHAP) |
| Calendar price data | **100% null** — scraping artefact |

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.12 |
| Data Processing | pandas, numpy, pyarrow |
| Database | DuckDB 1.1.3 |
| Visualisation | matplotlib, seaborn, folium |
| Statistics | scipy.stats |
| ML | scikit-learn, XGBoost, SHAP |
| Notebook | JupyterLab |
| Version Control | Git, GitHub |

---

## 📄 Key Documents

- `report/Bangkok_Airbnb_Analysis_Report.pdf` — Full report (19 pages)
- `decision_log.md` — Engineering Decision Log (6 decisions)
- `notebooks/01_data_exploration.ipynb` — Full analysis (76 cells)

---

## ⚠️ Known Limitation

Calendar price data is **100% null** for this Bangkok scrape — documented in `decision_log.md` and Report Section 10.

---

## 👤 Candidate

- **Sanduni Sathsarani** | sbatarenage@gmail.com
- **GitHub:** [SathsaraniBS](https://github.com/SathsaraniBS)
- **Degree:** B.Sc. (Hons) Computer Science — University of Plymouth