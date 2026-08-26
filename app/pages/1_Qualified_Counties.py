import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from mmi.build_db import load_county_master  # noqa: E402

st.set_page_config(page_title="Qualified Counties", layout="wide")

LABELS = {
    "unemployment_rate": "Unemployment Rate (%)",
    "pct_population_65_plus": "Population 65+ (%)",
    "rent_to_income_ratio_pct": "Rent-to-Income Ratio (%)",
    "rental_vacancy_rate_pct": "Rental Vacancy Rate (%)",
}

CRITERIA = [
    ("unemployment_rate", "le", 4.3, "Unemployment Rate ≤ 4.3%"),
    ("pct_population_65_plus", "ge", 14, "Population 65+ ≥ 14%"),
    ("rent_to_income_ratio_pct", "le", 30, "Rent-to-Income Ratio ≤ 30%"),
    ("rental_vacancy_rate_pct", "gt", 5, "Rental Vacancy Rate > 5%"),
]

OPS = {
    "lt": lambda s, v: s < v,
    "le": lambda s, v: s <= v,
    "gt": lambda s, v: s > v,
    "ge": lambda s, v: s >= v,
}


@st.cache_data
def get_data() -> pd.DataFrame:
    df = load_county_master()
    df["state"] = df["county_name"].str.rsplit(", ", n=1).str[-1]
    return df


@st.cache_data
def get_county_geojson():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    return requests.get(url, timeout=30).json()


df = get_data()

st.title("Qualified Counties")
st.caption("Toggle criteria on or off — thresholds are fixed.")

enabled = {col: st.checkbox(label, value=True) for col, _, _, label in CRITERIA}

mask = pd.Series(True, index=df.index)
for col, op, value, _ in CRITERIA:
    if enabled[col]:
        mask &= OPS[op](df[col], value)
qualified = df[mask]

state_options = ["All States"] + sorted(qualified["state"].dropna().unique())
selected_state = st.selectbox("Filter by state", state_options)

if selected_state != "All States":
    qualified = qualified[qualified["state"] == selected_state]

qualified = qualified.sort_values("county_name")

st.metric("Qualified counties", f"{len(qualified):,} / {len(df):,}")

if len(qualified) > 0:
    geojson = get_county_geojson()
    fig = px.choropleth(
        qualified,
        geojson=geojson,
        locations="fips",
        color_discrete_sequence=["#2E86AB"],
        scope="usa",
        hover_name="county_name",
    )
    fig.update_traces(showlegend=False)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=450)
    st.plotly_chart(fig, width="stretch")

    display_cols = ["county_name", "state"] + list(LABELS.keys())
    st.dataframe(
        qualified[display_cols].rename(columns=LABELS),
        width="stretch",
        height=400,
        hide_index=True,
    )
else:
    st.info("No counties match all criteria for this selection.")
