"""CDC WONDER pull: Birth Rate (county births / county population).

NOT YET IMPLEMENTED. CDC WONDER has no conventional REST API — it's queried by
POSTing a specifically-formed XML request body to an endpoint like
https://wonder.cdc.gov/controller/datarequest/D149 (dataset ID varies by natality
vintage, e.g. D149 = Natality 2007-2024). The XML must encode every filter/grouping
choice (e.g. group by county, measure = birth count) using CDC's internal parameter
codes, which aren't documented in a stable, public schema — the reliable way to get
them is to build the query in the WONDER web UI, use its "Export" button to get a
request-parameters file, and reverse-engineer the XML from that rather than guess.

Also note: CDC suppresses county birth counts under 10 for privacy, so full
county coverage isn't possible for the smallest counties regardless of query design.

Numerator (births) needs this; denominator (population) can reuse pep.py's output.
"""
import pandas as pd

from mmi.config import DATA_PROCESSED


def fetch() -> pd.DataFrame:
    raise NotImplementedError(
        "Needs a working CDC WONDER XML query built from the web UI's export "
        "feature. See module docstring."
    )


def main():
    raise NotImplementedError("See module docstring — not yet implemented.")


if __name__ == "__main__":
    main()
