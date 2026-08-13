"""Canonical county universe (FIPS + name), used as the join key every source aligns to."""
import pandas as pd
import requests

from mmi.config import ACS_YEAR, CENSUS_API_KEY, STATE_FIPS


def fetch_county_universe(year: int = ACS_YEAR) -> pd.DataFrame:
    """All counties in the 50 states + DC, from the ACS 5-Year geography list.

    Returns columns: fips (5-digit state+county), state_fips, county_fips, county_name.
    """
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    resp = requests.get(
        url,
        params={"get": "NAME", "for": "county:*", "in": "state:*", "key": CENSUS_API_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df[df["state"].isin(STATE_FIPS)].copy()
    df["fips"] = df["state"] + df["county"]
    df = df.rename(columns={"state": "state_fips", "county": "county_fips", "NAME": "county_name"})
    return df[["fips", "state_fips", "county_fips", "county_name"]].sort_values("fips").reset_index(drop=True)
