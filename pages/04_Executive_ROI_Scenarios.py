
import streamlit as st
import pandas as pd
import numpy as np
from ui import inject
inject()

from utils_pfmx import api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct

st.set_page_config(page_title="Executive ROI Scenarios", page_icon="💼", layout="wide")
st.markdown("### <span class='pill'>CCO / Executive</span> ROI & Scenario Dashboard", unsafe_allow_html=True)
API_URL = st.secrets["API_URL"]

shops_text = st.text_input("Shop IDs (komma-gescheiden)", value="26304,26305,26306")
shops = [int(x.strip()) for x in shops_text.split(",") if x.strip().isdigit()]
period = st.selectbox("Periode", ["last_month","this_quarter","last_quarter","this_year","last_year"], index=0)

col1,col2,col3,col4 = st.columns(4)
conv_target = col1.slider("Conversie-target (+pp)", 0.0, 0.20, 0.05, 0.01)
spv_uplift = col2.slider("SPV-uplift (%)", 0, 50, 10, 1) / 100.0
gross_margin = col3.slider("Brutomarge (%)", 20, 80, 55, 1) / 100.0
capex = col4.number_input("CAPEX per store (€)", min_value=0, value=1500, step=100)

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

base = df.groupby("shop_id", as_index=False).agg(
    visitors=("count_in","sum"),
    turnover=("turnover","sum"),
    conv=("conversion_rate","mean"),
    spv=("sales_per_visitor","mean"),
)
scen = base.copy()
scen["conv_new"] = np.clip(scen["conv"] + conv_target, 0, 1)
scen["spv_new"] = scen["spv"] * (1 + spv_uplift)
scen["tickets"] = scen["visitors"] * scen["conv"]
scen["tickets_new"] = scen["visitors"] * scen["conv_new"]
scen["turnover_new"] = scen["tickets_new"] * scen["spv_new"]
scen["uplift_eur"] = scen["turnover_new"] - scen["turnover"]
scen["gross_profit_uplift"] = scen["uplift_eur"] * gross_margin
days = max(len(df["date"].unique()), 1)
scen["payback_months"] = np.where(scen["gross_profit_uplift"]>0, capex / (scen["gross_profit_uplift"]/days * 12), np.nan)

a,b,c,d = st.columns(4)
a.metric("Extra omzet (periode)", fmt_eur(scen['uplift_eur'].sum()))
b.metric("Extra brutowinst", fmt_eur(scen['gross_profit_uplift'].sum()))
c.metric("Median Payback", f"{scen['payback_months'].median():.1f} mnd" if scen['payback_months'].notna().any() else "n.v.t.")
d.metric("Winkels", len(scen))

st.markdown("#### Resultaten per winkel")
st.dataframe(scen.set_index("shop_id")[["visitors","turnover","conv","spv","conv_new","spv_new","turnover_new","uplift_eur","gross_profit_uplift","payback_months"]])
