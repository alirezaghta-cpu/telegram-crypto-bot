"""Shared helpers: config, state IO, Telegram API, CoinGecko, i18n."""
import json
import os
import time

import httpx

from strings import T

TOKEN = os.environ.get('TG_BOT_TOKEN', '')
API = ('https://api.telegram.org/bot' + TOKEN) if TOKEN else ''
CHAT_ID = os.environ.get('TG_CHAT_ID', '-1001686062564')
UA = {'User-Agent': 'AlienpanelsBot/2.0'}
USERS_F, WATCH_F, BSTATE_F = 'users.json', 'watchlist.json', 'bot_state.json'
CHANNEL_URL = 'https://t.me/GalaxiesDrop'
BOT_USER = os.environ.get('BOT_USERNAME', 'Alienpanelsbot')
IDS = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'BNB': 'binancecoin',
       'XRP': 'xrp', 'ADA': 'cardano', 'DOGE': 'dogecoin', 'AVAX': 'avalanche-2',
       'LINK': 'chainlink', 'DOT': 'polkadot', 'ARB': 'arbitrum', 'OP': 'optimism'}
COOLDOWN = 3600
FREE_LIMIT = 10
VIP_DAYS = 7
SENS = {'relax': 5.0, 'normal': 3.0, 'high': 1.5}
THR24, MOVE = 5.0, 3.0
EMO = {'BTC': '🟠', 'ETH': '🔷', 'SOL': '◎', 'BNB': '🟡', 'XRP': '✕', 'ADA': '🔵',
       'DOGE': '🐕', 'AVAX': '🔺', 'LINK': '🔗', 'DOT': '●', 'ARB': '⚙️', 'OP': '🔴'}
SENS_KEY = {'relax': 's_relax', 'normal': 's_normal', 'high': 's_high'}


def load(f, d):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return d


def save(f, o):
    with open(f, 'w') as fh:
        json.dump(o, fh, ensure_ascii=False)


def tg(method, **kw):
    try:
        r = httpx.post(API + '/' + method, json=kw, timeout=45)
        j = r.json()
        if not j.get('ok'):
            print('tg fail', method, j.get('error_code'), j.get('description'))
        return j
    except Exception as e:
        print('tg err', method, e)
        return {'ok': False}


def send(chat, text, kb=None):
    kw = {'chat_id': chat, 'text': text, 'parse_mode': 'HTML'}
    if kb:
        kw['reply_markup'] = json.dumps(kb, ensure_ascii=False)
    return tg('sendMessage', **kw)


def edit(chat, mid, text, kb=None):
    kw = {'chat_id': chat, 'message_id': mid, 'text': text, 'parse_mode': 'HTML'}
    if kb:
        kw['reply_markup'] = json.dumps(kb, ensure_ascii=False)
    return tg('editMessageText', **kw)


def answer(cid, text=''):
    kw = {'callback_query_id': cid}
    if text:
        kw['text'] = text
    tg('answerCallbackQuery', **kw)


def cg(cg_ids):
    ids = sorted(set([i for i in cg_ids if i]))
    if not ids:
        return {}
    try:
        r = httpx.get('https://api.coingecko.com/api/v3/simple/price',
                      params={'ids': ','.join(ids), 'vs_currencies': 'usd',
                              'include_24hr_change': 'true'},
                      headers=UA, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print('cg err', e)
        return {}


def tr(lang, key, **kw):
    s = T.get(lang, T['fa']).get(key, key)
    try:
        return s.format(**kw)
    except Exception:
        return s


def is_vip(u):
    return u.get('vip', 0) > time.time()


def wl_limit(u):
    return 50 if is_vip(u) else FREE_LIMIT