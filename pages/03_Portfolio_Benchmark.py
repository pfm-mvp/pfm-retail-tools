
import streamlit as st
import pandas as pd
from ui import inject
inject()

from utils_pfmx import api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct

st.set_page_config(page_title="Portfolio Benchmark", page_icon="📊", layout="wide")
st.markdown("### <span class='pill'>Retail Director</span> Portfolio Benchmark", unsafe_allow_html=True)
API_URL = st.secrets["API_URL"]

shops_text = st.text_input("Shop IDs (komma-gescheiden)", value="26304,26305,26306")
shops = [int(x.strip()) for x in shops_text.split(",") if x.strip().isdigit()]
period = st.selectbox("Periode", ["last_month","this_quarter","last_quarter","this_year","last_year"], index=0)

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
st.markdown("#### KPI's per winkel")
st.dataframe(summ.set_index("shop_id"))

if meta is not None and "store_type" in summ.columns:
    st.markdown("#### Benchmark per store type")
    st.dataframe(summ.groupby("store_type").agg({"visitors":"sum","turnover":"sum","conv":"mean","spv":"mean"}))

if meta is not None and "sqm" in summ.columns:
    b = summ.copy()
    b["sqm_bucket"] = pd.cut(b["sqm"], bins=[0,150,300,600,20000], labels=["≤150","151-300","301-600",">600"])
    st.markdown("#### Benchmark per m²-klasse")
    st.dataframe(b.groupby("sqm_bucket").agg({"visitors":"sum","turnover":"sum","conv":"mean","spv":"mean"}))

conv_q1 = summ["conv"].quantile(0.25)
spv_q1 = summ["spv"].quantile(0.25)
under = summ[(summ["conv"]<=conv_q1) & (summ["spv"]<=spv_q1)].copy()
st.markdown("#### Onderpresteerders (lage conversie en lage SPV)")
st.dataframe(under.set_index("shop_id"))
