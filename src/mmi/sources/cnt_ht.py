"""Center for Neighborhood Technology (CNT) pull: Transportation Cost Burden.

htaindex.cnt.org/download/ looks account-gated but isn't, for the county-level
national file: its "All Counties" link is built client-side by download.js as
`download.php?data_yr={vintage}&focus=county`, which 302-redirects to a static
zip with NO auth required — confirmed with a plain unauthenticated curl request.
So this is a normal scripted pull like every other source, not the manual-file
workaround the module briefly used before this was found.

Confirmed column layout: `county` is the 5-digit county FIPS, oddly triple-quoted
in the source CSV (six quote characters wrapping e.g. 44001 — an escaping
artifact from CNT's export, stripped below). `t_ami` is transportation cost as a
percentage of income for the "regional typical household" (AMI) profile, which
is what "Transportation Cost Burden" in the data dictionary means. CNT also
provides `t_80ami` (low-income household profile) and `t_nmi` as alternatives.

This is also the one indicator confirmed NOT to refresh annually (CNT's last
major vintage as of this writing is still 2022, per this file's last-modified
date) — flag that explicitly in the app rather than implying it's as current as
everything else.
"""
import io
import zipfile

import pandas as pd
import requests

from mmi.config import DATA_PROCESSED

VINTAGE = 2022  # CNT's current release; check htaindex.cnt.org/download/ for a newer one
DOWNLOAD_URL = f"https://htaindex.cnt.org/download/download.php?data_yr={VINTAGE}&focus=county"


def fetch_county_level() -> pd.DataFrame:
    resp = requests.get(DOWNLOAD_URL, timeout=60)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
    with zf.open(csv_name) as f:
        df = pd.read_csv(f, dtype={"county": str})

    df["fips"] = df["county"].str.replace('"', "", regex=False).str.strip()

    out = df[["fips", "t_ami", "t_80ami", "t_nmi"]].rename(
        columns={
            "t_ami": "transportation_cost_burden_pct",
            "t_80ami": "transportation_cost_burden_low_income_pct",
            "t_nmi": "transportation_cost_burden_nmi_pct",
        }
    )
    return out.drop_duplicates("fips").sort_values("fips").reset_index(drop=True)


def main():
    df = fetch_county_level()
    out_path = DATA_PROCESSED / "cnt_ht.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} counties to {out_path}")


if __name__ == "__main__":
    main()
