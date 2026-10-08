'''Config, state store and i18n helpers for Alien Market Bot v2.'''
import json
import logging
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone, timedelta

from strings_fa import FA
from strings_en import EN

TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHAT_ID = os.environ.get('CHAT_ID', '')
GH_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GH_REPO = os.environ.get('GITHUB_REPOSITORY', '')
TEH = timezone(timedelta(hours=3, minutes=30))
TTL = 60
COOLDOWN = 4 * 3600
TH_STD = (5.0, 3.0)
TH_VIP = (3.0, 2.0)
PUMP_TH = 10.0
PUMP_MIN_VOL = 1000000
PUMP_MAX = 3
PUMP_COOL = {}
PUMP_COOL_SEC = 6 * 3600
WL_BASE, WL_PER_REF, WL_CAP = 10, 5, 50
IDS = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'BNB': 'binancecoin',
       'XRP': 'ripple', 'ADA': 'cardano', 'DOGE': 'dogecoin', 'AVAX': 'avalanche-2',
       'DOT': 'polkadot', 'LINK': 'chainlink', 'TON': 'the-open-network',
       'TRX': 'tron', 'LTC': 'litecoin', 'ATOM': 'cosmos',
       'SUI': 'sui', 'HBAR': 'hedera-hashgraph', 'XLM': 'stellar',
       'NEAR': 'near', 'ARB': 'arbitrum', 'UNI': 'uniswap',
       'SHIB': 'shiba-inu', 'APT': 'aptos'}
# non-crypto watchlist assets -> fetch keys in world/commodities maps
EXTRA = {'GOLD': 'gold', 'SILVER': 'silver', 'BRENT': 'brent',
         'WTI': 'wti', 'PLAT': 'plat', 'PALL': 'pall',
         'COPPER': 'copper', 'GAS': 'gas', 'DOLLAR': 'dollar'}
CATS = {'crypto': list(IDS.keys()),
        'comm': ['GOLD', 'SILVER', 'BRENT', 'WTI', 'PLAT', 'PALL',
                 'COPPER', 'GAS'],
        'fx': ['DOLLAR']}
JMONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
           'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
FILES = {'users': 'state/users.json', 'lists': 'state/userlists.json',
         'refs': 'state/refs.json', 'game': 'state/game.json'}
STATE = {}
BOT_UNAME = ''
CACHE = {'t': 0.0, 'd': {}}
L = {'fa': FA, 'en': EN}
FNG_CLASS_FA = {'Extreme Fear': 'ترس شدید', 'Fear': 'ترس', 'Neutral': 'خنثی',
                'Greed': 'طمع', 'Extreme Greed': 'طمع شدید'}
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('bot')


def _jalali(gy, gm, gd):
    '''Gregorian -> Jalali (jalaali algorithm).'''
    gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) \
        + ((gy2 + 399) // 400) - 80 + gd + gdm[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def _load(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def load_all():
    for k, p in FILES.items():
        STATE[k] = _load(p, {})
    STATE['legacy'] = _load('watchlist.json', [])


def save(key):
    path, data = FILES[key], STATE[key]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception as e:
        log.warning('local save failed %s: %s', path, e)
    if GH_TOKEN and GH_REPO:
        threading.Thread(target=_push_state, args=(path,), daemon=True).start()


def _push_state(path):
    '''Commit a state file back to the repo so Actions runs keep data.'''
    try:
        import base64
        api = f'https://api.github.com/repos/{GH_REPO}/contents/{path}'
        hdr = {'Authorization': f'Bearer {GH_TOKEN}',
               'Accept': 'application/vnd.github+json',
               'User-Agent': 'alien-market-bot'}
        sha = None
        try:
            req = urllib.request.Request(api, headers=hdr)
            with urllib.request.urlopen(req, timeout=20) as r:
                sha = json.loads(r.read()).get('sha')
        except Exception:
            pass
        with open(path, encoding='utf-8') as f:
            content = base64.b64encode(f.read().encode()).decode()
        body = {'message': f'state: update {path}', 'content': content}
        if sha:
            body['sha'] = sha
        req = urllib.request.Request(
            api, data=json.dumps(body).encode(), method='PUT',
            headers={**hdr, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()
    except Exception as e:
        log.warning('state push failed %s: %s', path, e)


def ensure_user(uid, name=''):
    u = STATE['users'].setdefault(str(uid), {})
    changed = False
    if name and u.get('name') != name:
        u['name'] = name
        changed = True
    if 'muted' not in u:
        u['muted'] = False
        changed = True
    if changed:
        save('users')
    STATE['lists'].setdefault(str(uid), [])
    return u


def lang_of(uid):
    lg = str(STATE['users'].get(str(uid), {}).get('lang', 'fa'))
    lg = lg.lstrip(':').lower()
    return 'en' if lg == 'en' else 'fa'


def lang_set(uid):
    return 'lang' in STATE['users'].get(str(uid), {})


def T(uid, key, **kw):
    s = L.get(lang_of(uid), L['fa']).get(key) or L['en'].get(key, key)
    return s.format(**kw) if kw else s


def ref_count(uid):
    return len(STATE['refs'].get(str(uid), []))


def wl_limit(uid):
    return min(WL_CAP, WL_BASE + WL_PER_REF * ref_count(uid))


def is_vip(uid):
    u = STATE['users'].get(str(uid), {})
    return bool(u.get('referred_by')) or ref_count(uid) > 0


def now_fa():
    '''Tehran time with Jalali date, e.g. 16 مهر 1405 — 10:52.'''
    dt = datetime.now(TEH)
    jy, jm, jd = _jalali(dt.year, dt.month, dt.day)
    return f'{jd} {JMONTHS[jm - 1]} {jy} — {dt.strftime("%H:%M")}'


def now_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
