
import streamlit as st
import pandas as pd
from ui import kpi_card
from utils_pfmx import inject_css, api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct

st.set_page_config(page_title="Portfolio Benchmark", page_icon="📊", layout="wide")
inject_css(st)

st.markdown("### <span class='pill'>Retail Director</span> Portfolio Benchmark", unsafe_allow_html=True)
API_URL = st.secrets["API_URL"]

shop_input = st.text_input("Shop IDs (komma-gescheiden)", value="26304,26305,26306")

with st.expander("🎯 Targets voor demo", expanded=True):
    colT1, colT2 = st.columns(2)
    with colT1:
        conv_target = st.slider("Conversie-target (%)", 0, 60, 25, 1) / 100.0
    with colT2:
        spv_target = st.number_input("SPV-target (€)", min_value=0.0, value=45.0, step=1.0)

shops = [int(x.strip()) for x in shop_input.split(",") if x.strip().isdigit()]
period = st.selectbox("Periode", ["last_month","this_quarter","last_quarter","this_year","last_year"], index=0)

# Optional store metadata upload (type, sqm)
meta_file = st.file_uploader("Optioneel: upload store-metadata CSV (kolommen: shop_id, store_type, sqm)", type=["csv"])
meta = None
if meta_file:
    meta = pd.read_csv(meta_file)
    meta["shop_id"] = meta["shop_id"].astype(int)

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

summ = df.groupby("shop_id", as_index=False).agg(
    visitors=("count_in","sum"),
    turnover=("turnover","sum"),
    conv=("conversion_rate","mean"),
    spv=("sales_per_visitor","mean"),
)

if meta is not None:
    summ = summ.merge(meta, on="shop_id", how="left")

# KPI summary cards (portfolio averages vs targets)
c1, c2 = st.columns(2)
conv_mean = summ["conv"].mean()
spv_mean = summ["spv"].mean()
tone1 = "good" if conv_mean >= conv_target else "bad"
tone2 = "good" if spv_mean >= spv_target else "bad"
arrow1 = "↑" if tone1=="good" else "↓"
arrow2 = "↑" if tone2=="good" else "↓"
kpi_card("Gem. conversie", f"{arrow1} {fmt_pct(conv_mean)}", f"Target {fmt_pct(conv_target)}", tone=tone1)
kpi_card("Gem. SPV", f"{arrow2} {fmt_eur(spv_mean)}", f"Target {fmt_eur(spv_target)}", tone=tone2)

st.markdown("#### KPI's per winkel")
st.dataframe(summ.set_index("shop_id"))

# Benchmarks by type/sqm buckets
if meta is not None and "store_type" in summ.columns:
    st.markdown("#### Benchmark per store type")
    st.dataframe(summ.groupby("store_type").agg({"visitors":"sum","turnover":"sum","conv":"mean","spv":"mean"}))

if meta is not None and "sqm" in summ.columns:
    b = summ.copy()
    b["sqm_bucket"] = pd.cut(b["sqm"], bins=[0,150,300,600,20000], labels=["≤150","151-300","301-600",">600"])
    st.markdown("#### Benchmark per m²-klasse")
    st.dataframe(b.groupby("sqm_bucket").agg({"visitors":"sum","turnover":"sum","conv":"mean","spv":"mean"}))

# Underperformers list (relative to adjustable targets)
st.markdown("#### Onderpresteerders (lager dan targets)")
under = summ[(summ["conv"]<conv_target) & (summ["spv"]<spv_target)].copy()
st.dataframe(under.set_index("shop_id"))
