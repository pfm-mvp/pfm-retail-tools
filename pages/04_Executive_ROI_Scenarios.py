
import streamlit as st
import pandas as pd
import numpy as np
from ui import kpi_card
from utils_pfmx import inject_css, api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct

st.set_page_config(page_title="Executive ROI Scenarios", page_icon="💼", layout="wide")
inject_css(st)

st.markdown("### <span class='pill'>CCO / Executive</span> ROI & Scenario Dashboard", unsafe_allow_html=True)
API_URL = st.secrets["API_URL"]

shop_input = st.text_input("Shop IDs (komma-gescheiden)", value="26304,26305,26306")
shops = [int(x.strip()) for x in shop_input.split(",") if x.strip().isdigit()]
period = st.selectbox("Periode", ["last_month","this_quarter","last_quarter","this_year","last_year"], index=0)

# Assumptions
st.markdown("#### Scenario-parameters")
col1,col2,col3,col4 = st.columns(4)
with col1:
    conv_target_pp = st.slider("Conversie-target (+pp)", 0.0, 0.20, 0.05, 0.01)
with col2:
    spv_uplift = st.slider("SPV-uplift (%)", 0, 50, 10, 1) / 100.0
with col3:
    gross_margin = st.slider("Brutomarge (%)", 20, 80, 55, 1) / 100.0
with col4:
    capex = st.number_input("CAPEX per store (€)", min_value=0, value=1500, step=100)

with st.expander("🎯 Targets voor demo", expanded=True):
    payback_target = st.slider("Payback-target (maanden)", 1, 36, 12, 1)

params = [("source","shops"), ("period", period)]
for sid in shops:
    params.append(("data", sid))
for k in ["count_in","conversion_rate","turnover","sales_per_visitor"]:
    params.append(("data_output", k))

js = api_get_report(params, API_URL)
df = normalize_vemcount_daylevel(js)
if df.empty:
    st.info("Geen data.")
    st.stop()

# Baseline by store
base = df.groupby("shop_id", as_index=False).agg(
    visitors=("count_in","sum"),
    turnover=("turnover","sum"),
    conv=("conversion_rate","mean"),
    spv=("sales_per_visitor","mean"),
)
# Scenario computations
scen = base.copy()
scen["conv_new"] = np.clip(scen["conv"] + conv_target_pp, 0, 1)
scen["spv_new"] = scen["spv"] * (1 + spv_uplift)
scen["tickets"] = scen["visitors"] * scen["conv"]
scen["tickets_new"] = scen["visitors"] * scen["conv_new"]
scen["turnover_new"] = scen["tickets_new"] * scen["spv_new"]
scen["uplift_eur"] = scen["turnover_new"] - scen["turnover"]
days = max(len(df["date"].unique()), 1)
scen["gross_profit_uplift"] = scen["uplift_eur"] * gross_margin
scen["payback_months"] = np.where(scen["gross_profit_uplift"]>0, capex / (scen["gross_profit_uplift"]/days * 30), np.nan)

# KPI cards with tone
extra_turnover = scen["uplift_eur"].sum()
extra_gp = scen["gross_profit_uplift"].sum()
pb_median = scen["payback_months"].median()
pb_tone = "good" if (not np.isnan(pb_median) and pb_median <= payback_target) else "bad"
pb_txt = f"{pb_median:.1f} mnd" if not np.isnan(pb_median) else "n.v.t."

c1,c2,c3,c4 = st.columns(4)
kpi_card("Extra omzet (periode)", f"💶 {fmt_eur(extra_turnover)}", "Scenario uplift", tone="primary")
kpi_card("Extra brutowinst", f"🏦 {fmt_eur(extra_gp)}", f"Marges: {int(gross_margin*100)}%", tone="primary")
kpi_card("Median Payback", f"{'↑' if pb_tone=='good' else '↓'} {pb_txt}", f"Target ≤ {payback_target} mnd", tone=pb_tone)
kpi_card("Winkels", f"🏬 {len(scen)}", "In scope", tone="neutral")

st.markdown("#### Resultaten per winkel")
st.dataframe(scen.set_index("shop_id")[["visitors","turnover","conv","spv","conv_new","spv_new","turnover_new","uplift_eur","gross_profit_uplift","payback_months"]])
