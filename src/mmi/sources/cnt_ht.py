"""Center for Neighborhood Technology (CNT) pull: Transportation Cost Burden.

NOT YET IMPLEMENTED. htaindex.cnt.org/download/ requires account registration —
there is no anonymous bulk-download endpoint, so this can't be scripted without
your CNT credentials. Two ways forward once you have an account:
  1. Manual: log in, export county-level data by hand each refresh cycle (defeats
     the "zero-touch" goal for this one variable, but simplest).
  2. Scripted: inspect the authenticated download request in browser devtools
     after logging in, and replicate it here with session cookies/credentials
     read from an env var — only worth it if CNT's terms of service allow
     automated access.
Also recall this index isn't updated annually (last major vintage ~2022), so even
once automated, it won't refresh on the same cadence as the rest of the pipeline —
flag that explicitly wherever this value is displayed.
"""
import pandas as pd

from mmi.config import DATA_PROCESSED


def fetch() -> pd.DataFrame:
    raise NotImplementedError("Needs a CNT account. See module docstring.")


def main():
    raise NotImplementedError("See module docstring — not yet implemented.")


if __name__ == "__main__":
    main()
