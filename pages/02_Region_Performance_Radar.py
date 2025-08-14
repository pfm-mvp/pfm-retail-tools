import streamlit as st
import pandas as pd
import plotly.express as px
from shop_mapping import SHOP_NAME_MAP
from utils_pfmx import inject_css, api_get_report, normalize_vemcount_daylevel, fmt_eur, fmt_pct, friendly_error

st.set_page_config(page_title="Region Performance Radar", page_icon="🧭", layout="wide")
inject_css()

ids = list(SHOP_NAME_MAP.keys())
st.markdown("### 🎯 Targets (demo)")
t1, t2 = st.columns(2)
with t1: conv_target = st.slider("Conversie‑target (%)", 0, 50, 25, 1) / 100.0
with t2: spv_target = st.number_input("SPV‑target (€)", min_value=0, value=45, step=1)

period = st.selectbox("Periode", ["this_month","last_month","this_quarter","last_quarter"], index=0)

params = [("source","shops"), ("period", period)]
for sid in ids: params.append(("data[]", sid))
for k in ["count_in","conversion_rate","turnover","sales_per_visitor"]:
    params.append(("data_output[]", k))

js = api_get_report(params, st.secrets["API_URL"])
if not friendly_error(js, period):
    df = normalize_vemcount_daylevel(js)
    if df.empty:
        st.info("Geen data voor de gekozen periode.")
        st.stop()

    df["weekday"] = pd.to_datetime(df["date"]).dt.day_name()
    roll = df.groupby(["shop_id","weekday"], as_index=False).agg(
        count_in=("count_in","sum"),
        conversion_rate=("conversion_rate","mean"),
        sales_per_visitor=("sales_per_visitor","mean"),
        turnover=("turnover","sum")
    )
    fig = px.scatter(roll, x="conversion_rate", y="sales_per_visitor", color="weekday",
                     hover_data=["shop_id","weekday","count_in","turnover"],
                     title="Conversie vs SPV per weekdag")
    st.plotly_chart(fig, use_container_width=True)

    low = (roll.sort_values(["shop_id","sales_per_visitor"])
              .groupby("shop_id", as_index=False).first()[["shop_id","weekday","sales_per_visitor","conversion_rate"]])
    low["conv_ok"] = low["conversion_rate"] >= conv_target
    low["spv_ok"] = low["sales_per_visitor"] >= spv_target
    st.markdown("#### Zwakste dag per winkel (laagste SPV)")
    st.dataframe(low.set_index("shop_id"))