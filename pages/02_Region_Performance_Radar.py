
import streamlit as st
import pandas as pd
import plotly.express as px
from ui import inject
inject()

from utils_pfmx import api_get_report, normalize_vemcount_daylevel, to_weekday_en, fmt_eur, fmt_pct

st.set_page_config(page_title="Region Performance Radar", page_icon="🧭", layout="wide")
st.markdown("### <span class='pill'>Area/Region Manager</span> Performance Radar", unsafe_allow_html=True)

API_URL = st.secrets["API_URL"]

shops_text = st.text_input("Shop IDs (komma-gescheiden)", value="26304,26305")
shops = [int(x.strip()) for x in shops_text.split(",") if x.strip().isdigit()]
period = st.selectbox("Periode", ["last_week","this_month","last_month","this_quarter","last_quarter","this_year","last_year"], index=1)

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

roll = df.groupby(["shop_id","weekday"], as_index=False).agg(
    count_in=("count_in","sum"),
    conversion_rate=("conversion_rate","mean"),
    turnover=("turnover","sum"),
    sales_per_visitor=("sales_per_visitor","mean"),
)

fig = px.scatter(
    roll, x="conversion_rate", y="sales_per_visitor", color="weekday",
    hover_data=["shop_id","weekday"],
    title="Conversie vs SPV per weekdag (gemiddeld)"
)
fig.add_hline(y=roll["sales_per_visitor"].mean(), line_dash="dot")
fig.add_vline(x=roll["conversion_rate"].mean(), line_dash="dot")
st.plotly_chart(fig, use_container_width=True)

low = (roll.sort_values(["shop_id","sales_per_visitor"])
          .groupby("shop_id", as_index=False).first()[["shop_id","weekday","sales_per_visitor","conversion_rate"]])
st.markdown("#### Zwakste dag per winkel (laagste SPV)")
st.dataframe(low.set_index("shop_id"))

piv = roll.pivot_table(index="weekday", values=["count_in","turnover","conversion_rate","sales_per_visitor"],
                       aggfunc={"count_in":"sum","turnover":"sum","conversion_rate":"mean","sales_per_visitor":"mean"})
st.markdown("#### Overzicht per weekdag (alle winkels)")
st.dataframe(piv)
