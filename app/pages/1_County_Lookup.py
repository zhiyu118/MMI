import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from mmi.build_db import load_county_master  # noqa: E402

st.set_page_config(page_title="County Lookup", layout="wide")


@st.cache_data
def get_data() -> pd.DataFrame:
    return load_county_master()


df = get_data()

st.title("County Lookup")
selected = st.multiselect(
    "Choose one or more counties to compare",
    options=df["county_name"].sort_values(),
    default=[df["county_name"].iloc[0]],
)

if selected:
    subset = df[df["county_name"].isin(selected)].set_index("county_name")
    st.dataframe(subset.T, width="stretch")
else:
    st.info("Select at least one county above.")
