import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mmi.build_db import load_county_master  # noqa: E402

st.set_page_config(page_title="MMI County Dashboard", layout="wide")

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
    return load_county_master()


@st.cache_data
def get_county_geojson():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    return requests.get(url, timeout=30).json()


df = get_data()
numeric_cols = [c for c in LABELS if c in df.columns]

st.title("MMI County Dashboard")
st.caption(f"{len(df):,} counties · updated indicators pulled from Census, BLS, and HRSA")

col1, col2 = st.columns([1, 2])

with col1:
    variable = st.selectbox("Variable", numeric_cols, format_func=lambda c: LABELS[c])
    series = df[variable].dropna()
    lo, hi = float(series.min()), float(series.max())
    selected_range = st.slider("Filter range", lo, hi, (lo, hi))
    filtered = df[df[variable].between(*selected_range)]
    st.metric("Counties matching filter", f"{len(filtered):,} / {len(df):,}")

with col2:
    geojson = get_county_geojson()
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="fips",
        color=variable,
        color_continuous_scale="Viridis",
        scope="usa",
        labels={variable: LABELS[variable]},
        hover_name="county_name",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=450)
    st.plotly_chart(fig, width="stretch")

st.subheader("Filtered counties")
display_cols = ["county_name", variable] + [c for c in numeric_cols if c != variable]
st.dataframe(filtered[["fips"] + display_cols].rename(columns=LABELS), width="stretch", height=400)
