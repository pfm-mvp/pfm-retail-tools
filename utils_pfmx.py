from urllib.parse import urlsplit
from typing import Optional, List, Tuple

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
      1) {API_URL}/live-inside           ← zelfde base als get-report
      2) {HOST}/live-inside
      3) {HOST}/report/live-inside
      4) {API_URL}/report/live-inside
    Eventuele LIVE_URL override (abs/rel) gaat VOOR alle kandidaten.
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

def api_get_report(params: List[Tuple[str, str]], timeout: int = 40):
    """
    Eerst POST met brackets (zoals je aangeeft dat nodig is).
    Als server dat afwijst (>=400), fallback naar POST zonder brackets.
    """
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}

    report_url = _derive_report_url(api_url_secret)

    # 1) Brackets
    try:
        r1 = requests.post(report_url, params=params, timeout=timeout)
        if 200 <= r1.status_code < 300:
            return r1.json()
        # Als het b.v. een 422/400 geeft, probeert fallback
        first_fail = f"{r1.status_code} @ {r1.url}"
    except Exception as e:
        first_fail = f"EXC {type(e).__name__}: {e}"

    # 2) Fallback: zonder brackets
    try:
        # transformeer params naar plain keys
        plain: List[Tuple[str,str]] = []
        for k, v in params:
            if k == "data[]":
                plain.append(("data", v))
            elif k == "data_output[]":
                plain.append(("data_output", v))
            else:
                plain.append((k, v))
        r2 = requests.post(report_url, params=plain, timeout=timeout)
        if 200 <= r2.status_code < 300:
            return r2.json()
        return {"_error": True, "status": r2.status_code, "text": r2.text, "_url": f"brackets→{first_fail} | plain→{r2.url}", "_method": "POST"}
    except Exception as e:
        return {"_error": True, "status": 0, "text": f"brackets→{first_fail} | plain→EXC {type(e).__name__}: {e}", "_url": report_url, "_method": "POST"}

def api_get_live_inside(shop_ids: List[int], source: str = "locations", timeout: int = 15):
    """
    Live inside met expliciete query: ?source=locations&data=<id>
    Probeert POST, dan GET, over meerdere URL-kandidaten.
    Logt de **volledige r.url** zodat je altijd ziet dat de querystring aanwezig is.
    """
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}
    live_override = _safe_get_secret("LIVE_URL")

    params = [("source", source)]
    for sid in shop_ids:
        params.append(("data", str(int(sid))))

    tried = []
    for url in _derive_live_candidates(api_url_secret, live_override):
        # POST
        try:
            r = requests.post(url, params=params, timeout=timeout)
            tried.append(f"POST {r.url} -> {r.status_code}")
            if 200 <= r.status_code < 300:
                return r.json()
        except Exception as e:
            tried.append(f"POST {url} -> EXC {type(e).__name__}: {e}")
        # GET
        try:
            r = requests.get(url, params=params, timeout=timeout)
            tried.append(f"GET  {r.url} -> {r.status_code}")
            if 200 <= r.status_code < 300:
                return r.json()
        except Exception as e:
            tried.append(f"GET  {url} -> EXC {type(e).__name__}: {e}")

    return {"_error": True, "status": 404, "text": "Geen geldig live-endpoint gevonden.", "_url": " | ".join(tried), "_method": "POST→GET"}
