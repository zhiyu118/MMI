import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from mmi.michigan import ACS_PATH, BOUNDARIES_PATH, load_master  # noqa: E402

st.set_page_config(page_title="Michigan Dashboard", layout="wide")

# Same indicators as the national dashboard minus the county-only ones
# (HPSA, primary care physician ratio, birth rate, net migration, school adequacy).
LABELS = {
    "population": "Population",
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
    "transportation_cost_burden_pct": "Transportation Cost Burden (% of income, 2022)",
    "income_moe_pct": "Median Household Income Margin of Error (% of estimate)",
}
LOW_PRECISION_MOE_PCT = 20


@st.cache_data(ttl=6 * 3600)
def get_data() -> pd.DataFrame:
    return load_master()


@st.cache_data
def get_boundaries() -> dict:
    return json.loads(BOUNDARIES_PATH.read_text())


if not (ACS_PATH.exists() and BOUNDARIES_PATH.exists()):
    st.title("Michigan Dashboard")
    st.info("Michigan data hasn't been generated yet. It is built by the scheduled refresh.")
    st.stop()

df = get_data()
geojson = get_boundaries()
filter_cols = [c for c in LABELS if c in df.columns]
acs_year = int(df["acs_year"].iloc[0])

st.title("Michigan Dashboard")
n_cities = int((df["geo_type"] == "City").sum())
n_towns = int((df["geo_type"] == "Township").sum())
st.caption(
    f"{n_cities:,} cities and {n_towns:,} townships · ACS {acs_year} 5-year estimates, "
    "BLS unemployment, CNT transportation costs"
)

with st.expander("About this data"):
    n_unemp = int(df["unemployment_rate"].notna().sum()) if "unemployment_rate" in df else 0
    n_transport = (
        int(df.loc[df["geo_type"] == "City", "transportation_cost_burden_pct"].notna().sum())
        if "transportation_cost_burden_pct" in df
        else 0
    )
    n_wide = int((df["income_moe_pct"] >= LOW_PRECISION_MOE_PCT).sum())
    st.markdown(
        f"""
- **Geography:** incorporated cities plus townships (including charter townships). Villages and
  census-designated places sit inside townships, so their residents are counted in the township.
- **Unemployment rate:** BLS Local Area Unemployment Statistics, most recent month available,
  not seasonally adjusted. BLS only covers sub-county areas with 25,000+ people, so **{n_unemp}** of
  {len(df):,} areas have a value.
- **Transportation cost burden:** CNT H+T Index (2022 release). CNT publishes city-level data but
  no township geography, so only **{n_transport}** cities have a value; townships are blank.
- **Precision:** ACS estimates for small areas can be imprecise. **{n_wide}** areas have a median
  household income margin of error of {LOW_PRECISION_MOE_PCT}% or more of the estimate — use the
  sidebar toggle to hide them.
- Indicators that exist only at the county level (HPSA, primary care physician ratio, birth rate,
  net migration, school adequacy) are not shown here.
"""
    )

st.sidebar.header("Filters")

area_type = st.sidebar.radio("Area type", ["All", "Cities", "Townships"], key="mi_area_type")

county_options = sorted({c for s in df["county"].dropna() for c in s.split(", ") if c})
selected_county = st.sidebar.selectbox("County", ["All Counties"] + county_options, key="mi_county")

hide_low_precision = st.sidebar.checkbox(
    f"Hide low-precision areas (income margin of error ≥ {LOW_PRECISION_MOE_PCT}%)",
    key="mi_hide_low_precision",
)

st.sidebar.markdown("---")
filter_count_placeholder = st.sidebar.empty()
selected_vars = st.sidebar.multiselect(
    "Variables",
    options=filter_cols,
    format_func=lambda c: LABELS[c],
    key="mi_vars",
)
ordered_selected_vars = [c for c in filter_cols if c in selected_vars]

bounds = {}
for var in ordered_selected_vars:
    st.sidebar.markdown(f"**{LABELS[var]}**")
    col_min, col_max = st.sidebar.columns(2)
    min_val = col_min.number_input("Min", key=f"mi_min_{var}", value=None)
    max_val = col_max.number_input("Max", key=f"mi_max_{var}", value=None)
    bounds[var] = (min_val, max_val)

n_applied = sum(1 for lo, hi in bounds.values() if lo is not None or hi is not None)
filter_count_placeholder.markdown(f"**{n_applied} filter(s) applied**")

mask = pd.Series(True, index=df.index)
if area_type == "Cities":
    mask &= df["geo_type"] == "City"
elif area_type == "Townships":
    mask &= df["geo_type"] == "Township"
if selected_county != "All Counties":
    mask &= df["county"].fillna("").map(lambda s: selected_county in s.split(", "))
if hide_low_precision:
    mask &= df["income_moe_pct"] < LOW_PRECISION_MOE_PCT
for var, (lo, hi) in bounds.items():
    if lo is not None:
        mask &= df[var] >= lo
    if hi is not None:
        mask &= df[var] <= hi

filtered = df[mask].sort_values("name")

st.metric("Areas matching filters", f"{len(filtered):,} / {len(df):,}")

# One trace: matching areas blue, everything else light gray, so the state
# outline stays visible and the view doesn't jump around as filters change.
def _county_label(c: str) -> str:
    if not c:
        return ""
    return f" — {c} Counties" if "," in c else f" — {c} County"


hover = (
    df["name"]
    + df["county"].fillna("").map(_county_label)
    + " ("
    + df["geo_type"]
    + ")"
    + mask.map(lambda m: "" if m else " · not matching filters")
)
fig = go.Figure(
    go.Choropleth(
        geojson=geojson,
        featureidkey="properties.GEOID",
        locations=df["geoid"],
        z=mask.astype(int),
        zmin=0,
        zmax=1,
        colorscale=[[0, "#E5E7EB"], [1, "#2E86AB"]],
        showscale=False,
        marker_line_width=0.4,
        marker_line_color="#FFFFFF",
        text=hover,
        hovertemplate="%{text}<extra></extra>",
    )
)
fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=600)
st.plotly_chart(fig, width="stretch")

if len(filtered) == 0:
    st.info("No areas match the selected filters.")
else:
    st.subheader("Cities and townships")
    unselected_vars = [c for c in filter_cols if c not in ordered_selected_vars]
    id_cols = ["name", "geo_type", "county"]
    display_cols = id_cols + ordered_selected_vars + unselected_vars
    rename_map = {"name": "Area", "geo_type": "Type", "county": "County"}
    for c in filter_cols:
        rename_map[c] = f"🔵 {LABELS[c]}" if c in ordered_selected_vars else LABELS[c]

    st.dataframe(
        filtered[display_cols].rename(columns=rename_map),
        width="stretch",
        height=400,
        hide_index=True,
    )
