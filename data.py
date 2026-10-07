'''Live market data fetchers (CoinGecko, tgju.org, alternative.me).'''
import asyncio
import re
import time

import httpx

from core import CACHE, IDS, TTL

UA = {'User-Agent': 'alien-market-bot/2.0'}


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
                out[key] = float(j['data'][0][0])
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
