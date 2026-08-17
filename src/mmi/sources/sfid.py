"""School Finance Indicators Database (SFID) pull: School Adequacy Rates.

Verified working download (district-level, not county):
https://schoolfinancedata.org/sites/default/files/data/districtcostdatabase_2026.xlsx
(the /media/data/... URL on the site is an HTML landing page, not the file itself —
the real asset lives under /sites/default/files/data/)

Confirmed columns include: year, leaid, district, state_name, stabbr, ppcstot
(per-pupil current spending), predcost (predicted/required per-pupil cost),
fundinggap (ppcstot - predcost — this is the adequacy measure the data dictionary
describes), enroll, plus demographic shares.

County-level aggregation uses district_crosswalk.py (NCES EDGE geocode data),
which assigns each district to a single county (its administrative office
location) — the same simplification NCES's own crosswalk makes, even though a
handful of districts technically span county lines. County adequacy is the
enrollment-weighted average of fundinggap across districts in that county, so
large districts dominate the county figure rather than being averaged flat
against tiny ones.
"""
import io

import pandas as pd
import requests

from mmi.config import DATA_PROCESSED
from mmi.district_crosswalk import fetch_crosswalk

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
    district = fetch_district_level().copy()
    district["leaid"] = district["leaid"].astype(str).str.zfill(7)

    crosswalk = fetch_crosswalk()
    merged = district.merge(crosswalk[["leaid", "fips"]], on="leaid", how="inner")
    merged = merged.dropna(subset=["fundinggap", "enroll"])
    merged = merged[merged["enroll"] > 0]

    def weighted_adequacy(g):
        return pd.Series(
            {
                "school_adequacy_rate": (g["fundinggap"] * g["enroll"]).sum() / g["enroll"].sum(),
                "school_adequacy_n_districts": len(g),
                "school_adequacy_total_enroll": g["enroll"].sum(),
            }
        )

    return merged.groupby("fips").apply(weighted_adequacy, include_groups=False).reset_index()


def main():
    df = fetch_county_level()
    out_path = DATA_PROCESSED / "sfid.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} counties to {out_path}")


if __name__ == "__main__":
    main()
