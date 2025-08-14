
import streamlit as st
import pandas as pd
import time
from ui import inject
inject()

try:
    from shop_mapping import shop_mapping
except Exception:
    shop_mapping = {"Putte (Iedereen)": 37953, "Den Bosch (Iedereen)": 37952}

from utils_pfmx import api_get_report, api_get_live_inside, normalize_vemcount_daylevel, fmt_eur, fmt_pct

st.set_page_config(page_title="Store Live Ops", page_icon="🟢", layout="wide")
st.markdown("### <span class='pill'>Store Manager</span> Live winkelbeeld & dagprestatie", unsafe_allow_html=True)

API_URL = st.secrets["API_URL"]
LIVE_URL = st.secrets.get("LIVE_URL")

col0, col1 = st.columns([2,1])
with col0:
    shop_name = st.selectbox("Kies winkel", list(shop_mapping.keys()))
with col1:
    source = st.radio("Bron", ["zones","locations"], index=0)

shop_id = shop_mapping[shop_name]
shops = [int(shop_id)]

colA, colB, colC = st.columns(3)
refresh = colA.checkbox("Auto-refresh", value=False)
interval = colB.slider("Interval (sec)", 5, 60, 10)
capacity = colC.number_input("Capaciteit (optioneel)", min_value=0, value=0, step=10)

live_placeholder = st.empty()

def render_live():
    try:
        live_json = api_get_live_inside(source, shops, API_URL, LIVE_URL)
        data = live_json.get("data") or live_json
        inside = 0
        if isinstance(data, dict):
            # probeer geselecteerde id direct te pakken, anders som over keys
            node = data.get(str(shop_id))
            if isinstance(node, dict):
                inside = node.get("inside") or node.get("count_inside") or node.get("current") or 0
            else:
                inside = sum(v.get("inside",0) if isinstance(v, dict) else 0 for v in data.values())
        occ = (inside / capacity) if capacity else None
        c1, c2, c3 = st.columns(3)
        c1.metric("Nu binnen", int(inside))
        c2.metric("Bezettingsgraad", fmt_pct(occ) if occ is not None else "—")
        c3.metric("Winkel", shop_name)
        if occ and occ > 0.8:
            st.warning("Druk! Overweeg extra bemensing of wachtrijmanagement.")
    except Exception as e:
        st.error(f"Live data niet beschikbaar: {e}")

def render_day_kpis():
    try:
        params = [("source", source), ("period", "today")]
        for sid in shops:
            params.append(("data", sid))
        for k in ["count_in","conversion_rate","turnover","sales_per_visitor"]:
            params.append(("data_output", k))
        js = api_get_report(params, API_URL)
        df = normalize_vemcount_daylevel(js)
        if df.empty:
            st.info("Geen dagdata.")
            return
        d0 = df.groupby("shop_id", as_index=False).agg(
            count_in=("count_in","sum"),
            turnover=("turnover","sum"),
            conversion_rate=("conversion_rate","mean"),
            sales_per_visitor=("sales_per_visitor","mean"),
        )
        a,b,c,d = st.columns(4)
        a.metric("Bezoekers vandaag", int(d0['count_in'].sum()))
        b.metric("Conversie", fmt_pct(d0['conversion_rate'].mean()))
        c.metric("Omzet", fmt_eur(d0['turnover'].sum()))
        d.metric("SPV", fmt_eur(d0['sales_per_visitor'].mean()))
        st.dataframe(d0.set_index("shop_id"))
    except Exception as e:
        st.error(f"Dag-KPI's niet beschikbaar: {e}")

render_live()
render_day_kpis()

if refresh:
    while True:
        time.sleep(interval)
        render_live()
