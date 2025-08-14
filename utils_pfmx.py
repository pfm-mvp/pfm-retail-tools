import streamlit as st
import requests
import pandas as pd
import numpy as np

PFM_PURPLE = "#762181"
PFM_RED = "#F04438"

def get_brand_colors():
    succ = st.secrets.get("SUCCESS_COLOR", "#00A650")
    dang = st.secrets.get("DANGER_COLOR", "#D7263D")
    return succ, dang

def inject_css():
    succ, dang = get_brand_colors()
    st.markdown(f"""
    <style>
    [data-testid="stSidebar"] {{
        background-color: {PFM_RED};
    }}
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] a {{
        color: #FFFFFF !important;
    }}
    .stButton button, .stDownloadButton button {{
        background-color: {PFM_PURPLE} !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
    }}
    .pfm-card {{
        border:1px solid #e6e6e6;border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05);
        background:#FFFFFF;
    }}
    .kpi-good {{ color: {succ}; font-weight:700; }}
    .kpi-bad  {{ color: {dang}; font-weight:700; }}
    </style>
    """, unsafe_allow_html=True)

def fmt_eur(x):
    try:
        return f"€{x:,.0f}".replace(",", ".")
    except Exception:
        return "€0"

def fmt_pct(x, digits=1):
    try:
        return f"{x*100:.{digits}f}%".replace(".", ",")
    except Exception:
        return "0%"

def api_get_report(params, base_url):
    url = f"{base_url.rstrip('/')}/get-report"
    resp = requests.get(url, params=params, timeout=40)
    if resp.status_code >= 400:
        return {"_error": True, "status": resp.status_code, "text": resp.text}
    return resp.json()

def api_get_live_inside(shop_ids, base_url, live_url=None):
    if live_url is None:
        live_url = f"{base_url.rstrip('/')}/report/live-inside"
    param_list = [("source", "locations")]
    for sid in shop_ids:
        param_list.append(("data", int(sid)))
    resp = requests.get(live_url, params=param_list, timeout=15)
    if resp.status_code >= 400:
        return {"_error": True, "status": resp.status_code, "text": resp.text}
    return resp.json()

def normalize_vemcount_daylevel(resp_json, kpis=("count_in","conversion_rate","turnover","sales_per_visitor")):
    if not isinstance(resp_json, dict) or "_error" in resp_json:
        return pd.DataFrame()
    rows = []
    data = resp_json.get("data", {})
    for day_key, day_blob in (data.items() if isinstance(data, dict) else []):
        day = pd.to_datetime(day_key.replace("date_",""), errors="coerce")
        if day is pd.NaT:
            continue
        for loc_id, loc_blob in (day_blob.items() if isinstance(day_blob, dict) else []):
            if not isinstance(loc_blob, dict):
                continue
            if "data" in loc_blob:
                d = loc_blob["data"]
                row = {"date": day, "shop_id": int(loc_id)}
                for k in kpis:
                    row[k] = d.get(k)
                rows.append(row)
            elif "dates" in loc_blob:
                vals = [v.get("data", {}) for v in loc_blob["dates"].values()]
                if not vals: 
                    continue
                agg = {"date": day, "shop_id": int(loc_id)}
                for k in kpis:
                    series = [x.get(k) for x in vals if x and x.get(k) is not None]
                    if not series:
                        agg[k] = None
                    elif k in {"count_in","turnover"}:
                        agg[k] = float(np.nansum(series))
                    else:
                        agg[k] = float(np.nanmean(series))
                rows.append(agg)
    if not rows:
        return pd.DataFrame(columns=["date","shop_id",*kpis])
    df = pd.DataFrame(rows).sort_values(["shop_id","date"]).reset_index(drop=True)
    if "sales_per_visitor" in df.columns:
        mask = df["sales_per_visitor"].isna()
        if "turnover" in df.columns and "count_in" in df.columns:
            df.loc[mask, "sales_per_visitor"] = (df.loc[mask, "turnover"] / df.loc[mask, "count_in"].replace(0, np.nan))
    return df

def friendly_error(js, context=""):
    if isinstance(js, dict) and js.get("_error"):
        st.error(f"Geen data ontvangen ({context}). Controleer periode, store IDs of API_URL. [status={js.get('status')}]")
        return True
    return False