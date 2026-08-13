"""NCES EDFacts/CCD pull: EL program enrollment count + EL % of population.

NOT YET IMPLEMENTED. nces.ed.gov/ccd/files.asp is a JS-rendered page — its file
links aren't reachable by a plain HTTP GET, so the exact current-year LEA-level
EL-enrollment CSV URL still needs to be found (likely via the CCD Data File Tool
or by contacting EDFacts@ed.gov per NCES's own guidance for this dataset).

Same district -> county aggregation dependency as sfid.py: once the LEA-level EL
counts are in hand, they need the same leaid -> county FIPS crosswalk (NCES CCD
LEA directory file's county field, or the EDGE geographic relationship shapefile)
before they can be rolled up to county level. Build this crosswalk once and share
it between nces_el.py and sfid.py rather than duplicating it.
"""
import pandas as pd

from mmi.config import DATA_PROCESSED


def fetch_county_level() -> pd.DataFrame:
    raise NotImplementedError(
        "Needs: (1) current LEA-level EL enrollment file URL, (2) leaid -> county "
        "FIPS crosswalk shared with sfid.py. See module docstring."
    )


def main():
    raise NotImplementedError("See module docstring — not yet implemented.")


if __name__ == "__main__":
    main()
