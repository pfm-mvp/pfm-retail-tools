
import streamlit as st
import pandas as pd
import time
from ui import kpi_card
from utils_pfmx import inject_css, api_get_report, api_get_live_inside, normalize_vemcount_daylevel, fmt_eur, fmt_pct

st.set_page_config(page_title="Store Live Ops", page_icon="🟢", layout="wide")
inject_css(st)

st.markdown("### <span class='pill'>Store Manager</span> Live winkelbeeld & dagprestatie", unsafe_allow_html=True)

API_URL = st.secrets["API_URL"]
LIVE_URL = st.secrets.get("LIVE_URL")  # optional override

# Store selector
try:
    from shop_mapping import shop_mapping
except Exception:
    shop_mapping = {"Putte (Iedereen)": 37953, "Den Bosch (Iedereen)": 37952}

col0, col1 = st.columns([2,1])
with col0:
    shop_name = st.selectbox("Kies winkel", list(shop_mapping.keys()))
with col1:
    source = st.radio("Bron", options=["zones", "locations"], index=0,
                      help="Gebruik 'zones' wanneer je mapping zone-IDs bevat (bijv. 'Iedereen').")

shop_id = shop_mapping[shop_name]
shops = [int(shop_id)]

# Targets
with st.expander("🎯 Targets voor demo", expanded=True):
    colt1, colt2 = st.columns(2)
    with colt1:
        conv_target = st.slider("Conversie-target (%)", 0, 60, 25, 1) / 100.0
    with colt2:
        weekly_visitors_target = st.number_input("Bezoekers target (deze week)", min_value=0, value=1500, step=50)

colA, colB, colC = st.columns(3)
with colA:
    refresh = st.checkbox("Auto-refresh live", value=False)
with colB:
    interval = st.slider("Interval (sec)", 5, 60, 10)
with colC:
    capacity = st.number_input("Capaciteit (optioneel)", min_value=0, value=0, step=10)

live_placeholder = st.empty()

def render_live():
    try:
        live_json = api_get_live_inside(source, shops, API_URL, LIVE_URL)
        data = live_json.get("data") or live_json
        total_inside = 0
        if isinstance(data, dict):
            v = data.get(str(shop_id)) or data.get(shop_id) or {}
            inside = v.get("inside") or v.get("count_inside") or v.get("current") or 0
            total_inside = inside if isinstance(inside, (int,float)) else 0
        occ = (total_inside / capacity) if capacity else None
        with live_placeholder.container():
            c1, c2, c3 = st.columns(3)
            kpi_card("Now", f"👥 {int(total_inside)}", "Nu binnen", tone="primary")
            if occ is not None:
                kpi_card("Occ", f"🧮 {fmt_pct(occ)}", "Bezettingsgraad", tone=("good" if occ<=0.8 else "bad"))
            kpi_card("Shop", f"🏬 1", "Geselecteerde winkel", tone="neutral")
            if occ and occ > 0.8:
                st.warning("Druk! Overweeg extra bemensing of wachtrijmanagement.")
    except Exception as e:
        st.error(f"Live data niet beschikbaar: {e}")

def fetch_period(params):
    js = api_get_report(params, API_URL)
    return normalize_vemcount_daylevel(js)

def render_ops_kpis():
    # Conversie gisteren
    params_y = [("source", source), ("period","yesterday"), ("data", shop_id),
                ("data_output","count_in"), ("data_output","conversion_rate"),
                ("data_output","turnover"), ("data_output","sales_per_visitor")]
    df_y = fetch_period(params_y)

    # Deze week & vorige week
    params_tw = [("source", source), ("period","this_week"), ("data", shop_id),
                ("data_output","count_in"), ("data_output","conversion_rate")]
    params_lw = [("source", source), ("period","last_week"), ("data", shop_id),
                ("data_output","count_in"), ("data_output","conversion_rate")]
    df_tw = fetch_period(params_tw)
    df_lw = fetch_period(params_lw)

    conv_y = df_y["conversion_rate"].mean() if not df_y.empty else None
    conv_tw = df_tw["conversion_rate"].mean() if not df_tw.empty else None
    conv_lw = df_lw["conversion_rate"].mean() if not df_lw.empty else None
    vis_tw = df_tw["count_in"].sum() if not df_tw.empty else 0

    delta_conv = None
    if conv_tw is not None and conv_lw is not None:
        delta_conv = (conv_tw - conv_lw)

    c1,c2,c3,c4 = st.columns(4)
    # Conversie gisteren
    if conv_y is not None:
        tone = "good" if conv_y >= conv_target else "bad"
        arrow = "↑" if tone=="good" else "↓"
        kpi_card("Conv (gisteren)", f"{arrow} {fmt_pct(conv_y)}", f"Target {fmt_pct(conv_target)}", tone=tone)
    else:
        kpi_card("Conv (gisteren)", "—", "Geen data", tone="neutral")

    # Conversie week vs vorige week
    if delta_conv is not None:
        tone = "good" if delta_conv >= 0 else "bad"
        arrow = "↑" if delta_conv >= 0 else "↓"
        kpi_card("Conv Δ (week)", f"{arrow} {fmt_pct(delta_conv)}", "Deze week vs vorige week", tone=tone)
    else:
        kpi_card("Conv Δ (week)", "—", "—", tone="neutral")

    # Bezoekers deze week
    tone = "good" if vis_tw >= weekly_visitors_target else "bad"
    arrow = "↑" if vis_tw >= weekly_visitors_target else "↓"
    kpi_card("Bezoekers (week)", f"{arrow} {vis_tw:,}".replace(",", "."), f"Target {weekly_visitors_target:,}".replace(",", "."), tone=tone)

    # SPV gisteren (optioneel extra context)
    spv_y = df_y["sales_per_visitor"].mean() if not df_y.empty else None
    if spv_y is not None:
        kpi_card("SPV (gisteren)", f"€{spv_y:,.2f}".replace(",", ".").replace(".", ",", 1), "Sales per visitor", tone="neutral")
    else:
        kpi_card("SPV (gisteren)", "—", "Geen data", tone="neutral")

render_live()
render_ops_kpis()

if refresh:
    while True:
        time.sleep(interval)
        render_live()
