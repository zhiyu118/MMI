"""Michigan cities + townships: ACS indicators, BLS LAUS unemployment, CNT transportation cost burden.

Geography: the 280 incorporated cities (ACS "place" geography) plus the 1,240
townships and charter townships (ACS "county subdivision" geography). Cities and
townships don't overlap and together cover every Michigan resident exactly once;
villages and CDPs sit inside townships, so they're left out rather than
double-counted.

Cities come from the place geography, not the county-subdivision one, because
county subdivisions split cities that cross county lines into one row per
county part (Lansing, Holland, ...), while the place geography reports each
city whole.

Output lives in data/processed/michigan/ — a subfolder on purpose, so
build_db.py's glob over data/processed/*.parquet doesn't try to join these
(non-county) tables into the national county master.

County-only indicators (HPSA, AHRF physician ratio, PEP birth/migration, SFID
school adequacy) are intentionally not included here.
"""
import datetime
import io
import json
import re
import time
import zipfile

import pandas as pd
import requests

from mmi.config import BLS_API_KEY, CENSUS_API_KEY, DATA_PROCESSED, ROOT, find_latest_acs_year
from mmi.sources.acs import CENSUS_NULL_CODES, VARIABLES, clean_numeric, derive_indicators
from mmi.sources.cnt_ht import VINTAGE as CNT_VINTAGE

STATE = "26"
OUT_DIR = DATA_PROCESSED / "michigan"
ACS_PATH = OUT_DIR / "mi_acs.parquet"
UNEMPLOYMENT_PATH = OUT_DIR / "mi_unemployment.parquet"
TRANSPORT_PATH = OUT_DIR / "mi_transport.parquet"
BOUNDARIES_PATH = ROOT / "data" / "reference" / "mi_boundaries.geojson"

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_BATCH = 50

# TIGERweb generalized (500K) boundaries. Layers 1 and 4 of this service only
# return geometry inside a scale window; their twins 7 (county subdivisions) and
# 10 (incorporated places) return polygons at any scale.
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/Generalized_ACS2024/Places_CouSub_ConCity_SubMCD/MapServer"
BOUNDARY_LAYERS = {"cousub": 7, "place": 10}

_KIND = re.compile(r"\b(charter township|township|city|village|CDP)$")


def _parts(name: str) -> list[str]:
    parts = [p.strip() for p in name.split(",")]
    if parts and parts[-1] == "Michigan":
        parts = parts[:-1]
    return parts  # [locality] or [locality, county]


def _kind(locality: str) -> str:
    m = _KIND.search(locality)
    return m.group(1) if m else "other"


def _acs_request(year: int, geography: dict) -> pd.DataFrame:
    get = "NAME," + ",".join(VARIABLES + ["B19013_001M"])
    resp = requests.get(
        f"https://api.census.gov/data/{year}/acs/acs5",
        params={"get": get, **geography, "key": CENSUS_API_KEY},
        timeout=120,
    )
    resp.raise_for_status()
    rows = resp.json()
    return pd.DataFrame(rows[1:], columns=rows[0])


def fetch_acs(year: int | None = None) -> pd.DataFrame:
    year = year or find_latest_acs_year()

    places = _acs_request(year, {"for": "place:*", "in": f"state:{STATE}"})
    subs = _acs_request(year, {"for": "county subdivision:*", "in": f"state:{STATE} county:*"})
    subs = subs.rename(columns={"county": "county_fips", "county subdivision": "cousub"})

    places["locality"] = places["NAME"].map(lambda n: _parts(n)[0])
    places["kind"] = places["locality"].map(_kind)
    cities = places[places["kind"] == "city"].copy()
    cities["geoid"] = cities["state"] + cities["place"]
    cities["geo_type"] = "City"

    subs["locality"] = subs["NAME"].map(lambda n: _parts(n)[0])
    subs["county_name"] = subs["NAME"].map(lambda n: _parts(n)[1] if len(_parts(n)) > 1 else "")
    subs["kind"] = subs["locality"].map(_kind)

    # Counties each city touches, read off its county-subdivision parts.
    city_counties = (
        subs[subs["kind"] == "city"]
        .groupby("locality")["county_name"]
        .apply(lambda s: ", ".join(sorted({c.removesuffix(" County") for c in s if c})))
    )
    cities["county"] = cities["locality"].map(city_counties).fillna("")

    towns = subs[subs["kind"].isin(["township", "charter township"])].copy()
    towns["geoid"] = towns["state"] + towns["county_fips"] + towns["cousub"]
    towns["geo_type"] = "Township"
    towns["county"] = towns["county_name"].str.removesuffix(" County")

    keep = pd.concat([cities, towns], ignore_index=True)
    keep = clean_numeric(keep)

    moe = pd.to_numeric(keep["B19013_001M"], errors="coerce")
    moe = moe.where(~moe.isin(CENSUS_NULL_CODES))
    income = keep["B19013_001E"]

    out = pd.DataFrame(
        {
            "geoid": keep["geoid"],
            "geo_type": keep["geo_type"],
            "name": keep["locality"],
            "county": keep["county"],
            "population": keep["B01001_001E"],
            # Margin of error as a share of the estimate: a quick precision flag.
            "income_moe_pct": (100 * moe / income).where(income > 0),
            "acs_year": year,
        }
    )
    out = pd.concat([out, derive_indicators(keep)], axis=1)
    assert out["geoid"].is_unique, "duplicate geoids in Michigan ACS pull"
    return out.sort_values(["geo_type", "name", "geoid"]).reset_index(drop=True)


# --- BLS LAUS -----------------------------------------------------------------

def _series_id(geo_type: str, geoid: str) -> str:
    # LAUS area code: 'CT' + state + 5-digit place FIPS (cities), or
    # 'CS' + state + 5-digit county-subdivision FIPS (townships), zero-padded to
    # 15 characters; series = 'LAU' + area code + measure '03' (unemployment rate).
    if geo_type == "City":
        area = f"CT{STATE}{geoid[2:]}000000"
    else:
        area = f"CS{STATE}{geoid[5:]}000000"
    return f"LAU{area}03"


def fetch_unemployment(geos: pd.DataFrame) -> pd.DataFrame:
    """Latest non-suppressed monthly unemployment rate per Michigan city/township.

    LAUS only publishes sub-county areas of 25,000+ people, so most requested
    series simply don't exist (BLS answers "Series does not exist" and returns no
    data points) and are skipped. Series IDs are built from Census codes, which
    only works because those codes are unique statewide in Michigan — asserted
    below so a collision fails loudly instead of attaching a rate to the wrong
    township.
    """
    series_to_geoid = {_series_id(r.geo_type, r.geoid): r.geoid for r in geos.itertuples()}
    assert len(series_to_geoid) == len(geos), (
        "Census place/county-subdivision codes collide once truncated to BLS's "
        "5-digit form — series IDs would be ambiguous"
    )

    year = datetime.date.today().year
    ids = list(series_to_geoid)
    records = []

    for i in range(0, len(ids), BLS_BATCH):
        batch = ids[i : i + BLS_BATCH]
        resp = requests.post(
            BLS_URL,
            json={
                "seriesid": batch,
                "startyear": str(year - 1),
                "endyear": str(year),
                "registrationkey": BLS_API_KEY,
            },
            timeout=90,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload["status"] != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS API error: {payload.get('message')}")

        for series in payload["Results"]["series"]:
            points = [p for p in series["data"] if p["value"] != "-"]
            if not points:
                continue
            latest = points[0]
            records.append(
                {
                    "geoid": series_to_geoid[series["seriesID"]],
                    "unemployment_rate": float(latest["value"]),
                    "unemployment_rate_period": f"{latest['year']}-{latest['period'].lstrip('M')}",
                }
            )
        time.sleep(0.5)

    return pd.DataFrame(records).drop_duplicates("geoid").sort_values("geoid").reset_index(drop=True)


# --- CNT H+T Index (place level only) -----------------------------------------

def fetch_transport() -> pd.DataFrame:
    resp = requests.get(
        f"https://htaindex.cnt.org/download/download.php?data_yr={CNT_VINTAGE}&focus=place&geoid={STATE}",
        timeout=90,
    )
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
    with zf.open(csv_name) as f:
        df = pd.read_csv(f, dtype={"place": str})
    df["geoid"] = df["place"].str.replace('"', "", regex=False).str.strip()
    return (
        df[["geoid", "t_ami"]]
        .rename(columns={"t_ami": "transportation_cost_burden_pct"})
        .drop_duplicates("geoid")
        .reset_index(drop=True)
    )


# --- boundaries (static reference file) ---------------------------------------

def _signed_area(ring: list) -> float:
    """Shoelace area in lon/lat; positive means counter-clockwise."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) / 2


def _orient(ring: list, clockwise: bool) -> list:
    is_clockwise = _signed_area(ring) < 0
    return ring if is_clockwise == clockwise else ring[::-1]


def rewind_for_plotly(geometry: dict) -> dict:
    """Exterior rings clockwise, holes counter-clockwise.

    Plotly's geo renderer (d3-geo) treats rings spherically, so it wants the
    opposite of RFC 7946 (which is what ArcGIS emits). Wrong winding doesn't
    error — each polygon silently fills the entire view instead of its own
    shape. Idempotent: orientation is decided from the ring's own area.
    """
    def fix(polygon: list) -> list:
        return [_orient(ring, clockwise=(i == 0)) for i, ring in enumerate(polygon)]

    if geometry["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": fix(geometry["coordinates"])}
    if geometry["type"] == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": [fix(p) for p in geometry["coordinates"]]}
    return geometry


def build_boundaries(geoids: set[str]) -> dict:
    features = []
    for layer in BOUNDARY_LAYERS.values():
        resp = requests.get(
            f"{TIGERWEB}/{layer}/query",
            params={
                "where": f"STATE='{STATE}'",
                "outFields": "GEOID",
                "returnGeometry": "true",
                "outSR": 4326,
                "geometryPrecision": 4,
                "f": "geojson",
            },
            timeout=180,
        )
        resp.raise_for_status()
        for feat in resp.json()["features"]:
            gid = feat["properties"]["GEOID"]
            if gid in geoids and feat.get("geometry"):
                features.append(
                    {"type": "Feature", "properties": {"GEOID": gid}, "geometry": rewind_for_plotly(feat["geometry"])}
                )
    return {"type": "FeatureCollection", "features": features}


# --- orchestration ------------------------------------------------------------

def _load_geos() -> pd.DataFrame:
    if not ACS_PATH.exists():
        main_acs()
    return pd.read_parquet(ACS_PATH, columns=["geoid", "geo_type", "name", "county"])


def main_acs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = fetch_acs()
    df.to_parquet(ACS_PATH, index=False)
    print(f"Wrote {len(df)} Michigan areas ({(df.geo_type == 'City').sum()} cities, "
          f"{(df.geo_type == 'Township').sum()} townships) to {ACS_PATH}")


def main_bls():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = fetch_unemployment(_load_geos())
    df.to_parquet(UNEMPLOYMENT_PATH, index=False)
    print(f"Wrote {len(df)} Michigan areas with BLS unemployment to {UNEMPLOYMENT_PATH}")


def main_cnt():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = fetch_transport()
    df.to_parquet(TRANSPORT_PATH, index=False)
    print(f"Wrote {len(df)} Michigan places with CNT transportation burden to {TRANSPORT_PATH}")


def main_boundaries():
    geoids = set(_load_geos()["geoid"])
    geojson = build_boundaries(geoids)
    BOUNDARIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOUNDARIES_PATH.write_text(json.dumps(geojson, separators=(",", ":")))
    missing = geoids - {f["properties"]["GEOID"] for f in geojson["features"]}
    print(f"Wrote {len(geojson['features'])} boundaries to {BOUNDARIES_PATH} "
          f"({len(missing)} areas have no boundary)")


def load_master() -> pd.DataFrame:
    """ACS indicators with BLS unemployment and CNT transportation burden joined on."""
    df = pd.read_parquet(ACS_PATH)
    for path in (UNEMPLOYMENT_PATH, TRANSPORT_PATH):
        if path.exists():
            df = df.merge(pd.read_parquet(path), on="geoid", how="left")
    return df


def main():
    main_acs()
    main_bls()
    main_cnt()
    main_boundaries()


if __name__ == "__main__":
    main()
