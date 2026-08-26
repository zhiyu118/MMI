"""Census Population Estimates Program (PEP) pull: net migration + birth rate.

Note: post-2020, Census stopped publishing county-level components-of-change
through the api.census.gov REST API and only distributes it as an annual bulk
flat file. Verified live at:
https://www2.census.gov/programs-surveys/popest/datasets/2020-{vintage}/counties/totals/co-est{vintage}-alldata.csv

Birth Rate also lives here rather than in cdc_natality.py: CDC WONDER's own API
documentation states its public API is policy-restricted from returning natality
data grouped or limited by any location field (region/state/county) — a firm
"vital statistics policy for public data sharing" restriction, not a technical
gap. This same PEP file already carries full-coverage, no-suppression county
birth counts (BIRTHS{year}) and a pre-computed crude birth rate per 1,000
(RBIRTH{year}), sourced from the same underlying NCHS vital statistics — so it's
a strictly better fit than fighting CDC WONDER's UI-only access for this project.
"""
import datetime

import pandas as pd
import requests

from mmi.config import DATA_PROCESSED, STATE_FIPS

MAX_LOOKBACK_YEARS = 3  # how far back to probe if the current calendar year's file isn't out yet


def _vintage_url(vintage: int) -> str:
    return (
        f"https://www2.census.gov/programs-surveys/popest/datasets/"
        f"2020-{vintage}/counties/totals/co-est{vintage}-alldata.csv"
    )


def find_latest_vintage() -> int:
    """Probes for the newest published vintage rather than relying on a hardcoded
    year — Census publishes this file in March, so a fixed constant would need
    manual bumping every year right when the new one drops."""
    current_year = datetime.date.today().year
    for vintage in range(current_year, current_year - MAX_LOOKBACK_YEARS, -1):
        if requests.head(_vintage_url(vintage), timeout=15).status_code == 200:
            return vintage
    raise RuntimeError(
        f"No PEP county file found for vintages {current_year - MAX_LOOKBACK_YEARS + 1}-{current_year}"
    )


def fetch(vintage: int | None = None, data_year: int | None = None) -> pd.DataFrame:
    vintage = vintage or find_latest_vintage()
    data_year = data_year or vintage  # most recent year's columns within the vintage file, e.g. NETMIG2025
    url = _vintage_url(vintage)
    df = pd.read_csv(url, encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
    df = df[(df["SUMLEV"] == 50) & (df["STATE"].isin(STATE_FIPS))].copy()
    df["fips"] = df["STATE"] + df["COUNTY"]

    out = pd.DataFrame(
        {
            "fips": df["fips"],
            "pep_data_year": data_year,
            "net_migration": df[f"NETMIG{data_year}"],
            "net_migration_rate_per_1000": df[f"RNETMIG{data_year}"],
            "births": df[f"BIRTHS{data_year}"],
            "birth_rate_per_1000": df[f"RBIRTH{data_year}"],
        }
    )
    return out.sort_values("fips").reset_index(drop=True)


def main():
    df = fetch()
    out_path = DATA_PROCESSED / "pep.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} counties to {out_path}")


if __name__ == "__main__":
    main()
