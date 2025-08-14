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
    build_params_reports_brackets,
)

st.set_page_config(page_title="Store Live Ops", page_icon="🟢", layout="wide")
inject_css()

# Selectie
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

# Live inside (fout stopt NIET de pagina)
st.markdown("#### Live inside")
live_js = api_get_live_inside([shop_id], source="locations")
live_error = friendly_error(live_js, "live-inside")
inside = 0
if not live_error and isinstance(live_js, dict):
    live_data = live_js.get("data") or {}
    if isinstance(live_data, dict):
        blob = live_data.get(str(shop_id)) or live_data.get(shop_id)
        if isinstance(blob, dict):
            inside = blob.get("inside") or blob.get("count_inside") or blob.get("current") or 0

c1, c2 = st.columns(2)
c1.metric("👥 Nu binnen", int(inside))
c2.markdown("&nbsp;", unsafe_allow_html=True)

# Dag & Week KPI's (met brackets)
st.markdown("#### Dag & Week KPI's")
outputs = ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]

# Yesterday
params_y = build_params_reports_brackets("shops", "yesterday", [shop_id], outputs)
js_y = api_get_report(params_y)
y_error = friendly_error(js_y, "yesterday")

# This week
params_tw = build_params_reports_brackets("shops", "this_week", [shop_id], outputs)
js_tw = api_get_report(params_tw)
tw_error = friendly_error(js_tw, "this_week")

# Last week
params_lw = build_params_reports_brackets("shops", "last_week", [shop_id], outputs)
js_lw = api_get_report(params_lw)
lw_error = friendly_error(js_lw, "last_week")

# Dataframes (safe fallbacks)
df_y  = normalize_vemcount_daylevel(js_y)  if not y_error  else pd.DataFrame(columns=["conversion_rate"])
df_tw = normalize_vemcount_daylevel(js_tw) if not tw_error else pd.DataFrame(columns=["count_in"])
df_lw = normalize_vemcount_daylevel(js_lw) if not lw_error else pd.DataFrame(columns=["count_in"])

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
