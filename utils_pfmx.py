
import requests
import pandas as pd
import numpy as np

PFM_PURPLE = "#762181"
PFM_RED = "#F04438"
PFM_ORANGE = "#F59E0B"

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

# GET /get-report via FastAPI proxy. Pass params as list of tuples (no [] keys).
def api_get_report(params, base_url):
    url = f"{base_url.rstrip('/')}/get-report"
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# GET /report/live-inside (proxied or direct). source: 'locations' or 'zones'. ids: list[int]
def api_get_live_inside(source, ids, base_url, live_url=None):
    if live_url is None:
        live_url = f"{base_url.rstrip('/')}/report/live-inside"
    param_list = [("source", source)]
    for _id in ids:
        param_list.append(("data", int(_id)))
    r = requests.get(live_url, params=param_list, timeout=15)
    r.raise_for_status()
    return r.json()

# Normalize typical Vemcount day response
def normalize_vemcount_daylevel(resp_json, kpis=("count_in","conversion_rate","turnover","sales_per_visitor")):
    rows = []
    data = resp_json.get("data", {})
    for day_key, day_blob in data.items():
        date_str = day_key.replace("date_","")
        locations = day_blob if isinstance(day_blob, dict) else {}
        for loc_id, loc_blob in locations.items():
            if "data" in loc_blob:
                d = loc_blob["data"]
                row = {"date": pd.to_datetime(date_str), "shop_id": int(loc_id)}
                for k in kpis:
                    row[k] = d.get(k)
                rows.append(row)
            elif "dates" in loc_blob:
                ksum = {"count_in","turnover"}
                kmean = {"conversion_rate","sales_per_visitor"}
                agg = {"date": pd.to_datetime(date_str), "shop_id": int(loc_id)}
                vals = list(loc_blob["dates"].values())
                for k in kpis:
                    series = [v["data"].get(k) for v in vals if v.get("data")]
                    series = [x for x in series if x is not None]
                    if not series:
                        agg[k] = None
                    elif k in ksum:
                        agg[k] = float(np.nansum(series))
                    elif k in kmean:
                        agg[k] = float(np.nanmean(series))
                    else:
                        agg[k] = float(np.nansum(series))
                rows.append(agg)
    if not rows:
        return pd.DataFrame(columns=["date","shop_id",*kpis])
    df = pd.DataFrame(rows).sort_values(["shop_id","date"]).reset_index(drop=True)
    if "sales_per_visitor" in df.columns:
        mask = df["sales_per_visitor"].isna()
        if "turnover" in df.columns and "count_in" in df.columns:
            df.loc[mask, "sales_per_visitor"] = (df.loc[mask, "turnover"] / df.loc[mask, "count_in"].replace(0, np.nan))
    return df

def to_weekday_en(series):
    return pd.to_datetime(series).dt.day_name()
