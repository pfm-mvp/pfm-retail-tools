import streamlit as st
import pandas as pd
from shop_mapping import SHOP_NAME_MAP
from utils_pfmx import inject_css, api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct, friendly_error

st.set_page_config(page_title="Portfolio Benchmark", page_icon="📊", layout="wide")
inject_css()

ids = list(SHOP_NAME_MAP.keys())
params = [("source","shops"), ("period","this_quarter")]
for sid in ids: params.append(("data", sid))
for k in ["count_in","conversion_rate","turnover","sales_per_visitor"]:
    params.append(("data_output", k))

js = api_get_report(params, st.secrets["API_URL"])
if friendly_error(js, "this_quarter"):
    st.stop()

df = normalize_vemcount_daylevel(js)
if df.empty:
    st.info("Geen data.")
    st.stop()

st.write(df.head())
