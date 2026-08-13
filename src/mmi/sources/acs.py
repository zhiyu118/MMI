"""Census ACS 5-Year pull: income, rent, home value, age, foreign-born, rental vacancy.

Variable codes verified against https://api.census.gov/data/{year}/acs/acs5/groups/*.json
"""
import pandas as pd
import requests

from mmi.config import ACS_YEAR, CENSUS_API_KEY, DATA_PROCESSED, STATE_FIPS

MALE_65_PLUS = ["B01001_020E", "B01001_021E", "B01001_022E", "B01001_023E", "B01001_024E", "B01001_025E"]
FEMALE_65_PLUS = ["B01001_044E", "B01001_045E", "B01001_046E", "B01001_047E", "B01001_048E", "B01001_049E"]

VARIABLES = [
    "B19013_001E",  # median household income (annual)
    "B19025_001E",  # aggregate household income
    "B19001_001E",  # total households
    "B25071_001E",  # median gross rent as % of household income
    "B25077_001E",  # median home value
    "B01002_001E",  # median age
    "B01001_001E",  # total population
    "B05012_001E",  # total population (nativity universe)
    "B05012_003E",  # foreign-born population
    "B25064_001E",  # median gross rent
    "B25065_001E",  # aggregate gross rent
    "B25003_003E",  # renter-occupied housing units
    "B25004_002E",  # vacant housing units, for rent
    *MALE_65_PLUS,
    *FEMALE_65_PLUS,
]


def fetch(year: int = ACS_YEAR) -> pd.DataFrame:
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    get_param = "NAME," + ",".join(VARIABLES)
    resp = requests.get(
        url,
        params={"get": get_param, "for": "county:*", "in": "state:*", "key": CENSUS_API_KEY},
        timeout=60,
    )
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df[df["state"].isin(STATE_FIPS)].copy()
    df["fips"] = df["state"] + df["county"]

    # Census's fixed set of sentinel codes for suppressed/not-computed estimates.
    # (Not a magnitude cutoff — aggregate dollar variables legitimately exceed 1e8
    # for populous counties, e.g. LA County aggregate income is ~$4.3e11.)
    CENSUS_NULL_CODES = {-666666666, -999999999, -888888888, -555555555, -333333333, -222222222}

    for col in VARIABLES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[df[col].isin(CENSUS_NULL_CODES), col] = pd.NA

    out = pd.DataFrame({"fips": df["fips"], "county_name": df["NAME"], "acs_year": year})

    out["median_monthly_hh_income"] = df["B19013_001E"] / 12
    out["mean_monthly_hh_income"] = (df["B19025_001E"] / df["B19001_001E"]) / 12
    out["rent_to_income_ratio_pct"] = df["B25071_001E"]
    out["median_home_value"] = df["B25077_001E"]
    out["property_price_to_income_ratio"] = df["B25077_001E"] / df["B19013_001E"]
    out["median_age"] = df["B01002_001E"]

    pop_65_plus = df[MALE_65_PLUS].sum(axis=1) + df[FEMALE_65_PLUS].sum(axis=1)
    out["pct_population_65_plus"] = 100 * pop_65_plus / df["B01001_001E"]

    out["pct_foreign_born"] = 100 * df["B05012_003E"] / df["B05012_001E"]
    out["total_foreign_born_population"] = df["B05012_003E"]

    out["median_monthly_rent"] = df["B25064_001E"]
    # Mean gross rent approximated as aggregate gross rent / renter-occupied units.
    # True ACS universe for gross rent is "renter-occupied paying cash rent," a slightly
    # smaller denominator, so this is a small downward-biased approximation.
    out["mean_monthly_rent"] = df["B25065_001E"] / df["B25003_003E"]

    # Rental vacancy rate = vacant-for-rent / (renter-occupied + vacant-for-rent), per
    # Census's standard rental vacancy rate definition.
    out["rental_vacancy_rate_pct"] = 100 * df["B25004_002E"] / (df["B25003_003E"] + df["B25004_002E"])

    return out.sort_values("fips").reset_index(drop=True)


def main():
    df = fetch()
    out_path = DATA_PROCESSED / "acs.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} counties to {out_path}")


if __name__ == "__main__":
    main()
