# utils_pfmx.py — clean & robust
import streamlit as st
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlsplit
from typing import Optional, List, Tuple

PFM_PURPLE = "#762181"
PFM_RED = "#F04438"

# ---------------------------
# UI helpers
# ---------------------------
def get_brand_colors():
    succ = st.secrets.get("SUCCESS_COLOR", "#00A650")
    dang = st.secrets.get("DANGER_COLOR", "#D7263D")
    return succ, dang

def inject_css():
    succ, dang = get_brand_colors()
    css = "<style>\n"
    css += '[data-testid="stSidebar"] { background-color: %s; }\n' % PFM_RED
    css += '[data-testid="stSidebar"] *, [data-testid="stSidebar"] a { color: #FFFFFF !important; }\n'
    css += '.stButton button, .stDownloadButton button { background:#762181 !important; color:#fff !important; border-radius:12px !important; border:none !important; }\n'
    css += '.pfm-card { border:1px solid #e6e6e6; box-shadow:0 1px 3px rgba(0,0,0,.05); background:#fff; padding:16px; border-radius:16px; }\n'
    css += '.kpi-good { color:%s; font-weight:700; }\n' % succ
    css += '.kpi-bad { color:%s; font-weight:700; }\n' % dang
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

# ---------------------------
# Secrets & endpoint resolution
# ---------------------------
def _safe_get_secret(name: str) -> Optional[str]:
    """Safe read of Streamlit secret; returns None when missing/empty."""
    try:
        val = st.secrets.get(name)
    except Exception:
        return None
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None

def _derive_endpoints_from_base(api_url: Optional[str], live_override: Optional[str] = None) -> Tuple[str, str]:
    """
    Expectation:
      secrets["API_URL"] may equal 'https://vemcount-agent.onrender.com/get-report'
    We return:
      report_url = exactly what you provided if it ends with /get-report, else <host>/get-report
      live_url   = <host>/report/live-inside, unless LIVE_URL override is set (absolute or relative)
    """
    if not isinstance(api_url, str) or not api_url.strip():
        raise ValueError("API_URL secret ontbreekt of is leeg")

    api_url = api_url.strip()
    parts = urlsplit(api_url)
    if not parts.scheme or not parts.netloc:
        raise ValueError(f"API_URL is geen geldige URL: {api_url!r}")

    root = f"{parts.scheme}://{parts.netloc}"

    if api_url.rstrip("/").endswith("/get-report"):
        report_url = api_url.rstrip("/")
    else:
        report_url = f"{root}/get-report"

    if live_override:
        lo = live_override.strip()
        if lo.startswith(("http://", "https://")):
            live_url = lo.rstrip("/")
        else:
            live_url = f"{root}/{lo.lstrip('/').rstrip('/')}"
    else:
        live_url = f"{root}/report/live-inside"

    return report_url, live_url

# ---------------------------
# Formatting helpers
# ---------------------------
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

def _no_brackets(params: List[Tuple[str, object]]) -> List[Tuple[str, str]]:
    """Repeat keys without [] and cast values to str; drop None values."""
    out: List[Tuple[str, str]] = []
    for k, v in params:
        if v is None:
            continue
        out.append((str(k), str(v)))
    return out

# ---------------------------
# HTTP (POST, no brackets)
# ---------------------------
def api_get_report(params: List[Tuple[str, object]], timeout: int = 40):
    """
    POST to /get-report with querystring params (no [] in keys).
    Base comes from st.secrets["API_URL"] which may itself end with /get-report.
    """
    api_url_secret = _safe_get_secret("API_URL")
    live_override = _safe_get_secret("LIVE_URL")
    try:
        report_url, _ = _derive_endpoints_from_base(api_url_secret, live_override)
        resp = requests.post(report_url, params=_no_brackets(params), timeout=timeout)
    except ValueError as e:
        return {"_error": True, "status": 0, "text": str(e), "_url": api_url_secret or "<missing:API_URL>", "_method": "POST"}
    except Exception as e:
        return {"_error": True, "status": 0, "text": f"{type(e).__name__}: {e}", "_url": api_url_secret or "<missing:API_URL>", "_method": "POST"}

    if resp.status_code >= 400:
        return {"_error": True, "status": resp.status_code, "text": resp.text, "_url": resp.url, "_method": "POST"}
    try:
        return resp.json()
    except Exception as e:
        return {"_error": True, "status": resp.status_code, "text": f"JSON decode error: {e}", "_url": resp.url, "_method": "POST"}

def api_get_live_inside(shop_ids: List[int], source: str = "locations", timeout: int = 20):
    """
    POST to /report/live-inside with source=<default: locations> and repeated data=<id>.
    Base host is derived from API_URL so we never end up with /get-report/get-report.
    """
    api_url_secret = _safe_get_secret("API_URL")
    live_override = _safe_get_secret("LIVE_URL")
    try:
        _, live_url = _derive_endpoints_from_base(api_url_secret, live_override)
        param_list: List[Tuple[str, object]] = [("source", source)]
        for sid in shop_ids:
            param_list.append(("data", int(sid)))  # force np.int64 → int
        resp = requests.post(live_url, params=_no_brackets(param_list), timeout=timeout)
    except ValueError as e:
        return {"_error": True, "status": 0, "text": str(e), "_url": live_override or "<auto>/report/live-inside", "_method": "POST"}
    except Exception as e:
        return {"_error": True, "status": 0, "text": f"{type(e).__name__}: {e}", "_url": live_override or "<auto>/report/live-inside", "_method": "POST"}

    if resp.status_code >= 400:
        return {"_error": True, "status": resp.status_code, "text": resp.text, "_url": resp.url, "_method": "POST"}
    try:
        return resp.json()
    except Exception as e:
        return {"_error": True, "status": resp.status_code, "text": f"JSON decode error: {e}", "_url": resp.url, "_method": "POST"}

# ---------------------------
# Normalizers & error UI
# ---------------------------
def normalize_vemcount_daylevel(resp_json, kpis=("count_in", "conversion_rate", "turnover", "sales_per_visitor")):
    if not isinstance(resp_json, dict) or resp_json.get("_error"):
        return pd.DataFrame()
    rows = []
    data = resp_json.get("data", {})
    for day_key, day_blob in (data.items() if isinstance(data, dict) else []):
        day = pd.to_datetime(day_key.replace("date_", ""), errors="coerce")
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
                    elif k in {"count_in", "turnover"}:
                        agg[k] = float(np.nansum(series))
                    else:
                        agg[k] = float(np.nanmean(series))
                rows.append(agg)
    if not rows:
        return pd.DataFrame(columns=["date", "shop_id", *kpis])
    df = pd.DataFrame(rows).sort_values(["shop_id", "date"]).reset_index(drop=True)
    if "sales_per_visitor" in df.columns:
        mask = df["sales_per_visitor"].isna()
        if "turnover" in df.columns and "count_in" in df.columns:
            df.loc[mask, "sales_per_visitor"] = (
                df.loc[mask, "turnover"] / df.loc[mask, "count_in"].replace(0, np.nan)
            )
    return df

def friendly_error(js, context: str = ""):
    if isinstance(js, dict) and js.get("_error"):
        st.error(f"Geen data ontvangen ({context}). Controleer API_URL/LIVE_URL of periode/IDs. [status={js.get('status')}]")
        extra = f"{js.get('_method','')} {js.get('_url','')}"
        st.caption(f"↪ {extra}")
        return True
    return False
