
import streamlit as st
import pandas as pd
from ui import kpi_card
from utils_pfmx import inject_css, api_get_report, normalize_vemcount_daylevel, to_weekday_en, quad_plot, fmt_eur, fmt_pct

st.set_page_config(page_title="Region Performance Radar", page_icon="🧭", layout="wide")
inject_css(st)

st.markdown("### <span class='pill'>Area/Region Manager</span> Performance Radar", unsafe_allow_html=True)
API_URL = st.secrets["API_URL"]

shop_input = st.text_input("Shop IDs (komma-gescheiden)", value="26304,26305")

with st.expander("🎯 Targets voor demo", expanded=True):
    colT1, colT2 = st.columns(2)
    with colT1:
        conv_target = st.slider("Conversie-target (%)", 0, 60, 25, 1) / 100.0
    with colT2:
        spv_target = st.number_input("SPV-target (€)", min_value=0.0, value=45.0, step=1.0)

shops = [int(x.strip()) for x in shop_input.split(",") if x.strip().isdigit()]

# Default periode: this_month
period = st.selectbox("Periode", ["this_month","last_month","this_quarter","last_quarter","this_year","last_year"], index=0)

params = [("source","shops"), ("period", period)]
for sid in shops:
    params.append(("data", sid))
for k in ["count_in","conversion_rate","turnover","sales_per_visitor"]:
    params.append(("data_output", k))

js = api_get_report(params, API_URL)
df = normalize_vemcount_daylevel(js)

if df.empty:
    st.info("Geen data voor de gekozen periode/winkels.")
    st.stop()

df["weekday"] = to_weekday_en(df["date"])

# KPI rollups
roll = df.groupby(["shop_id","weekday"], as_index=False).agg(
    count_in=("count_in","sum"),
    conversion_rate=("conversion_rate","mean"),
    turnover=("turnover","sum"),
    sales_per_visitor=("sales_per_visitor","mean"),
)

# Quadrant
fig, xmean, ymean = quad_plot(roll, x="conversion_rate", y="sales_per_visitor", color="weekday",
                              title="Conversie vs SPV per weekdag (gemiddeld)")
st.plotly_chart(fig, use_container_width=True)
st.caption(f"Stippellijnen tonen gemiddelden: Conversie {fmt_pct(xmean)}, SPV {fmt_eur(ymean)}. Target-lijnen: Conv {fmt_pct(conv_target)}, SPV {fmt_eur(spv_target)}.")

# Summary KPI cards vs targets
c1, c2 = st.columns(2)
c1_tone = "good" if xmean >= conv_target else "bad"
c2_tone = "good" if ymean >= spv_target else "bad"
c1_arrow = "↑" if c1_tone=="good" else "↓"
c2_arrow = "↑" if c2_tone=="good" else "↓"
kpi_card("Gem. Conversie", f"{c1_arrow} {fmt_pct(xmean)}", f"Target {fmt_pct(conv_target)}", tone=c1_tone)
kpi_card("Gem. SPV", f"{c2_arrow} {fmt_eur(ymean)}", f"Target {fmt_eur(spv_target)}", tone=c2_tone)

# Top underperforming weekday per shop
low = (roll.sort_values(["shop_id","sales_per_visitor"])
          .groupby("shop_id", as_index=False).first()[["shop_id","weekday","sales_per_visitor","conversion_rate"]])
st.markdown("#### Zwakste dag per winkel (laagste SPV)")
st.dataframe(low.set_index("shop_id"))

# Overzicht per weekdag (alle winkels)
piv = roll.pivot_table(index="weekday", values=["count_in","turnover","conversion_rate","sales_per_visitor"],
                       aggfunc={"count_in":"sum","turnover":"sum","conversion_rate":"mean","sales_per_visitor":"mean"})
st.markdown("#### Overzicht per weekdag (alle winkels)")
st.dataframe(piv)
