# MMI County Dashboard

County-level indicator database and query interface for the MMI project — median
income, housing costs, demographics, employment, healthcare access, and more,
across all 3,144 US counties (50 states + DC).

## Architecture

- **Pull scripts** (`src/mmi/sources/`) — one per data source, each writes a
  Parquet file to `data/processed/`.
- **Assembly** (`src/mmi/build_db.py`) — joins every source's Parquet file into
  one wide county-level table, keyed on 5-digit county FIPS. Any new file dropped
  into `data/processed/` with a `fips` column gets joined in automatically.
- **App** (`app/`) — Streamlit interface: choropleth map + range filter on Home,
  multi-county comparison on County Lookup.
- **Refresh** (`.github/workflows/`) — GitHub Actions run the pull scripts on a
  schedule and commit the updated Parquet files, so the deployed app always reads
  fresh data without a separate database server.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in CENSUS_API_KEY and BLS_API_KEY
```

Run any pull script directly: `PYTHONPATH=src python3 -m mmi.sources.acs`

Run the app locally: `streamlit run app/Home.py`

## Data sources

| Source | Status | Cadence |
|---|---|---|
| Census ACS 5-Year | ✅ working | Annual (Dec) |
| Census Population Estimates (net migration) | ✅ working | Annual |
| BLS LAUS (unemployment) | ✅ working | Monthly |
| HRSA HPSA (shortage designation) | ✅ working | Annual |
| HRSA AHRF (provider ratio) | ⏳ not implemented — see `src/mmi/sources/hrsa.py` | Annual |
| School Finance Indicators DB (adequacy) | ⏳ partial — district-level only, needs county crosswalk, see `src/mmi/sources/sfid.py` | Annual |
| NCES EDFacts (EL enrollment) | ⏳ not implemented — see `src/mmi/sources/nces_el.py` | Annual |
| CDC WONDER (birth rate) | ⏳ not implemented — see `src/mmi/sources/cdc_natality.py` | Annual |
| CNT H+T Index (transportation cost burden) | ⏳ not implemented, needs a CNT account — see `src/mmi/sources/cnt_ht.py` | Irregular |

Dropped from the original scope (no reliable, annually-updated, full-county-coverage
source exists): Job Openings, Unemployed-to-Job-Openings Ratio, Proximity to
Essential Services, Utilization of Public School Facilities.
