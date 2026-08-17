"""NCES EDFacts pull: EL program enrollment count + EL % of population.

STILL NOT IMPLEMENTED, but narrowed down:
- Confirmed EL/LEP counts are NOT in CCD proper. Reverse-engineered CCD's file
  browser (nces.ed.gov/ccd/files.asp -> its Angular app calls a JSON API at
  nces.ed.gov/ccd/datatables/api/File/{fiscal}/{level}/{schoolYearId}/0/0/0) and
  enumerated every District- and School-level table for 2022-23 through 2024-25:
  only Directory, Membership (by race/sex/grade — no program breakdown), Staff,
  Lunch Program Eligibility, Dropout, and Graduate/Completer exist. No EL table.
- EL/LEP is collected via EDFacts's separate "Title III/LEP" topic instead of CCD.
  The old bulk-file index (www2.ed.gov/.../edfacts/data-files/index.html) 404s —
  ed.gov's EDFacts section was reorganized at some point in 2025 and the old path
  is gone. The likely current home is the "Data Download Tool" at
  eddataexpress.ed.gov/download/data-builder/data-download-tool, but that's a
  client-rendered tool with no discoverable backing API (unlike CCD's), so the
  next step is either finding its API by inspecting real browser network traffic
  (not just a plain HTTP GET, which returns nothing useful), or emailing
  EDFacts@ed.gov directly per NCES's own suggestion.

Once LEA-level EL counts exist, aggregate via district_crosswalk.fetch_crosswalk()
the same way sfid.py does (enrollment-weighted average per county).
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
