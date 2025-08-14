# utils_pfmx.py — live candidates improved, reports use [] keys
import streamlit as st
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlsplit
from typing import Optional, List, Tuple

PFM_PURPLE = "#762181"
PFM_RED = "#F04438"

# ---------- UI ----------
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

# ---------- Secrets & endpoints ----------
def _safe_get_secret(name: str) -> Optional[str]:
    try:
        val = st.secrets.get(name)
    except Exception:
        return None
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None

def _host_root_from_api_url(api_url: str) -> str:
    parts = urlsplit(api_url)
    if not parts.scheme or not parts.netloc:
        raise ValueError(f"API_URL is geen geldige URL: {api_url!r}")
    return f"{parts.scheme}://{parts.netloc}"

def _derive_report_url(api_url_secret: str) -> str:
    """Exact /get-report indien zo opgegeven; anders <host>/get-report."""
    api_url = api_url_secret.strip()
    if api_url.rstrip("/").endswith("/get-report"):
        return api_url.rstrip("/")
    return f"{_host_root_from_api_url(api_url)}/get-report"

def _derive_live_candidates(api_url_secret: str, live_override: Optional[str]) -> List[str]:
    """
    Voorkeursvolgorde voor live-inside:
      1) LIVE_URL override (abs/rel tov host)
      2) <API_URL>/live-inside            ← zelfde base-pad als /get-report
      3) <host>/live-inside
      4) <host>/report/live-inside        ← fallback (oude verwachting)
      5) <API_URL>/report/live-inside     ← extra fallback
    """
    api_url = api_url_secret.strip()
    root = _host_root_from_api_url(api_url)
    cands: List[str] = []

    if live_override:
        lo = live_override.strip()
        if lo.startswith(("http://", "https://")):
            cands.append(lo.rstrip("/"))
        else:
            cands.append(f"{root}/{lo.lstrip('/').rstrip('/')}")

    cands.append(f"{api_url.rstrip('/')}/live-inside")
    cands.append(f"{root}/live-inside")
    cands.append(f"{root}/report/live-inside")
    cands.append(f"{api_url.rstrip('/')}/report/live-inside")

    seen = set(); uniq = []
    for u in cands:
        if u not in seen:
            uniq.append(u); seen.add(u)
    return uniq

# ---------- Formatting ----------
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
    out: List[Tuple[str, str]] = []
    for k, v in params:
        if v is None:
            continue
        out.append((str(k), str(v)))
    return out

# --- bracket/plain builders voor REPORTS ---
def build_params_reports_brackets(source: str, period: Optional[str], data_ids: List[int], outputs: List[str]) -> List[Tuple[str,str]]:
    """data[]=..., data_output[]=... (zoals jij aangeeft dat nodig is)"""
    p: List[Tuple[str,str]] = [("source", source)]
    if period:
        p.append(("period", period))
    for d in data_ids:
        p.append(("data[]", str(int(d))))
    for o in outputs:
        p.append(("data_output[]", str(o)))
    return p

def build_params_reports_plain(source: str, period: Optional[str], data_ids: List[int], outputs: List[str]) -> List[Tuple[str,str]]:
    """data=..., data_output=... (fallback indien nodig)"""
    p: List[Tuple[str,str]] = [("source", source)]
    if period:
        p.append(("period", period))
    for d in data_ids:
        p.append(("data", str(int(d))))
    for o in outputs:
        p.append(("data_output", str(o)))
    return p

# ---------- HTTP ----------
def api_get_report(params: List[Tuple[str, str]], timeout: int = 40):
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}
    try:
        report_url = _derive_report_url(api_url_secret)
        resp = requests.post(report_url, params=params, timeout=timeout)
    except Exception as e:
        return {"_error": True, "status": 0, "text": f"{type(e).__name__}: {e}", "_url": api_url_secret or "<missing:API_URL>", "_method": "POST"}

    if resp.status_code >= 400:
        return {"_error": True, "status": resp.status_code, "text": resp.text, "_url": resp.url, "_method": "POST"}
    try:
        return resp.json()
    except Exception as e:
        return {"_error": True, "status": resp.status_code, "text": f"JSON decode error: {e}", "_url": resp.url, "_method": "POST"}

def api_get_live_inside(shop_ids: List[int], source: str = "locations", timeout: int = 15):
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}
    live_override = _safe_get_secret("LIVE_URL")

    params = [("source", source)]
    for sid in shop_ids:
        params.append(("data", str(int(sid))))

    tried = []
    for url in _derive_live_candidates(api_url_secret, live_override):
        try:
            r = requests.post(url, params=params, timeout=timeout)
            tried.append(f"POST {url} -> {r.status_code}")
            if 200 <= r.status_code < 300:
                return r.json()
        except Exception as e:
            tried.append(f"POST {url} -> EXC {type(e).__name__}: {e}")
        try:
            r = requests.get(url, params=params, timeout=timeout)
            tried.append(f"GET  {url} -> {r.status_code}")
            if 200 <= r.status_code < 300:
                return r.json()
        except Exception as e:
            tried.append(f"GET  {url} -> EXC {type(e).__name__}: {e}")

    return {
        "_error": True,
        "status": 404,
        "text": "Geen geldig live-endpoint gevonden.",
        "_url": " | ".join(tried),
        "_method": "POST→GET"
    }

# ---------- Normalizers & error UI ----------
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
