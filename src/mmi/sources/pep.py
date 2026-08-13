"""Census Population Estimates Program (PEP) pull: net migration.

Note: post-2020, Census stopped publishing county-level components-of-change
through the api.census.gov REST API and only distributes it as an annual bulk
flat file. Verified live at:
https://www2.census.gov/programs-surveys/popest/datasets/2020-{vintage}/counties/totals/co-est{vintage}-alldata.csv
"""
import pandas as pd

from mmi.config import DATA_PROCESSED, STATE_FIPS

VINTAGE = 2025  # bump each year when Census publishes a new co-est{vintage}-alldata.csv
DATA_YEAR = VINTAGE  # most recent year's columns within the vintage file, e.g. NETMIG2025


def fetch(vintage: int = VINTAGE, data_year: int = DATA_YEAR) -> pd.DataFrame:
    url = (
        f"https://www2.census.gov/programs-surveys/popest/datasets/"
        f"2020-{vintage}/counties/totals/co-est{vintage}-alldata.csv"
    )
    df = pd.read_csv(url, encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
    df = df[(df["SUMLEV"] == 50) & (df["STATE"].isin(STATE_FIPS))].copy()
    df["fips"] = df["STATE"] + df["COUNTY"]

    out = pd.DataFrame(
        {
            "fips": df["fips"],
            "pep_data_year": data_year,
            "net_migration": df[f"NETMIG{data_year}"],
            "net_migration_rate_per_1000": df[f"RNETMIG{data_year}"],
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
