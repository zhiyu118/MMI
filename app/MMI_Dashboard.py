import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mmi.build_db import load_county_master  # noqa: E402

st.set_page_config(page_title="MMI Dashboard", layout="wide")

LABELS = {
    "median_monthly_hh_income": "Median Monthly Household Income ($)",
    "mean_monthly_hh_income": "Mean Monthly Household Income ($)",
    "rent_to_income_ratio_pct": "Rent-to-Income Ratio (%)",
    "property_price_to_income_ratio": "Property Price-to-Income Ratio",
    "median_age": "Median Age",
    "pct_population_65_plus": "Population 65+ (%)",
    "pct_foreign_born": "Foreign Born (%)",
    "median_monthly_rent": "Median Monthly Rent ($)",
    "mean_monthly_rent": "Mean Monthly Rent ($)",
    "rental_vacancy_rate_pct": "Rental Vacancy Rate (%)",
    "unemployment_rate": "Unemployment Rate (%)",
    "net_migration_rate_per_1000": "Net Migration Rate (per 1,000)",
    "birth_rate_per_1000": "Birth Rate (per 1,000)",
    "hpsa_score": "HPSA Score (higher = more severe shortage)",
    "population_per_primary_care_physician": "Population per Primary Care Physician",
    "school_adequacy_rate": "School Adequacy Rate ($ per pupil, actual - required)",
    "transportation_cost_burden_pct": "Transportation Cost Burden (% of income, 2022)",
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
numeric_cols = [c for c in LABELS if c in df.columns]

st.title("MMI Dashboard")
st.caption(f"{len(df):,} counties · updated indicators pulled from Census, BLS, and HRSA")

st.sidebar.header("Filters")

state_options = ["All States"] + sorted(df["state"].dropna().unique())
selected_state = st.sidebar.selectbox("State", state_options)

st.sidebar.markdown("---")
filter_count_placeholder = st.sidebar.empty()
selected_vars = st.sidebar.multiselect(
    "Variables",
    options=numeric_cols,
    format_func=lambda c: LABELS[c],
)
ordered_selected_vars = [c for c in numeric_cols if c in selected_vars]

bounds = {}
for var in ordered_selected_vars:
    st.sidebar.markdown(f"**{LABELS[var]}**")
    col_min, col_max = st.sidebar.columns(2)
    min_val = col_min.number_input("Min", key=f"min_{var}", value=None)
    max_val = col_max.number_input("Max", key=f"max_{var}", value=None)
    bounds[var] = (min_val, max_val)

n_applied = sum(1 for lo, hi in bounds.values() if lo is not None or hi is not None)
filter_count_placeholder.markdown(f"**{n_applied} filter(s) applied**")

mask = pd.Series(True, index=df.index)
if selected_state != "All States":
    mask &= df["state"] == selected_state
for var, (lo, hi) in bounds.items():
    if lo is not None:
        mask &= df[var] >= lo
    if hi is not None:
        mask &= df[var] <= hi

filtered = df[mask].sort_values("county_name")

st.metric("Counties matching filters", f"{len(filtered):,} / {len(df):,}")

if len(filtered) > 0:
    geojson = get_county_geojson()
    fig = px.choropleth(
        filtered,
        geojson=geojson,
        locations="fips",
        color_discrete_sequence=["#2E86AB"],
        scope="usa",
        hover_name="county_name",
    )
    fig.update_traces(showlegend=False)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=450)
    st.plotly_chart(fig, width="stretch")

    st.subheader("Counties")
    display_cols = ["county_name", "state"] + numeric_cols
    rename_map = {"county_name": "County", "state": "State"}
    for c in numeric_cols:
        rename_map[c] = f"🔵 {LABELS[c]}" if c in ordered_selected_vars else LABELS[c]
    st.dataframe(
        filtered[["fips"] + display_cols].rename(columns=rename_map),
        width="stretch",
        height=400,
        hide_index=True,
    )
else:
    st.info("No counties match the selected filters.")
