"""HRSA pull: HPSA Designation (monthly cadence) + Provider-to-population ratio (annual cadence).

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

Provider-to-population ratio — the HPSA file above only covers counties with an
active shortage designation (~1,015 of 3,144), so it can't give a ratio for every
county. Full coverage comes from the Area Health Resource Files (AHRF) instead,
confirmed downloadable at:
https://data.hrsa.gov/DataDownload/AHRF/AHRF_2024-2025_CSV.zip
Field names (not opaque codes, despite the technical doc's "field numbers" framing
— those turned out to be page numbers in a printed table of contents) were found
by downloading AHRF_USER_TECH_2024-2025.zip and reading its
"AHRF 2024-2025 Technical Documentation.xlsx", which lists every column's variable
name, source, and vintage. Confirmed fields, both keyed on `fips_st_cnty`:
  - AHRF2025hp.csv: phys_nf_prim_care_pc_exc_rsdt_23 (non-federal primary care
    physicians in patient care, excluding hospital residents and age 75+, 2023)
  - AHRF2025pop.csv: popn_est_23 (population estimate, 2023 — matched to the same
    year as the physician count rather than mixing vintages)
"""
import io
import zipfile

import pandas as pd
import requests

from mmi.config import DATA_PROCESSED

HPSA_URL = "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"
AHRF_URL = "https://data.hrsa.gov/DataDownload/AHRF/AHRF_2024-2025_CSV.zip"
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


def _read_ahrf_csv(zf: zipfile.ZipFile, suffix: str, usecols: list[str]) -> pd.DataFrame:
    name = next(n for n in zf.namelist() if n.lower().endswith(suffix))
    with zf.open(name) as f:
        return pd.read_csv(f, usecols=usecols, dtype={"fips_st_cnty": str})


def fetch_ahrf_provider_ratio() -> pd.DataFrame:
    resp = requests.get(AHRF_URL, timeout=120)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))

    hp = _read_ahrf_csv(zf, "hp.csv", ["fips_st_cnty", "phys_nf_prim_care_pc_exc_rsdt_23"])
    pop = _read_ahrf_csv(zf, "pop.csv", ["fips_st_cnty", "popn_est_23"])

    merged = hp.merge(pop, on="fips_st_cnty").rename(columns={"fips_st_cnty": "fips"})
    physicians = merged["phys_nf_prim_care_pc_exc_rsdt_23"]
    # A ratio is undefined (not infinite/huge) where a county has zero primary
    # care physicians — flag those separately rather than encode as a number.
    merged["primary_care_physicians"] = physicians
    merged["population_per_primary_care_physician"] = (merged["popn_est_23"] / physicians).where(physicians > 0)
    merged["has_zero_primary_care_physicians"] = physicians == 0

    return merged[
        ["fips", "primary_care_physicians", "population_per_primary_care_physician", "has_zero_primary_care_physicians"]
    ].sort_values("fips").reset_index(drop=True)


def main_hpsa():
    """HPSA designations are updated on a rolling basis (no fixed release date),
    unlike AHRF which is genuinely annual — run this on the monthly schedule,
    not bundled with the (much larger, truly-annual) AHRF pull."""
    hpsa = fetch_hpsa_designation()
    hpsa.to_parquet(DATA_PROCESSED / "hrsa_hpsa.parquet", index=False)
    print(f"Wrote {len(hpsa)} designated counties (of 3,144 — absence means 'not designated')")


def main_ahrf():
    ratio = fetch_ahrf_provider_ratio()
    ratio.to_parquet(DATA_PROCESSED / "hrsa_ahrf.parquet", index=False)
    print(f"Wrote {len(ratio)} counties to hrsa_ahrf.parquet")


def main():
    """Runs both pulls — used for local/manual full refreshes. The scheduled
    workflows call main_hpsa/main_ahrf separately on their own cadences."""
    main_hpsa()
    main_ahrf()


if __name__ == "__main__":
    main()
