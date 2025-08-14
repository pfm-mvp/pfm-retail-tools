import streamlit as st
from utils_pfmx import inject_css
from typing import Optional

st.set_page_config(page_title="PFM Retail Performance Suite", page_icon="🧭", layout="wide")
inject_css()

st.markdown('''
<div style="display:flex;align-items:center;gap:12px;margin:8px 0 12px 0;">
  <div style="width:12px;height:32px;background:#762181;border-radius:3px;"></div>
  <h2 style="margin:0;">PFM Retail Performance Suite</h2>
</div>
<p style="color:#555;margin-top:-6px;">Unlocking Location Potential — live ops, regional radar, portfolio benchmarks & ROI scenarios.</p>
''', unsafe_allow_html=True)

def card(role, title, desc, btn_label, target_page, key):
    st.markdown(f'''
    <div class="pfm-card">
      <div style="font-size:14px;color:#762181;font-weight:700;margin-bottom:6px;">{role}</div>
      <div style="font-size:22px;font-weight:700;">{title}</div>
      <div style="color:#666;margin-top:4px;">{desc}</div>
    </div>
    ''', unsafe_allow_html=True)
    if st.button(btn_label, key=key, type="primary"):
        st.switch_page(target_page)

col1, spacer, col2 = st.columns([1, 0.06, 1])
with col1:
    card("Store Manager", "Store Live Ops",
         "Live bezetting, drukte en dag‑KPI's van één vestiging.",
         "Open app", "pages/01_Store_Live_Ops.py", "open_live_ops")
with col2:
    card("Area / Region Manager", "Region Performance Radar",
         "Weekdag‑profielen, conversie × SPV quadrant, zwakste dagen.",
         "Open app", "pages/02_Region_Performance_Radar.py", "open_region")

col3, spacer2, col4 = st.columns([1, 0.06, 1])
with col3:
    card("Retail Director", "Portfolio Benchmark",
         "Benchmark per type en m²; lijst onderpresteerders.",
         "Open app", "pages/03_Portfolio_Benchmark.py", "open_benchmark")
with col4:
    card("CCO / Executive", "Executive ROI Scenarios",
         "Conversie‑targets, SPV‑uplift, brutomarge en payback.",
         "Open app", "pages/04_Executive_ROI_Scenarios.py", "open_roi")

st.markdown("---")
st.caption("PFM brand: paars #762181, rood #F04438, tint #F9F7FB.")
