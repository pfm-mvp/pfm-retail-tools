
import streamlit as st
st.set_page_config(page_title="PFM Retail Performance Suite", page_icon="🧭", layout="wide")
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin:8px 0 12px 0;">
  <div style="width:12px;height:32px;background:#762181;border-radius:3px;"></div>
  <h2 style="margin:0;">PFM Retail Performance Suite</h2>
</div>
<p style="color:#555;margin-top:-6px;">Unlocking Location Potential — live operations, regional radar, portfolio benchmarks & ROI scenarios.</p>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div style="border:1px solid #eee;border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05)">
      <div style="font-size:14px;color:#762181;font-weight:700;margin-bottom:6px;">Store Manager</div>
      <div style="font-size:22px;font-weight:700;">Store Live Ops</div>
      <div style="color:#666;margin-top:4px;">Live bezetting, drukte en dag-KPI's van één vestiging.</div>
      <div style="margin-top:12px;">
        <a href="./pages/01_Store_Live_Ops.py" target="_self" style="background:#762181;color:#fff;padding:8px 12px;border-radius:12px;text-decoration:none;">Open app</a>
      </div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div style="border:1px solid #eee;border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05)">
      <div style="font-size:14px;color:#762181;font-weight:700;margin-bottom:6px;">Area / Region Manager</div>
      <div style="font-size:22px;font-weight:700;">Region Performance Radar</div>
      <div style="color:#666;margin-top:4px;">Weekdag-profielen, conversie × SPV quadrant, zwakste dagen.</div>
      <div style="margin-top:12px;">
        <a href="./pages/02_Region_Performance_Radar.py" target="_self" style="background:#762181;color:#fff;padding:8px 12px;border-radius:12px;text-decoration:none;">Open app</a>
      </div>
    </div>
    """, unsafe_allow_html=True)

col3, col4 = st.columns(2)
with col3:
    st.markdown("""
    <div style="border:1px solid #eee;border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05)">
      <div style="font-size:14px;color:#762181;font-weight:700;margin-bottom:6px;">Retail Director</div>
      <div style="font-size:22px;font-weight:700;">Portfolio Benchmark</div>
      <div style="color:#666;margin-top:4px;">Benchmark per type en m²; lijst onderpresteerders.</div>
      <div style="margin-top:12px;">
        <a href="./pages/03_Portfolio_Benchmark.py" target="_self" style="background:#762181;color:#fff;padding:8px 12px;border-radius:12px;text-decoration:none;">Open app</a>
      </div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown("""
    <div style="border:1px solid #eee;border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05)">
      <div style="font-size:14px;color:#762181;font-weight:700;margin-bottom:6px;">CCO / Executive</div>
      <div style="font-size:22px;font-weight:700;">Executive ROI Scenarios</div>
      <div style="color:#666;margin-top:4px;">Conversie-targets, SPV-uplift, brutomarge en payback.</div>
      <div style="margin-top:12px;">
        <a href="./pages/04_Executive_ROI_Scenarios.py" target="_self" style="background:#762181;color:#fff;padding:8px 12px;border-radius:12px;text-decoration:none;">Open app</a>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("PFM brand: #762181 (primary), #F04438 (accent), #F9F7FB (tint).")
