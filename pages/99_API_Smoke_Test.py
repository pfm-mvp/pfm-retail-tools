import streamlit as st
from shop_mapping import SHOP_NAME_MAP
from utils_pfmx import api_get_report, api_get_live_inside

st.set_page_config(page_title="API Smoke Test", page_icon="🧪", layout="wide")
st.title("🧪 API Smoke Test – Primary vs Fallback")

ids = list(SHOP_NAME_MAP.keys())
if not ids:
    st.warning("Geen shop_ids in SHOP_NAME_MAP."); st.stop()

outputs = ["count_in","conversion_rate","turnover","sales_per_visitor"]
test_ids = ids[:1]

# --- GET-REPORT ---
st.subheader("1️⃣ get-report test")
res_report = api_get_report("shops","last_week", test_ids, outputs, period_step="day")
st.code(res_report["_url"])
if "_data" in res_report:
    data = res_report["_data"]
    kpi_count = len(outputs)
    found_kpis = [k for k in outputs if k in str(data)]
    st.write(f"Variant: **{res_report['_variant']}** – {len(found_kpis)}/{kpi_count} KPI's gevonden.")
    with st.expander("Bekijk JSON"):
        st.json(data)

# --- LIVE-INSIDE ---
st.subheader("2️⃣ live-inside test")
res_live = api_get_live_inside(test_ids, source="locations")
st.code(res_live["_url"])
if "_data" in res_live:
    st.write(f"Variant: **{res_live['_variant']}**")
    with st.expander("Bekijk JSON"):
        st.json(res_live["_data"])