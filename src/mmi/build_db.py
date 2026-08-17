"""Joins every source's Parquet file into one county-level table, keyed on fips.

Generic by design: any new file dropped into data/processed/ with a 'fips' column
gets joined in automatically, so adding a new source later needs no changes here.
"""
import duckdb
import pandas as pd

from mmi.config import DATA_PROCESSED

BASE_SOURCE = "acs.parquet"  # has full 3,144-county coverage; anchors the join


def load_county_master(base_source: str = BASE_SOURCE) -> pd.DataFrame:
    parquet_files = sorted(DATA_PROCESSED.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {DATA_PROCESSED} — run the pull scripts first")

    base_path = DATA_PROCESSED / base_source
    master = pd.read_parquet(base_path).copy()

    for path in parquet_files:
        if path.name == base_source:
            continue
        df = pd.read_parquet(path)
        if "fips" not in df.columns:
            continue
        cols = [c for c in df.columns if c != "county_name"]
        master = master.merge(df[cols], on="fips", how="left")

    return master.sort_values("fips").reset_index(drop=True)


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    master = load_county_master()
    con = duckdb.connect(database=":memory:")
    con.register("county_master", master)
    return con


def main():
    master = load_county_master()
    print(f"{len(master)} counties, {len(master.columns)} columns:")
    for col in master.columns:
        non_null = master[col].notna().sum()
        print(f"  {col}: {non_null}/{len(master)} non-null")


if __name__ == "__main__":
    main()
