"""HRSA pull: HPSA Designation (implemented) + Provider-to-population ratio (TODO).

HPSA Designation — verified working against a live download:
https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv
Filtered to active ("Designated" status), geographic-level Primary Care HPSAs
(HPSA Type Code in {"Hpsa Geo", "Hpsa Geo HN"}) — this excludes population-specific
(low-income, migrant, etc.) and facility-based (RHC/FQHC/ITU/PRSN) designations,
which describe the same underlying shortage but aren't a whole-county property.
About 1,015 of 3,144 counties currently have an active geographic HPSA; counties
with none are genuinely "not designated," not missing data.

Where a county has multiple overlapping sub-county HPSA records (common in large
urban counties, e.g. Milwaukee County WI has 116), we take the single most severe
record by HPSA Score, since "HPSA Designation" is meant to describe the county's
worst documented shortage, not an average across areas of very different size.

Provider-to-population ratio — NOT YET IMPLEMENTED. The HPSA file above only
covers counties with an active shortage designation (~1,015 of 3,144), so it can't
give a ratio for every county as required. Full county coverage needs the Area
Health Resource Files (AHRF) instead, which has raw physician counts + population
for all counties — confirmed downloadable at:
https://data.hrsa.gov/DataDownload/AHRF/AHRF_2024-2025_CSV.zip
But AHRF's ~40MB main file uses opaque numeric field codes (e.g. "F1234_25") that
need to be mapped via the technical documentation zip (AHRF_USER_TECH_2024-2025.zip)
to find the current-year "active primary care physicians" and "population" fields
before this can be built.
"""
import io
import zipfile

import pandas as pd
import requests

from mmi.config import DATA_PROCESSED

HPSA_URL = "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"
GEO_TYPE_CODES = {"Hpsa Geo", "Hpsa Geo HN"}


def fetch_hpsa_designation() -> pd.DataFrame:
    df = pd.read_csv(HPSA_URL, low_memory=False)
    geo = df[
        (df["HPSA Discipline Class"] == "Primary Care")
        & (df["HPSA Status"] == "Designated")
        & (df["HPSA Type Code"].isin(GEO_TYPE_CODES))
    ].copy()

    geo["fips"] = geo["State and County Federal Information Processing Standard Code"].astype(str).str.zfill(5)
    geo["is_high_needs"] = geo["HPSA Type Code"] == "Hpsa Geo HN"

    # Keep the most severe record (highest HPSA Score) per county.
    geo = geo.sort_values("HPSA Score", ascending=False).drop_duplicates("fips", keep="first")

    return geo[["fips", "HPSA Score", "is_high_needs", "HPSA Degree of Shortage"]].rename(
        columns={"HPSA Score": "hpsa_score", "HPSA Degree of Shortage": "hpsa_degree_of_shortage"}
    ).sort_values("fips").reset_index(drop=True)


def fetch_ahrf_provider_ratio() -> pd.DataFrame:
    raise NotImplementedError(
        "Needs AHRF technical documentation to map field codes for primary care "
        "physician counts and population. See module docstring."
    )


def main():
    hpsa = fetch_hpsa_designation()
    out_path = DATA_PROCESSED / "hrsa_hpsa.parquet"
    hpsa.to_parquet(out_path, index=False)
    print(f"Wrote {len(hpsa)} designated counties to {out_path} (of 3,144 total — absence means 'not designated')")


if __name__ == "__main__":
    main()
