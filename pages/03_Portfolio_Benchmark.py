import streamlit as st
import pandas as pd
from shop_mapping import SHOP_NAME_MAP
from utils_pfmx import inject_css, api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct, friendly_error

st.set_page_config(page_title="Portfolio Benchmark", page_icon="📊", layout="wide")
inject_css()

ids = list(SHOP_NAME_MAP.keys())
period = st.selectbox("Periode", ["last_month","this_quarter","last_quarter","this_year","last_year"], index=0)

params = [("source","locations"), ("period", period)]
for sid in ids: params.append(("data", sid))
for k in ["count_in","conversion_rate","turnover","sales_per_visitor"]:
    params.append(("data_output", k))

js = api_get_report(params, st.secrets["API_URL"])
if not friendly_error(js, period):
    df = normalize_vemcount_daylevel(js)
    if df.empty:
        st.info("Geen data voor de gekozen periode.")
        st.stop()

    summ = df.groupby("shop_id", as_index=False).agg(
        visitors=("count_in","sum"),
        turnover=("turnover","sum"),
        conv=("conversion_rate","mean"),
        spv=("sales_per_visitor","mean"),
    )
    st.markdown("#### KPI's per winkel")
    st.dataframe(summ.set_index("shop_id"))

    st.markdown("### 🎯 Targets (demo)")
    t1, t2 = st.columns(2)
    with t1: conv_target = st.slider("Conversie‑target (%)", 0, 50, 25, 1) / 100.0
    with t2: spv_target = st.number_input("SPV‑target (€)", min_value=0, value=45, step=1)

    under = summ[(summ["conv"] < conv_target) & (summ["spv"] < spv_target)]
    st.markdown("#### Onderpresteerders t.o.v. targets")
    st.dataframe(under.set_index("shop_id"))