'''Threshold alert monitor: runs every 10 minutes, alerts per user.'''
import time

from core import (L, IDS, STATE, CHAT_ID, TH_STD, TH_VIP, COOLDOWN,
                   log, lang_of, now_fa, now_utc, is_vip)
from data import fetch_prices

COOL = {}


def alert_text(chat_id, sym, px, chg, mv):
    fa = lang_of(str(chat_id)) == 'fa'
    t = now_fa() if fa else now_utc()
    return (L['fa'] if fa else L['en'])['alert'].format(
        s=sym, px=f'{px:,.0f}', chg=f'{chg:.2f}', mv=f'{mv:.2f}', t=t)


async def monitor(c):
    targets = {}
    for uid, lst in STATE['lists'].items():
        th = TH_VIP if is_vip(uid) else TH_STD
        for s in lst:
            targets.setdefault(s, []).append((uid, int(uid), th))
    if CHAT_ID:
        for s in STATE.get('legacy', []):
            targets.setdefault(s, []).append(('legacy', int(CHAT_ID), TH_STD))
    if not targets:
        return
    prices = await fetch_prices()
    if not prices:
        return
    now = time.time()
    for sym, tgts in targets.items():
        d = prices.get(IDS.get(sym, ''))
        if not d:
            continue
        px = float(d['usd'])
        chg = float(d.get('usd_24h_change') or 0.0)
        for key, chat, th in tgts:
            last = COOL.get(f'{key}:{sym}')
            mv = abs(px - last['px']) / last['px'] * 100 if last else 0.0
            cooled = (now - last['t']) > COOLDOWN if last else True
            if not cooled:
                continue
            if abs(chg) >= th[0] or mv >= th[1]:
                muted = STATE['users'].get(str(key), {}).get('muted', False)
                if not muted:
                    try:
                        await c.bot.send_message(
                            chat_id=chat,
                            text=alert_text(chat, sym, px, chg, mv),
                            parse_mode='HTML')
                    except Exception as e:
                        log.warning('alert to %s failed: %s', chat, e)
                COOL[f'{key}:{sym}'] = {'t': now, 'px': px}
