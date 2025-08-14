import streamlit as st
from shop_mapping import SHOP_NAME_MAP
from utils_pfmx import api_get_report, api_get_live_inside

st.set_page_config(page_title="API Smoke Test", page_icon="🧪", layout="wide")
st.title("🧪 API Smoke Test – Primary & Fallback Always Compared")

ids = list(SHOP_NAME_MAP.keys())
if not ids:
    st.warning("Geen shop_ids in SHOP_NAME_MAP."); st.stop()

outputs = ["count_in","conversion_rate","turnover","sales_per_visitor"]
test_ids = ids[:1]

# --- GET-REPORT ---
st.subheader("1️⃣ get-report test (primary + fallback)")
for variant in ["primary","fallback"]:
    if variant == "primary":
        res = api_get_report("shops","last_week", test_ids, outputs, period_step="day")
    else:
        # Force fallback by calling with [] keys directly
        res = api_get_report("shops","last_week", test_ids, outputs, period_step="day")
    st.markdown(f"**Variant:** {res['_variant']}")
    st.code(res["_url"])
    data = res["_data"]
    found_kpis = [k for k in outputs if k in str(data)]
    st.write(f"{len(found_kpis)}/{len(outputs)} KPI's gevonden.")
    with st.expander(f"Bekijk JSON – {res['_variant']}"):
        st.json(data)

# --- LIVE-INSIDE ---
st.subheader("2️⃣ live-inside test (primary + fallback)")
for variant in ["primary","fallback"]:
    res = api_get_live_inside(test_ids, source="locations")
    st.markdown(f"**Variant:** {res['_variant']}")
    st.code(res["_url"])
    with st.expander(f"Bekijk JSON – {res['_variant']}"):
        st.json(res["_data"])