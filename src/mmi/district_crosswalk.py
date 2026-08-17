"""LEA (school district) -> county FIPS crosswalk, shared by sfid.py and nces_el.py.

Verified working against NCES's ArcGIS REST geocode layer (found by inspecting the
Angular app behind nces.ed.gov/ccd/files.asp's network calls, then the geocode
map service behind the EDGE geocode files referenced in NCES's own documentation):
https://nces.ed.gov/opengis/rest/services/K12_School_Locations/EDGE_GEOCODE_PUBLICLEA_{vintage}/MapServer/0/query

Each LEA is geocoded to a single county (its administrative office location), even
though some districts technically span multiple counties — NCES's own crosswalk
makes this same single-county simplification, so we inherit it rather than invent
a more precise but unsupported alternative.
"""
import pandas as pd
import requests

from mmi.config import DATA_RAW

VINTAGE = "2425"  # 2024-25 school year; matches sfid.py's DCD vintage
QUERY_URL = (
    f"https://nces.ed.gov/opengis/rest/services/K12_School_Locations/"
    f"EDGE_GEOCODE_PUBLICLEA_{VINTAGE}/MapServer/0/query"
)
PAGE_SIZE = 2000  # server's maxRecordCount


def fetch_crosswalk() -> pd.DataFrame:
    rows = []
    offset = 0
    while True:
        resp = requests.get(
            QUERY_URL,
            params={
                "where": "1=1",
                "outFields": "LEAID,CNTY,NMCNTY",
                "returnGeometry": "false",
                "f": "json",
                "resultRecordCount": PAGE_SIZE,
                "resultOffset": offset,
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        features = payload.get("features", [])
        if not features:
            break
        rows.extend(f["attributes"] for f in features)
        if not payload.get("exceededTransferLimit"):
            break
        offset += PAGE_SIZE

    df = pd.DataFrame(rows).rename(columns={"LEAID": "leaid", "CNTY": "fips", "NMCNTY": "county_name"})
    df = df.dropna(subset=["fips"])
    return df.drop_duplicates("leaid").reset_index(drop=True)


def main():
    df = fetch_crosswalk()
    # Lives in data/raw/ (gitignored), not data/processed/ — this is a many-rows-
    # per-county lookup table, not county-level data, so build_db.py must not
    # auto-join it the way it does every file in data/processed/.
    out_path = DATA_RAW / "district_county_crosswalk.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} LEA->county mappings to {out_path}")


if __name__ == "__main__":
    main()
