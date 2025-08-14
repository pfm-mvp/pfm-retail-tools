import streamlit as st
import pandas as pd
import numpy as np
from shop_mapping import SHOP_NAME_MAP
from utils_pfmx import inject_css, api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct, friendly_error

st.set_page_config(page_title="Executive ROI Scenarios", page_icon="💼", layout="wide")
inject_css()

ids = list(SHOP_NAME_MAP.keys())
period = st.selectbox("Periode", ["last_month","this_quarter","last_quarter","this_year","last_year"], index=0)

st.markdown("### 🎯 Targets (demo)")
c1,c2,c3,c4 = st.columns(4)
with c1: conv_add = st.slider("Conversie uplift (+pp)", 0.0, 0.20, 0.05, 0.01)
with c2: spv_uplift = st.slider("SPV‑uplift (%)", 0, 50, 10, 1) / 100.0
with c3: gross_margin = st.slider("Brutomarge (%)", 20, 80, 55, 1) / 100.0
with c4: capex = st.number_input("CAPEX per store (€)", min_value=0, value=1500, step=100)
payback_target = st.slider("Payback‑target (mnd)", 6, 24, 12, 1)

params = [("source","shops"), ("period", period)]
for sid in ids: params.append(("data[]", sid))
for k in ["count_in","conversion_rate","turnover","sales_per_visitor"]:
    params.append(("data_output[]", k))

js = api_get_report(params, st.secrets["API_URL"])
if not friendly_error(js, period):
    df = normalize_vemcount_daylevel(js)
    if df.empty:
        st.info("Geen data voor de gekozen periode.")
        st.stop()

    base = df.groupby("shop_id", as_index=False).agg(
        visitors=("count_in","sum"),
        turnover=("turnover","sum"),
        conv=("conversion_rate","mean"),
        spv=("sales_per_visitor","mean"),
    )

    scen = base.copy()
    scen["conv_new"] = np.clip(scen["conv"] + conv_add, 0, 1)
    scen["spv_new"] = scen["spv"] * (1 + spv_uplift)
    scen["tickets"] = scen["visitors"] * scen["conv"]
    scen["tickets_new"] = scen["visitors"] * scen["conv_new"]
    scen["turnover_new"] = scen["tickets_new"] * scen["spv_new"]
    scen["uplift_eur"] = scen["turnover_new"] - scen["turnover"]
    scen["gross_profit_uplift"] = scen["uplift_eur"] * gross_margin
    scen["payback_months"] = np.where(scen["gross_profit_uplift"]>0, capex / (scen["gross_profit_uplift"]/12), np.nan)

    good = (scen["payback_months"] <= payback_target)
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='pfm-card'><div>💶 Extra omzet (periode)</div><div style='font-size:28px'>{fmt_eur(scen['uplift_eur'].sum())}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='pfm-card'><div>🏦 Extra brutowinst</div><div style='font-size:28px'>{fmt_eur(scen['gross_profit_uplift'].sum())}</div></div>", unsafe_allow_html=True)
    med_pb = scen["payback_months"].median()
    icon = "↑" if good.mean()>0.5 else "↓"
    c3.markdown(f"<div class='pfm-card'><div>⏳ Median Payback</div><div style='font-size:28px'>{icon} {med_pb:.1f} mnd</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='pfm-card'><div>🏬 Winkels</div><div style='font-size:28px'>{len(scen)}</div></div>", unsafe_allow_html=True)

    st.markdown("#### Resultaten per winkel")
    st.dataframe(scen.set_index("shop_id")[["visitors","turnover","conv","spv","conv_new","spv_new","turnover_new","uplift_eur","gross_profit_uplift","payback_months"]])