import streamlit as st
import pandas as pd
from shop_mapping import SHOP_NAME_MAP
from utils_pfmx import (
    inject_css,
    api_get_live_inside,
    api_get_report,
    normalize_vemcount_daylevel,
    fmt_eur,
    fmt_pct,
    friendly_error,
    build_params_reports_brackets,   # ← nieuw
)

st.set_page_config(page_title="Store Live Ops", page_icon="🟢", layout="wide")
inject_css()

# --- Selectie
name_by_id = SHOP_NAME_MAP
id_by_name = {v: k for k, v in name_by_id.items()}
shop_name = st.selectbox("Kies winkel", list(id_by_name.keys()))
shop_id = id_by_name[shop_name]

st.markdown("### 🎯 Targets (demo)")
colT1, colT2 = st.columns(2)
with colT1:
    conv_target = st.slider("Conversie‑target (%)", 0, 50, 25, 1) / 100.0
with colT2:
    visitors_target = st.number_input("Bezoekerstarget (deze week)", min_value=0, value=1200, step=50)

# --- LIVE INSIDE (robuust: POST→GET & meerdere URL-kandidaten)
st.markdown("#### Live inside")
live_js = api_get_live_inside([shop_id], source="locations")
if friendly_error(live_js, "live-inside"):
    st.stop()

live_data = live_js.get("data") or {}
inside = 0
if isinstance(live_data, dict):
    blob = live_data.get(str(shop_id)) or live_data.get(shop_id)
    if isinstance(blob, dict):
        inside = blob.get("inside") or blob.get("count_inside") or blob.get("current") or 0

c1, c2 = st.columns(2)
c1.metric("👥 Nu binnen", int(inside))
c2.markdown("&nbsp;", unsafe_allow_html=True)

# --- DAG & WEEK KPI's (met brackets data[] en data_output[])
st.markdown("#### Dag & Week KPI's")

# Yesterday
params_y = build_params_reports_brackets(
    source="shops",
    period="yesterday",
    data_ids=[shop_id],
    outputs=["count_in", "conversion_rate", "turnover", "sales_per_visitor"],
)
js_y = api_get_report(params_y)
if friendly_error(js_y, "yesterday"):
    st.stop()

# This week
params_tw = build_params_reports_brackets(
    source="shops", period="this_week", data_ids=[shop_id],
    outputs=["count_in", "conversion_rate", "turnover", "sales_per_visitor"]
)
js_tw = api_get_report(params_tw)
if friendly_error(js_tw, "this_week"):
    st.stop()

# Last week
params_lw = build_params_reports_brackets(
    source="shops", period="last_week", data_ids=[shop_id],
    outputs=["count_in", "conversion_rate", "turnover", "sales_per_visitor"]
)
js_lw = api_get_report(params_lw)
if friendly_error(js_lw, "last_week"):
    st.stop()

# --- KPIs renderen
df_y  = normalize_vemcount_daylevel(js_y)
df_tw = normalize_vemcount_daylevel(js_tw)
df_lw = normalize_vemcount_daylevel(js_lw)

conv_y = float(df_y["conversion_rate"].mean()) if not df_y.empty else 0.0
vis_tw = int(df_tw["count_in"].sum()) if not df_tw.empty else 0
vis_lw = int(df_lw["count_in"].sum()) if not df_lw.empty else 0
wow = ((vis_tw - vis_lw) / vis_lw) if vis_lw else 0.0

c1, c2, c3 = st.columns(3)
conv_class = "kpi-good" if conv_y >= conv_target else "kpi-bad"
c1.markdown(
    f"<div class='pfm-card'><div>🛒 Conversie (gisteren)</div>"
    f"<div class='{conv_class}' style='font-size:28px'>{fmt_pct(conv_y)}</div></div>",
    unsafe_allow_html=True,
)

vis_class = "kpi-good" if vis_tw >= visitors_target else "kpi-bad"
c2.markdown(
    f"<div class='pfm-card'><div>👣 Bezoekers (deze week)</div>"
    f"<div class='{vis_class}' style='font-size:28px'>{vis_tw:,}</div></div>".replace(",", "."),
    unsafe_allow_html=True,
)

wow_icon = "↑" if wow >= 0 else "↓"
wow_class = "kpi-good" if wow >= 0 else "kpi-bad"
c3.markdown(
    f"<div class='pfm-card'><div>WoW (visitors)</div>"
    f"<div class='{wow_class}' style='font-size:28px'>{wow_icon} {fmt_pct(abs(wow))}</div></div>",
    unsafe_allow_html=True,
)
