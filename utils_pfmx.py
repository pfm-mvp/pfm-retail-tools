# ... imports en CSS helpers blijven gelijk ...

# ---------------------------
# Endpoint helpers
# ---------------------------
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

def _derive_report_and_live_candidates(api_url_secret: str, live_override: Optional[str] = None) -> List[str]:
    """
    Retourneert mogelijke live-inside endpoints in volgorde van voorkeur.
    1) <host>/report/live-inside
    2) <API_URL>/report/live-inside   (dus inclusief eventuele '/get-report' in de base)
    3) LIVE_URL override (indien absoluut), anders <host>/<LIVE_URL>
    """
    api_url = api_url_secret.strip()
    root = _host_root_from_api_url(api_url)

    cands = [f"{root}/report/live-inside", f"{api_url.rstrip('/')}/report/live-inside"]

    if live_override:
        lo = live_override.strip()
        if lo.startswith(("http://","https://")):
            cands.insert(0, lo.rstrip("/"))  # override absolute krijgt hoogste prioriteit
        else:
            cands.insert(0, f"{root}/{lo.lstrip('/').rstrip('/')}")  # override relatief

    # dedup (preserve order)
    seen = set(); uniq = []
    for u in cands:
        if u not in seen:
            uniq.append(u); seen.add(u)
    return uniq

# ---------------------------
# Param builders
# ---------------------------
def build_params_reports_brackets(source: str, period: Optional[str], data_ids: List[int], outputs: List[str]) -> List[Tuple[str,str]]:
    """
    Bouwt params met brackets: data[]=..., data_output[]=...
    """
    p: List[Tuple[str,str]] = [("source", source)]
    if period:
        p.append(("period", period))
    for d in data_ids:
        p.append(("data[]", str(int(d))))
    for o in outputs:
        p.append(("data_output[]", str(o)))
    return p

def build_params_reports_plain(source: str, period: Optional[str], data_ids: List[int], outputs: List[str]) -> List[Tuple[str,str]]:
    """
    Bouwt params zonder brackets: data=..., data_output=...
    (Handig als backend dat verwacht.)
    """
    p: List[Tuple[str,str]] = [("source", source)]
    if period:
        p.append(("period", period))
    for d in data_ids:
        p.append(("data", str(int(d))))
    for o in outputs:
        p.append(("data_output", str(o)))
    return p

# ---------------------------
# HTTP (POST/GET, robust)
# ---------------------------
def api_get_report(params: List[Tuple[str,str]], timeout: int = 40):
    """
    POST naar /get-report (precies zoals in secrets gezet of <host>/get-report).
    """
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}
    try:
        # report endpoint: ofwel exact wat jij gaf (als eindigt op /get-report), anders <host>/get-report
        api_url = api_url_secret.strip()
        if api_url.rstrip("/").endswith("/get-report"):
            report_url = api_url.rstrip("/")
        else:
            report_url = f"{_host_root_from_api_url(api_url)}/get-report"
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
    """
    Probeert POST en daarna GET op meerdere live-inside URL kandidaten.
    Stuurt herhaald 'data=' (zonder brackets) — conform jouw voorbeeld voor live.
    """
    api_url_secret = _safe_get_secret("API_URL")
    if not api_url_secret:
        return {"_error": True, "status": 0, "text": "API_URL secret ontbreekt of is leeg", "_url": "<missing:API_URL>", "_method": "POST"}
    live_override = _safe_get_secret("LIVE_URL")

    params = [("source", source)]
    for sid in shop_ids:
        params.append(("data", str(int(sid))))

    tried = []
    for url in _derive_report_and_live_candidates(api_url_secret, live_override):
        # 1) POST
        try:
            r = requests.post(url, params=params, timeout=timeout)
            tried.append(f"POST {url} -> {r.status_code}")
            if 200 <= r.status_code < 300:
                return r.json()
        except Exception as e:
            tried.append(f"POST {url} -> EXC {type(e).__name__}: {e}")

        # 2) fallback: GET
        try:
            r = requests.get(url, params=params, timeout=timeout)
            tried.append(f"GET  {url} -> {r.status_code}")
            if 200 <= r.status_code < 300:
                return r.json()
        except Exception as e:
            tried.append(f"GET  {url} -> EXC {type(e).__name__}: {e}")

    # nothing worked
    return {
        "_error": True,
        "status": 404,
        "text": "Geen geldig live-endpoint gevonden.",
        "_url": " | ".join(tried),
        "_method": "POST→GET"
    }

# ---------------------------
# Normalizers & error UI (ongewijzigd)
# ---------------------------
# ... keep normalize_vemcount_daylevel(...) & friendly_error(...) zoals eerder ...
