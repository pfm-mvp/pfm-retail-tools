
import streamlit as st
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlencode
from typing import Optional, List, Tuple, Dict, Any

def inject_css():
    st.markdown('<style>.kpi{padding:12px 14px;border:1px solid #EEE;border-radius:16px;}</style>', unsafe_allow_html=True)

def fmt_eur(x):
    try: return '€ {:,.0f}'.format(float(x)).replace(',', '.')
    except: return '€ 0'

def fmt_pct(x):
    try: return '{:.1f}%'.format(float(x)*100.0)
    except: return '0.0%'

def _normalize_base(url: str) -> str:
    if not url: return ''
    if '://' not in url: url = 'https://' + url
    return url.rstrip('/')

def _api_base() -> str:
    return _normalize_base(st.secrets.get('API_URL','').strip())

def build_params_reports_plain(source: str, period: str, data_ids: List[int], outputs: List[str],
                               date_from: Optional[str]=None, date_to: Optional[str]=None,
                               period_step: Optional[str]=None, extra: Optional[List[Tuple[str,str]]]=None):
    params = [('source', source), ('period', period)]
    if date_from: params.append(('date_from', date_from))
    if date_to: params.append(('date_to', date_to))
    if period_step: params.append(('period_step', period_step))
    params += [('data', int(i)) for i in data_ids]
    params += [('data_output', o) for o in outputs]
    if extra: params += list(extra)
    return params

def _post_json(full_url: str, timeout: int=90) -> Dict[str, Any]:
    try:
        r = requests.post(full_url, timeout=timeout); r.raise_for_status(); return r.json()
    except Exception as e:
        return {'_error': True, 'status': getattr(e,'response',None).status_code if hasattr(e,'response') and e.response is not None else None, '_url': full_url, '_method': 'POST', 'exception': str(e)}

def api_get_report(params, timeout: int=90):
    base = _api_base()
    if not base: return {'_error': True, 'status': None, '_url': '', '_method': 'POST', 'exception': 'Missing API_URL secret'}
    path = '/get-report'
    full = (base if base.endswith(path) else base+path) + '?' + urlencode(params, doseq=True)
    return _post_json(full, timeout=timeout)

def api_get_live_inside(shop_ids: List[int], source: str='locations', timeout: int=45):
    base = _api_base()
    if not base: return {'_error': True, 'status': None, '_url': '', '_method': 'POST', 'exception': 'Missing API_URL secret'}
    p = [('source', source)] + [('data', int(i)) for i in shop_ids]
    path = '/report/live-inside'
    full = (base if base.endswith(path) else base+path) + '?' + urlencode(p, doseq=True)
    return _post_json(full, timeout=timeout)

def _as_float(x):
    try: return float(x)
    except: return 0.0

def normalize_vemcount_daylevel(js: Dict[str, Any]) -> pd.DataFrame:
    if not isinstance(js, dict) or 'data' not in js: return pd.DataFrame()
    rows = []
    for date_key, by_shop in (js.get('data') or {}).items():
        try: date = pd.to_datetime(date_key.replace('date_',''), errors='coerce').date()
        except: date = None
        if not isinstance(by_shop, dict): continue
        for sid, payload in by_shop.items():
            try: shop_id = int(sid)
            except:
                try: shop_id = int(payload.get('shop_id'))
                except: continue
            if not isinstance(payload, dict): continue
            if 'data' in payload and isinstance(payload['data'], dict):
                kpis = payload['data']
                rows.append({'date': date, 'shop_id': shop_id,
                             'count_in': _as_float(kpis.get('count_in')),
                             'conversion_rate': _as_float(kpis.get('conversion_rate')),
                             'turnover': _as_float(kpis.get('turnover')),
                             'sales_per_visitor': _as_float(kpis.get('sales_per_visitor') or 0)})
            elif 'dates' in payload and isinstance(payload['dates'], dict):
                cin=tov=conv_num=conv_den=spv_num=spv_cnt=0.0
                for ts, slot in payload['dates'].items():
                    if not isinstance(slot, dict): continue
                    k = slot.get('data', {})
                    cin += _as_float(k.get('count_in')); tov += _as_float(k.get('turnover'))
                    cr=k.get('conversion_rate'); spv=k.get('sales_per_visitor')
                    if cr is not None:
                        try: conv_num += float(cr); conv_den += 1
                        except: pass
                    if spv is not None:
                        try: spv_num += float(spv); spv_cnt += 1
                        except: pass
                rows.append({'date': date, 'shop_id': shop_id, 'count_in': cin, 'turnover': tov,
                             'conversion_rate': (conv_num/conv_den) if conv_den>0 else 0.0,
                             'sales_per_visitor': (spv_num/spv_cnt) if spv_cnt>0 else 0.0})
    df = pd.DataFrame(rows)
    if df.empty: return df
    if 'sales_per_visitor' in df.columns:
        mask = df['sales_per_visitor'].isna()
        if 'turnover' in df.columns and 'count_in' in df.columns:
            df.loc[mask, 'sales_per_visitor'] = df.loc[mask, 'turnover'] / df.loc[mask, 'count_in'].replace(0, np.nan)
    return df

def friendly_error(js, context: str=''):
    if isinstance(js, dict) and js.get('_error'):
        st.error(f'Geen data ontvangen ({context}). Controleer API_URL of periode/IDs. [status={js.get("status")}]')
        st.caption(f"↪ {js.get('_method','')} {js.get('_url','')}")
        return True
    return False
