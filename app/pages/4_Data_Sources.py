import pandas as pd
import streamlit as st

st.set_page_config(page_title="Data Sources", layout="wide")

# (display label, source, update schedule) — kept independent of LABELS/column
# names in the other pages since this is documentation, not derived from data.
VARIABLES = [
    ("Birth Rate (per 1,000)", "Census Population Estimates Program (PEP)", "Annual (March)"),
    ("Foreign Born (%)", "Census ACS 5-Year", "Annual (December)"),
    ("HPSA Score (higher = more severe shortage)", "HRSA HPSA (Health Professional Shortage Area) Database", "Monthly"),
    ("Mean Monthly Household Income ($)", "Census ACS 5-Year", "Annual (December)"),
    ("Mean Monthly Rent ($)", "Census ACS 5-Year", "Annual (December)"),
    ("Median Age", "Census ACS 5-Year", "Annual (December)"),
    ("Median Monthly Household Income ($)", "Census ACS 5-Year", "Annual (December)"),
    ("Median Monthly Rent ($)", "Census ACS 5-Year", "Annual (December)"),
    ("Net Migration Rate (per 1,000)", "Census Population Estimates Program (PEP)", "Annual (March)"),
    ("Population 65+ (%)", "Census ACS 5-Year", "Annual (December)"),
    ("Population per Primary Care Physician", "HRSA Area Health Resource Files (AHRF)", "Annual"),
    ("Property Price-to-Income Ratio", "Census ACS 5-Year", "Annual (December)"),
    ("Rent-to-Income Ratio (%)", "Census ACS 5-Year", "Annual (December)"),
    ("Rental Vacancy Rate (%)", "Census ACS 5-Year", "Annual (December)"),
    ("School Adequacy Rate ($ per pupil, actual - required)", "School Finance Indicators Database (SFID)", "Annual (February–March)"),
    ("Transportation Cost Burden (% of income)", "Center for Neighborhood Technology (CNT) H+T Index", "Irregular — current release is 2022"),
    ("Unemployment Rate (%)", "BLS Local Area Unemployment Statistics (LAUS)", "Monthly"),
]

st.title("Data Sources")
st.caption("Every variable in this dashboard, its source, and how often it's refreshed.")

df = pd.DataFrame(VARIABLES, columns=["Variable", "Source", "Update Schedule"])
df = df.sort_values("Variable").reset_index(drop=True)

st.dataframe(df, width="stretch", height=650, hide_index=True)

st.subheader("Michigan Dashboard (cities and townships)")
st.caption(
    "Same sources as above, read at city and township level. Indicators that exist only "
    "for counties (HPSA, primary care physician ratio, birth rate, net migration, school "
    "adequacy) are not part of the Michigan dashboard."
)

ACS_MI = "Census ACS 5-Year (place and county-subdivision tables)"
MI_VARIABLES = [
    ("Population", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Median Age", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Population 65+ (%)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Foreign Born (%)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Median Monthly Household Income ($)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Mean Monthly Household Income ($)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Median Monthly Rent ($)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Mean Monthly Rent ($)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Rent-to-Income Ratio (%)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Property Price-to-Income Ratio", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Rental Vacancy Rate (%)", ACS_MI, "Cities and townships", "Annual (December)"),
    ("Median Household Income Margin of Error (% of estimate)", ACS_MI, "Cities and townships", "Annual (December)"),
    (
        "Unemployment Rate (%)",
        "BLS Local Area Unemployment Statistics (LAUS)",
        "Only cities and townships with 25,000+ residents (BLS threshold)",
        "Monthly",
    ),
    (
        "Transportation Cost Burden (% of income)",
        "Center for Neighborhood Technology (CNT) H+T Index",
        "Cities only — CNT has no township geography",
        "Irregular — current release is 2022",
    ),
]
mi_df = pd.DataFrame(
    MI_VARIABLES, columns=["Variable", "Source", "Michigan geography covered", "Update Schedule"]
)
st.dataframe(mi_df, width="stretch", hide_index=True)
