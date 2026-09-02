import datetime
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
BLS_API_KEY = os.environ.get("BLS_API_KEY", "")

# 50 states + DC. Territories (PR, GU, VI, AS, MP) excluded — most county-level
# federal sources listed here don't cover them consistently across all indicators.
STATE_FIPS = [
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16",
    "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42",
    "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56",
]

ACS_MAX_LOOKBACK_YEARS = 3


def find_latest_acs_year() -> int:
    """Probes for the newest published ACS 5-Year vintage rather than relying on
    a hardcoded year — a hardcoded ACS_YEAR constant silently went a full vintage
    stale (2023 when 2024 had already been out for months) because nothing
    forced anyone to notice and bump it. Same fix as pep.py's vintage detection."""
    current_year = datetime.date.today().year
    for year in range(current_year, current_year - ACS_MAX_LOOKBACK_YEARS, -1):
        if requests.head(f"https://api.census.gov/data/{year}/acs/acs5/variables.json", timeout=15).status_code == 200:
            return year
    raise RuntimeError(
        f"No ACS 5-Year vintage found for {current_year - ACS_MAX_LOOKBACK_YEARS + 1}-{current_year}"
    )
