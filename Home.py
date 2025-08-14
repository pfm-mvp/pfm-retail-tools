import streamlit as st

st.set_page_config(page_title="PFM Retail Performance Suite", page_icon="🧭", layout="wide")

st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin:8px 0 12px 0;">
  <div style="width:12px;height:32px;background:#762181;border-radius:3px;"></div>
  <h2 style="margin:0;">PFM Retail Performance Suite</h2>
</div>
<p style="color:#555;margin-top:-6px;">Unlocking Location Potential — live operations, regional radar, portfolio benchmarks & ROI scenarios.</p>
""", unsafe_allow_html=True)

def card(role, title, desc, btn_label, target_page, key):
    st.markdown(
        f"""
        <div style="border:1px solid #e6e6e6;border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05);">
          <div style="font-size:14px;color:#762181;font-weight:700;margin-bottom:6px;">{role}</div>
          <div style="font-size:22px;font-weight:700;">{title}</div>
          <div style="color:#666;margin-top:4px;">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button(btn_label, key=key, type="primary"):
        st.switch_page(target_page)

# Rij 1
col1, spacer, col2 = st.columns([1, 0.06, 1])
with col1:
    card(
        role="Store Manager",
        title="Store Live Ops",
        desc="Live bezetting, drukte en dag‑KPI's van één vestiging.",
        btn_label="Open app",
        target_page="pages/01_Store_Live_Ops.py",
        key="open_live_ops"
    )
with col2:
    card(
        role="Area / Region Manager",
        title="Region Performance Radar",
        desc="Weekdag‑profielen, conversie × SPV quadrant, zwakste dagen.",
        btn_label="Open app",
        target_page="pages/02_Region_Performance_Radar.py",
        key="open_region"
    )

# Rij 2
col3, spacer2, col4 = st.columns([1, 0.06, 1])
with col3:
    card(
        role="Retail Director",
        title="Portfolio Benchmark",
        desc="Benchmark per type en m²; lijst onderpresteerders.",
        btn_label="Open app",
        target_page="pages/03_Portfolio_Benchmark.py",
        key="open_benchmark"
    )
with col4:
    card(
        role="CCO / Executive",
        title="Executive ROI Scenarios",
        desc="Conversie‑targets, SPV‑uplift, brutomarge en payback.",
        btn_label="Open app",
        target_page="pages/04_Executive_ROI_Scenarios.py",
        key="open_roi"
    )

st.markdown("---")
st.caption("PFM brand: #762181 (primary), #F04438 (accent), #F9F7FB (tint).")
