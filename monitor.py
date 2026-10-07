'''Threshold alert monitor + pump scanner: runs every 10 minutes.'''
import time

from core import (L, IDS, STATE, CHAT_ID, TH_STD, TH_VIP, COOLDOWN,
                   PUMP_TH, PUMP_MIN_VOL, PUMP_MAX, PUMP_COOL, PUMP_COOL_SEC,
                   log, lang_of, now_fa, now_utc, is_vip)
from data import fetch_prices, fetch_movers

COOL = {}


def alert_text(chat_id, sym, px, chg, mv):
    fa = lang_of(str(chat_id)) == 'fa'
    t = now_fa() if fa else now_utc()
    return (L['fa'] if fa else L['en'])['alert'].format(
        s=sym, px=f'{px:,.0f}', chg=f'{chg:.2f}', mv=f'{mv:.2f}', t=t)


async def pump_scan(c):
    '''Notify the channel about coins pumping hard right now.'''
    if not CHAT_ID:
        return
    rows = await fetch_movers()
    if not rows:
        return
    now = time.time()
    sent = 0
    for d in rows:
        if sent >= PUMP_MAX:
            break
        try:
            chg = float(d.get('price_change_percentage_24h') or 0.0)
            px = float(d.get('current_price') or 0.0)
            vol = float(d.get('total_volume') or 0.0)
        except (TypeError, ValueError):
            continue
        if chg < PUMP_TH or px <= 0 or vol < PUMP_MIN_VOL:
            continue
        cid = d.get('id') or d.get('symbol') or ''
        if not cid:
            continue
        last = PUMP_COOL.get(cid)
        if last and now - last < PUMP_COOL_SEC:
            continue
        sym = str(d.get('symbol') or cid).upper()
        # پمپ‌ها را با زبان فارسی کانال ارسال می‌کنیم.
        text = L['fa']['pump'].format(
            s=sym, px=f'{px:,.4f}' if px < 1 else f'{px:,.2f}',
            chg=f'{chg:.1f}', vol=f'{vol / 1_000_000:,.1f}', t=now_fa())
        try:
            await c.bot.send_message(chat_id=CHAT_ID, text=text,
                                     parse_mode='HTML')
            PUMP_COOL[cid] = now
            sent += 1
        except Exception as e:
            log.warning('pump alert to %s failed: %s', CHAT_ID, e)
            PUMP_COOL[cid] = now


async def monitor(c):
    try:
        await pump_scan(c)
    except Exception as e:
        log.warning('pump scan failed: %s', e)
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