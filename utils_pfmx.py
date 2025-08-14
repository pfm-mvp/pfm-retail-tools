# utils_pfmx.py — clean import; no side-effects
import streamlit as st
import requests
import pandas as pd
import numpy as np
import http.client
import json
from urllib.parse import urlsplit, urlencode, quote
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

def _qs_preserve_brackets(pairs: list[tuple[str, object]]) -> str:
    """
    Bouwt een querystring waarbij [] in de KEY behouden blijven.
    We encoden alleen de VALUE (':' laten we toe voor tijden zoals 09:00).
    Voorbeeld: [("data[]", 32224), ("data_output[]", "turnover")]
    -> "data[]=32224&data_output[]=turnover"
    """
    parts = []
    for k, v in pairs:
        if v is None:
            continue
        parts.append(f"{k}={quote(str(v), safe=':')}")
    return "&".join(parts)

# ---------------------------
# Secrets & endpoints
# ---------------------------
def _qs_preserve_brackets(pairs: list[tuple[str, object]]) -> str:
    """
    Maakt een querystring waarbij we de KEY ongewijzigd laten (dus 'data[]')
    en alleen de VALUE URL-encoden. Daardoor blijven [] zichtbaar i.p.v. %5B%5D.
    """
    parts = []
    for k, v in pairs:
        if v is None:
            continue
        # laat brackets in KEY staan; encode alleen VALUE (':' laten we toe voor tijden)
        parts.append(f"{k}={quote(str(v), safe=':')}")
    return "&".join(parts)

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
    api_url = api_url_secret.strip()
    if api_url.rstrip("/").endswith("/get-report"):
        return api_url.rstrip("/")
    return f"{_host_root_from_api_url(api_url)}/get-report"

def _derive_live_candidates(api_url_secret: str, live_override: Optional[str]) -> List[str]:
    """
    Live-inside endpoint-kandidaten (in volgorde):
      1) {API_URL}/live-inside            ← zelfde base als get-report
      2) {HOST}/live-inside
      3) {HOST}/report/live-inside
      4) {API_URL}/report/live-inside
    LIVE_URL override (abs/rel) gaat vóór deze kandidaten.
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

    cands.extend([
        f"{api_url.rstrip('/')}/live-inside",
        f"{root}/live-inside",
        f"{root}/report/live-inside",
        f"{api_url.rstrip('/')}/report/live-inside",
    ])

    seen = set(); uniq = []
    for u in cands:
        if u not in seen:
            uniq.append(u); seen.add(u)
    return uniq

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

# --- params builders (reports) ---
def build_params_reports_brackets(source: str, period: Optional[str], data_ids: List[int], outputs: List[str]) -> List[Tuple[str,str]]:
    """data[]=..., data_output[]=..."""
    p: List[Tuple[str,str]] = [("source", source)]
    if period:
        p.append(("period", period))
    for d in data_ids:
        p.append(("data[]", str(int(d))))
    for o in outputs:
        p.append(("data_output[]", str(o)))
    return p

def build_params_reports_plain(source: str, period: Optional[str], data_ids: List[int], outputs: List[str]) -> List[Tuple[str,str]]:
    """data=..., data_output=..."""
    p: List[Tuple[str,str]] = [("source", source)]
    if period:
        p.append(("period", period))
    for d in data_ids:
        p.append(("data", str(int(d))))
    for o in outputs:
        p.append(("data_output", str(o)))
    return p

# ---------------------------
# HTTP (POST; live logt volledige r.url)
# ---------------------------
def api_get_report(params: list[tuple[str, object]], timeout: int = 40):
    """
    POST naar exact de base uit secrets (die bij jou al /get-report is),
    met herhaalde keys ZONDER brackets: data=... & data_output=...
    """
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}

    base = api_url_secret.rstrip("/")   # verwacht: https://vemcount-agent.onrender.com/get-report
    # herhaalde keys korrekt maken
    qs   = urlencode(params, doseq=True).replace("%3A", ":")
    url  = f"{base}?{qs}"

    try:
        resp = requests.post(url, timeout=timeout)  # LET OP: géén params= gebruiken
        if resp.status_code >= 400:
            return {"_error": True, "status": resp.status_code, "text": resp.text, "_url": resp.url, "_method": "POST"}
        return resp.json()
    except Exception as e:
        return {"_error": True, "status": 0, "text": f"{type(e).__name__}: {e}", "_url": url, "_method": "POST"}


def api_get_live_inside(shop_ids: list[int], source: str = "locations", timeout: int = 15):
    """
    POST naar <HOST>/report/live-inside met ?source=locations&data=<id>
    (dus géén brackets).
    """
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}

    parts = urlsplit(api_url_secret.rstrip("/"))
    root  = f"{parts.scheme}://{parts.netloc}"
    live_url = f"{root}/report/live-inside"

    params = [("source", source)]
    for sid in shop_ids:
        params.append(("data", int(sid)))     # zonder []

    qs  = urlencode(params, doseq=True)
    url = f"{live_url}?{qs}"

    try:
        resp = requests.post(url, timeout=timeout)  # géén params=
        if resp.status_code >= 400:
            return {"_error": True, "status": resp.status_code, "text": resp.text, "_url": resp.url, "_method": "POST"}
        return resp.json()
    except Exception as e:
        return {"_error": True, "status": 0, "text": f"{type(e).__name__}: {e}", "_url":
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
