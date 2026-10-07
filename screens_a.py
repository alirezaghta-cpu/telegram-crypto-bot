'''Screens A: main menu, prices, fear & greed, watchlist.'''
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core import (T, lang_of, now_fa, now_utc, FNG_CLASS_FA, IDS,
                   wl_limit, is_vip, STATE)
from data import fetch_prices, fetch_world, fetch_commodities
from ui import out, menu_kb, back_kb

COMM_KEYS = (('brent', 'wti'), ('plat', 'pall'), ('copper', 'gas'))


def _px(v):
    '''Format a USD price so small-cap prices stay readable.'''
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 1:
        return f"{v:,.2f}"
    if v >= 0.01:
        return f"{v:.4f}"
    return f"{v:.8f}"


async def show_menu(u, edit=False):
    uid = u.effective_user.id
    await out(u, T(uid, 'menu'), menu_kb(uid), edit)


async def show_prices(u, edit=False):
    uid = u.effective_user.id
    prices = await fetch_prices()
    world = await fetch_world()
    comm = await fetch_commodities()
    fa = lang_of(uid) == 'fa'
    lines = [T(uid, 'prices_head', t=now_fa() if fa else now_utc()), '']
    if fa and world.get('dollar'):
        dt = (f"{now_fa()[:10]} {world['dollar_t']}"
              if world.get('dollar_t') else now_fa())
        lines.append(T(uid, 'dollar', v=f"{world['dollar']:,}", t=dt))
    comms = []
    if world.get('gold'):
        comms.append(T(uid, 'gold', v=f"{world['gold']:,.2f}"))
    if world.get('silver'):
        comms.append(T(uid, 'silver', v=f"{world['silver']:,.2f}"))
    for keys in COMM_KEYS:
        for key in keys:
            d = comm.get(key)
            if d:
                comms.append(T(uid, key, v=f"{d[0]:,.2f}",
                               c=f"{d[1]:.2f}"))
    if comms:
        lines.append(T(uid, 'comm_head'))
        lines.extend(comms)
    for cg, key in (('bitcoin', 'btc'), ('ethereum', 'eth')):
        d = prices.get(cg)
        if d:
            lines.append(T(uid, key, v=f"{d['usd']:,.0f}",
                           c=f"{d.get('usd_24h_change') or 0:.2f}"))
    if world.get('fng'):
        v, cls = world['fng']
        if fa:
            cls = FNG_CLASS_FA.get(cls, cls)
        lines.append(T(uid, 'fng_line', v=v, c=cls))
    grid = []
    for sym in IDS:
        if sym in ('BTC', 'ETH'):
            continue
        d = prices.get(IDS[sym])
        if d:
            grid.append(f"{sym}: {_px(d['usd'])} USD "
                        f"({d.get('usd_24h_change') or 0:.1f}%)")
    if grid:
        lines.append('')
        lines.append('🪙 رمزارزهای مهم:' if fa else '🪙 Major coins:')
        lines.extend(grid)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T(uid, 'btn_refresh'), callback_data='prices')],
        [InlineKeyboardButton(T(uid, 'btn_list'), callback_data='list'),
         InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')],
    ])
    await out(u, '\n'.join(lines), kb, edit)


async def show_fng(u, edit=False):
    uid = u.effective_user.id
    world = await fetch_world()
    fa = lang_of(uid) == 'fa'
    if not world.get('fng'):
        await out(u, '⚠️ ' + T(uid, 'hint'), back_kb(uid), edit)
        return
    v, cls = world['fng']
    if fa:
        cls = FNG_CLASS_FA.get(cls, cls)
    await out(u, T(uid, 'fng_head', v=v, c=cls), back_kb(uid), edit)


async def show_list(u, edit=False):
    uid = u.effective_user.id
    lst = STATE['lists'].get(str(uid), [])
    limit = wl_limit(uid)
    badge = T(uid, 'vip') if is_vip(uid) else T(uid, 'std')
    if not lst:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(T(uid, 'btn_add'), callback_data='add')],
            [InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')],
        ])
        text = (T(uid, 'list_head', n=0, limit=limit, badge=badge)
                + '\n\n' + T(uid, 'list_empty'))
        await out(u, text, kb, edit)
        return
    prices = await fetch_prices()
    lines = [T(uid, 'list_head', n=len(lst), limit=limit, badge=badge), '']
    for s in lst:
        d = prices.get(IDS.get(s, ''), {})
        if d:
            lines.append(f"{s}: {d['usd']:,.0f} USD "
                         f"({d.get('usd_24h_change') or 0:.1f}%)")
        else:
            lines.append(f'{s}: —')
    rows = [[InlineKeyboardButton(f'❌ {s}', callback_data=f'del:{s}')]
            for s in lst]
    rows.append([InlineKeyboardButton(T(uid, 'btn_add'), callback_data='add'),
                 InlineKeyboardButton(T(uid, 'btn_refresh'), callback_data='list')])
    rows.append([InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')])
    await out(u, '\n'.join(lines), InlineKeyboardMarkup(rows), edit)