import streamlit as st
import requests
from urllib.parse import urlencode
from typing import Optional, List, Tuple, Dict, Any

def _normalize_base(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    return url.rstrip("/")

def _api_base() -> str:
    return _normalize_base(st.secrets.get("API_URL", "").strip())

def _with_get_report_prefix(base: str) -> str:
    b = base.rstrip("/")
    return b if b.endswith("/get-report") else b + "/get-report"

def _post_json(url: str, timeout: int = 90) -> Dict[str, Any]:
    r = requests.post(url, timeout=timeout)
    r.raise_for_status()
    return r.json()

def api_get_report(
    source: str,
    period: str,
    data_ids: List[int],
    outputs: List[str],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    period_step: Optional[str] = None,
    extra: Optional[List[Tuple[str, str]]] = None,
    timeout: int = 90
) -> Dict[str, Any]:
    base = _with_get_report_prefix(_api_base())

    # Primary
    params = [("source", source), ("period", period)]
    if date_from:   params.append(("date_from", date_from))
    if date_to:     params.append(("date_to", date_to))
    if period_step: params.append(("period_step", period_step))
    params += [("data", int(i)) for i in data_ids]
    params += [("data_output", o) for o in outputs]
    if extra:
        params += list(extra)
    url = f"{base}?{urlencode(params, doseq=True)}"

    try:
        return {"_variant": "primary", "_url": url, "_data": _post_json(url, timeout=timeout)}
    except requests.HTTPError:
        # Fallback
        params_fb = [("source", source), ("period", period)]
        if date_from:   params_fb.append(("date_from", date_from))
        if date_to:     params_fb.append(("date_to", date_to))
        if period_step: params_fb.append(("period_step", period_step))
        params_fb += [("data[]", int(i)) for i in data_ids]
        params_fb += [("data_output[]", o) for o in outputs]
        if extra:
            params_fb += list(extra)
        url_fb = f"{base}?{urlencode(params_fb, doseq=True)}"
        return {"_variant": "fallback", "_url": url_fb, "_data": _post_json(url_fb, timeout=timeout)}

def api_get_live_inside(
    shop_ids: List[int],
    source: str = "locations",
    timeout: int = 45
) -> Dict[str, Any]:
    base = _with_get_report_prefix(_api_base())

    # Primary
    params = [("source", source)] + [("data", int(i)) for i in shop_ids]
    url = f"{base}/live-inside?{urlencode(params, doseq=True)}"
    try:
        return {"_variant": "primary", "_url": url, "_data": _post_json(url, timeout=timeout)}
    except requests.HTTPError:
        # Fallback
        params_fb = [("source", source)] + [("data[]", int(i)) for i in shop_ids]
        url_fb = f"{base}/live-inside?{urlencode(params_fb, doseq=True)}"
        return {"_variant": "fallback", "_url": url_fb, "_data": _post_json(url_fb, timeout=timeout)}