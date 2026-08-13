"""BLS LAUS pull: county unemployment rate (monthly).

Series ID format verified against a live API call:
LAUCN + state FIPS (2) + county FIPS (3) + 00000000 + measure code (03 = unemployment rate)
"""
import time

import pandas as pd
import requests

from mmi.config import BLS_API_KEY, DATA_PROCESSED
from mmi.county_fips import fetch_county_universe

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BATCH_SIZE = 50  # max series per request with a registered API key


def _series_id(fips: str) -> str:
    return f"LAUCN{fips}0000000003"


def fetch(start_year: int, end_year: int) -> pd.DataFrame:
    counties = fetch_county_universe()
    series_ids = [_series_id(f) for f in counties["fips"]]
    id_to_fips = {sid: fips for sid, fips in zip(series_ids, counties["fips"])}

    records = []
    for i in range(0, len(series_ids), BATCH_SIZE):
        batch = series_ids[i : i + BATCH_SIZE]
        resp = requests.post(
            BLS_URL,
            json={
                "seriesid": batch,
                "startyear": str(start_year),
                "endyear": str(end_year),
                "registrationkey": BLS_API_KEY,
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload["status"] != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS API error: {payload.get('message')}")

        for series in payload["Results"]["series"]:
            fips = id_to_fips[series["seriesID"]]
            latest = next((pt for pt in series["data"] if pt["value"] != "-"), None)
            if latest is None:
                continue
            records.append(
                {
                    "fips": fips,
                    "unemployment_rate": float(latest["value"]),
                    "unemployment_rate_period": f"{latest['year']}-{latest['period'].lstrip('M')}",
                }
            )
        time.sleep(0.5)  # be polite to the API between batches

    return pd.DataFrame(records).sort_values("fips").reset_index(drop=True)


def main():
    from datetime import date

    end_year = date.today().year
    df = fetch(start_year=end_year - 1, end_year=end_year)
    out_path = DATA_PROCESSED / "bls_laus.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} counties to {out_path}")


if __name__ == "__main__":
    main()
