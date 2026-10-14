# MMI Dashboard

County-level indicator database and query interface for the MMI project — median
income, housing costs, demographics, employment, healthcare access, and more,
across all 3,144 US counties (50 states + DC).

## Architecture

- **Pull scripts** (`src/mmi/sources/`) — one per data source, each writes a
  Parquet file to `data/processed/`.
- **Assembly** (`src/mmi/build_db.py`) — joins every source's Parquet file into
  one wide county-level table, keyed on 5-digit county FIPS. Any new file dropped
  into `data/processed/` with a `fips` column gets joined in automatically.
- **App** (`app/`) — Streamlit interface, 5 pages: **MMI Dashboard** (main
  page — multi-variable filter panel with a state dropdown and per-variable
  min/max bounds, choropleth map, full county table), **Michigan Dashboard**
  (the same idea for Michigan cities and townships — see below),
  **Qualified Counties** (fixed-threshold screener with toggleable criteria),
  **County Lookup** (multi-county side-by-side comparison), **Data Sources**
  (reference table of every variable's source and update cadence).
- **Refresh** (`.github/workflows/`) — GitHub Actions run the pull scripts on a
  schedule and commit the updated Parquet files, so the deployed app always reads
  fresh data without a separate database server. `refresh-monthly.yml` runs on
  the 5th of each month (BLS unemployment); `refresh-annual.yml` runs Dec 15
  (timed for ACS's December release) and Mar 15 (timed for Census PEP's and
  SFID's Feb–March releases) — see the per-source cadence table below for
  which sources land in which run.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in CENSUS_API_KEY and BLS_API_KEY
```

Run any pull script directly: `PYTHONPATH=src python3 -m mmi.sources.acs`

Run the app locally: `streamlit run app/MMI_Dashboard.py`

## Michigan dashboard (cities and townships)

A second dashboard covers Michigan below the county level: the **280
incorporated cities** (ACS place geography) plus the **1,240 townships and
charter townships** (ACS county-subdivision geography). Cities and townships
don't overlap and together cover every resident once; villages and
census-designated places sit inside townships, so they're left out rather than
double-counted. Cities come from the place geography because the
county-subdivision one splits cities that cross county lines into one row per
county part.

| Indicator | Source | Coverage |
|---|---|---|
| Income, rent, home value ratios, age, 65+, foreign-born, vacancy, population | Census ACS 5-Year (same table codes and formulas as the county dashboard — `derive_indicators` in `src/mmi/sources/acs.py` is shared) | All cities and townships |
| Income margin of error (% of estimate) | ACS `B19013_001M` | All; used for the "hide low-precision" toggle |
| Unemployment rate | BLS LAUS, series built from Census codes (`LAUCT…` cities, `LAUCS…` townships) | Only areas BLS covers — cities and townships of 25,000+ |
| Transportation cost burden | CNT H+T Index, place-level file | Cities only — CNT has no township geography |

County-only indicators (HPSA, primary care physician ratio, birth rate, net
migration, school adequacy) are intentionally not shown.

Code: `src/mmi/michigan.py`. Output: `data/processed/michigan/*.parquet` (a
subfolder on purpose, so `build_db.py` doesn't try to join it into the county
table). Annual refresh pulls ACS and CNT, the monthly refresh pulls BLS.
Boundaries are a static reference file, `data/reference/mi_boundaries.geojson`,
built from Census TIGERweb generalized boundaries; rebuild it by hand when a
new ACS vintage changes geography:

```bash
PYTHONPATH=src python3 -c "from mmi import michigan; michigan.main_boundaries()"
```

## Data sources

| Source | Status | Cadence |
|---|---|---|
| Census ACS 5-Year (income, rent, home value, age, foreign-born, vacancy) | ✅ working | Annual (Dec) |
| Census Population Estimates (net migration) | ✅ working | Annual (March, per Census's official PEP release schedule — the county-level file releases later than the December national/state one) |
| Census Population Estimates (birth rate) | ✅ working — see note below on why this replaced CDC WONDER | Annual (March, same file/schedule as net migration) |
| BLS LAUS (unemployment) | ✅ working | Monthly |
| HRSA HPSA (shortage designation) | ✅ working | Monthly (moved off the annual schedule — designations drifted ~1% of counties in 3 weeks, too fast for a twice-yearly sweep) |
| HRSA AHRF (primary care provider ratio) | ✅ working | Annual |
| School Finance Indicators DB (adequacy) | ✅ working — district-level data enrollment-weighted up to county via `src/mmi/district_crosswalk.py` | Annual (February–March, based on the last two editions' release dates) |
| CNT H+T Index (transportation cost burden) | ✅ working — fully automated, no account needed (see note below) | Irregular — CNT's current release is still 2022 |

**Birth Rate** comes from the Census PEP file (`src/mmi/sources/pep.py`), not CDC
WONDER — CDC WONDER's own API documentation states its public API is policy-blocked
from returning natality data grouped or filtered by any location field (state or
county), so no XML query could ever get county-level results from it. `pep.py`'s
existing county-level file already carries full-coverage birth counts and a crude
birth rate sourced from the same underlying NCHS vital statistics.

**CNT H+T Index** looks account-gated on the site, but its "All Counties" national
download (`download.php?data_yr=2022&focus=county` on htaindex.cnt.org, found by
reading the download page's own JS) is a plain unauthenticated file — no login
step needed in the pipeline at all.

Dropped from the original scope (no reliable, annually-updated, full-county-coverage
source exists): Job Openings, Unemployed-to-Job-Openings Ratio, Proximity to
Essential Services, Utilization of Public School Facilities.

Also dropped: **EL Program Enrollment Count** and **English Learner Population as
% of Total Population**. The administrative source (EDFacts's Title III/LEP data)
turned out to be unreachable — it's not part of CCD, and both paths to it found
(`www2.ed.gov`'s old bulk-file index, `eddataexpress.ed.gov`) are gone or bot-gated.
ACS's language-proficiency tables (`B16004`) were considered as a substitute but
rejected: "speaks English less than very well" is a self-reported survey answer,
not the same thing as being administratively identified and enrolled in EL
services — different population, different threshold, no reclassification when a
student exits the program. Shipping it under an "EL" label would misrepresent
what's actually being measured, so it's dropped rather than approximated.
