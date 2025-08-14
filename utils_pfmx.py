import streamlit as st
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlsplit

PFM_PURPLE = "#762181"
PFM_RED = "#F04438"

def get_brand_colors():
    succ = st.secrets.get("SUCCESS_COLOR", "#00A650")
    dang = st.secrets.get("DANGER_COLOR", "#D7263D")
    return succ, dang

def inject_css():
    succ, dang = get_brand_colors()
    css = "<style>\n"
    css += '[data-testid="stSidebar"] ' + "{\n" + f"  background-color: {PFM_RED};\n" + "}\n"
    css += '[data-testid="stSidebar"] *, [data-testid="stSidebar"] a ' + "{\n" + "  color: #FFFFFF !important;\n" + "}\n"
    css += ".stButton button, .stDownloadButton button " + "{\n" + f"  background-color: {PFM_PURPLE} !important;\n  color: #FFFFFF !important;\n  border-radius: 12px !important;\n  border: none !important;\n" + "}\n"
    css += ".pfm-card " + "{\n" + "  border:1px solid #e6e6e6;border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05);\n  background:#FFFFFF;\n" + "}\n"
    css += ".kpi-good " + "{\n" + f"  color: {succ}; font-weight:700;\n" + "}\n"
    css += ".kpi-bad " + "{\n" + f"  color: {dang}; font-weight:700;\n" + "}\n"
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

def _resolve_urls(api_url: str, live_url: str|None):
    api_url = (api_url or "").rstrip("/")
    # get-report endpoint (avoid double /get-report)
    if api_url.endswith("/get-report"):
        get_report_url = api_url
    else:
        get_report_url = api_url + "/get-report"
    # live-side from root unless LIVE_URL supplied
    if live_url:
        live_inside_url = live_url.rstrip("/")
    else:
        parts = urlsplit(api_url)
        root = f"{parts.scheme}://{parts.netloc}"
        live_inside_url = root + "/live-side"
    return get_report_url, live_inside_url

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

def _bracketize_params(params):
    """Ensure data and data_output keys are encoded as data[] and data_output[] for /get-report."""
    fixed = []
    for k, v in params:
        if k == "data":
            fixed.append(("data[]", v))
        elif k == "data_output":
            fixed.append(("data_output[]", v))
        else:
            fixed.append((k, v))
    return fixed

def api_get_report(params, base_url):
    """Call FastAPI /get-report with source=shops and bracketed arrays for data[] and data_output[]."""
    get_url, _ = _resolve_urls(st.secrets["API_URL"], st.secrets.get("LIVE_URL"))
    safe_params = _bracketize_params(params)
    resp = requests.get(get_url, params=safe_params, timeout=40)
    if resp.status_code >= 400:
        return {"_error": True, "status": resp.status_code, "text": resp.text, "_url": resp.url}
    return resp.json()

def api_get_live_inside(shop_ids, base_url, live_url=None):
    """Live counter at /live-side with source=locations and data=shop_id (no brackets)."""
    _, live_inside_url = _resolve_urls(st.secrets["API_URL"], st.secrets.get("LIVE_URL"))
    param_list = [("source", "locations")]
    for sid in shop_ids:
        param_list.append(("data", int(sid)))
    resp = requests.get(live_inside_url, params=param_list, timeout=15)
    if resp.status_code >= 400:
        return {"_error": True, "status": resp.status_code, "text": resp.text, "_url": resp.url}
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
        st.error(f"Geen data ontvangen ({context}). Controleer API_URL/LIVE_URL of periode/IDs. [status={js.get('status')}]")
        st.caption(f"↪ endpoint: {js.get('_url','')}")
        return True
    return False