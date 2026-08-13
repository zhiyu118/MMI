import os
from pathlib import Path

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

ACS_YEAR = 2023  # latest available 5-year vintage; bump as new releases land
