"""School Finance Indicators Database (SFID) pull: School Adequacy Rates.

Verified working download (district-level, not county):
https://schoolfinancedata.org/sites/default/files/data/districtcostdatabase_2026.xlsx
(the /media/data/... URL on the site is an HTML landing page, not the file itself —
the real asset lives under /sites/default/files/data/)

Confirmed columns include: year, leaid, district, state_name, stabbr, ppcstot
(per-pupil current spending), predcost (predicted/required per-pupil cost),
fundinggap (ppcstot - predcost — this is the adequacy measure the data dictionary
describes), enroll, plus demographic shares.

NOT YET IMPLEMENTED: aggregating leaid (NCES district ID) up to county FIPS.
Needs the NCES CCD Local Education Agency directory file's county field (or the
NCES EDGE district-county geographic relationship file, which is a shapefile/GIS
join rather than a simple key lookup, since some districts span multiple counties).
Once that crosswalk exists, county adequacy = enrollment-weighted average of
fundinggap across districts whose primary county is that county.
"""
import io

import pandas as pd
import requests

from mmi.config import DATA_PROCESSED

DCD_URL = "https://schoolfinancedata.org/sites/default/files/data/districtcostdatabase_2026.xlsx"


def fetch_district_level() -> pd.DataFrame:
    # Cloudflare 403s both pandas/urllib's default UA and a bare "Mozilla/5.0" UA
    # with no other headers — needs a fuller browser-like header set.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(DCD_URL, headers=headers, timeout=60)
    resp.raise_for_status()
    df = pd.read_excel(io.BytesIO(resp.content), sheet_name="Data")
    latest_year = df["year"].max()
    return df[df["year"] == latest_year][["leaid", "district", "stabbr", "fundinggap", "enroll"]]


def fetch_county_level() -> pd.DataFrame:
    raise NotImplementedError("Needs leaid -> county FIPS crosswalk. See module docstring.")


def main():
    df = fetch_district_level()
    out_path = DATA_PROCESSED / "sfid_district_raw.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} districts (raw, pre-county-aggregation) to {out_path}")


if __name__ == "__main__":
    main()
