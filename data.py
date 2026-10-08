'''Live market data fetchers (CoinGecko, tgju.org, Yahoo Finance, alternative.me).'''
import asyncio
import re
import time
from urllib.parse import quote

import httpx

from core import CACHE, IDS, TTL

UA = {'User-Agent': 'alien-market-bot/2.0'}
YF = {'brent': 'BZ=F', 'wti': 'CL=F', 'plat': 'PL=F',
      'pall': 'PA=F', 'copper': 'HG=F', 'gas': 'NG=F'}


async def fetch_prices():
    now = time.time()
    if now - CACHE['t'] < TTL and CACHE['d']:
        return CACHE['d']
    ids = ','.join(sorted(set(IDS.values())))
    async with httpx.AsyncClient(timeout=15, headers=UA) as cl:
        for attempt in range(3):
            try:
                r = await cl.get(
                    'https://api.coingecko.com/api/v3/simple/price',
                    params={'ids': ids, 'vs_currencies': 'usd',
                            'include_24hr_change': 'true'},
                )
                if r.status_code == 200:
                    CACHE.update(t=now, d=r.json())
                    return CACHE['d']
                if r.status_code == 429:
                    await asyncio.sleep(3 * (attempt + 1))
            except Exception:
                await asyncio.sleep(1.5)
    return CACHE['d']


async def fetch_commodities():
    '''Spot prices for oil, platinum, palladium, copper and gas (Yahoo).'''
    out = {}
    async with httpx.AsyncClient(timeout=15, headers=UA) as cl:
        for key, sym in YF.items():
            try:
                r = await cl.get(
                    'https://query1.finance.yahoo.com/v8/finance/chart/'
                    + quote(sym),
                    params={'interval': '1d', 'range': '1d'},
                )
                m = r.json()['chart']['result'][0]['meta']
                out[key] = (float(m['regularMarketPrice']),
                            float(m.get('regularMarketChangePercent') or 0))
            except Exception:
                pass
    return out


async def fetch_movers():
    '''Top 24h gainers for the pump scanner (best effort).'''
    try:
        async with httpx.AsyncClient(timeout=15, headers=UA) as cl:
            r = await cl.get(
                'https://api.coingecko.com/api/v3/coins/markets',
                params={'vs_currency': 'usd',
                        'order': 'percent_change_24h_desc',
                        'per_page': '50', 'page': '1',
                        'price_change_percentage': '24h'},
            )
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return []


def _num(v):
    '''Parse tgju "4,116.02" style strings (fixes missing gold bug).'''
    return float(str(v).replace(',', '').strip())


async def fetch_world():
    out = {}
    nc = int(time.time())
    async with httpx.AsyncClient(timeout=15, headers=UA) as cl:
        for slug, key in (('ons', 'gold'), ('silver', 'silver')):
            try:
                r = await cl.get(
                    f'https://api.tgju.org/v1/market/indicator/today-table-data/{slug}',
                    params={'lang': 'fa', 'nc': nc},
                )
                j = r.json()
                out[key] = _num(j['data'][0][0])
            except Exception:
                # fallback: gold-api.com real-time price
                sym = 'XAU' if key == 'gold' else 'XAG'
                try:
                    r = await cl.get(f'https://api.gold-api.com/price/{sym}')
                    if r.status_code == 200:
                        out[key] = float(r.json()['price'])
                except Exception:
                    pass
        try:
            r = await cl.get('https://api.alternative.me/fng/?limit=1')
            d = r.json()['data'][0]
            out['fng'] = (int(d['value']), d['value_classification'])
        except Exception:
            pass
        try:
            r = await cl.get(
                'https://serviceprovider.tgju.org/fa/partial/market-home-currency-regional',
                params={'tab': 1},
            )
            before = r.text.split('قیمت به ریال')[0]
            nums = re.findall(r'[0-9][0-9,]{5,}', before)
            if nums:
                out['dollar'] = int(nums[-1].replace(',', ''))
            m = re.search(r'ساعت\s*([0-9:]+)', r.text)
            if m:
                out['dollar_t'] = m.group(1)
        except Exception:
            pass
    return out
