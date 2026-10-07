"""Alienpanelsbot v2 — bilingual interactive market bot.
RUN_ONCE=1 -> single poll cycle (GitHub Actions cron); otherwise long-poll loop.
"""
import os
import time

import httpx

from core import (API, BSTATE_F, CHAT_ID, COOLDOWN, EMO, IDS, MOVE, SENS, THR24,
                   TOKEN, USERS_F, WATCH_F, cg, load, save, send, tr)
from menus import (kb_back, kb_lang, kb_menu, prices_rows, show_alerts, show_del,
                   show_menu, show_prices, show_ref, show_set, show_watch)


def uget(users, uid, name=''):
    u = users.get(str(uid))
    if u is None:
        u = {'lang': 'fa', 'alerts': True, 'sens': 'normal', 'muted': False,
             'wlist': {}, 'vip': 0, 'refs': 0, 'ref_used': False,
             'await': None, 'lang_set': False}
        users[str(uid)] = u
    if name and not u.get('name'):
        u['name'] = name
    return u


def ref_link(uid):
    return 'https://t.me/' + os.environ.get('BOT_USERNAME', 'Alienpanelsbot') + '?start=ref' + str(uid)


def handle_start(uid, u, chat, arg, users):
    L = u.get('lang', 'fa')
    if arg.startswith('ref') and not u.get('ref_used'):
        try:
            rid = int(arg[3:])
        except ValueError:
            rid = 0
        ref = users.get(str(rid))
        if rid and ref is not None and rid != uid:
            u['ref_used'] = True
            exp = int(time.time()) + 7 * 86400
            ref['vip'] = max(ref.get('vip', 0), exp)
            u['vip'] = max(u.get('vip', 0), exp)
            ref['refs'] = ref.get('refs', 0) + 1
            send(rid, tr(ref.get('lang', 'fa'), 'ref_got'))
            send(chat, tr(L, 'ref_welcome'))
    if not u.get('lang_set'):
        send(chat, tr(L, 'lang_pick'), kb_lang())
        return
    send(chat, tr(L, 'menu'), kb_menu(L))


def do_add(u, chat, L, sym):
    sym = sym.strip().upper().replace('$', '').replace(' ', '')
    if sym not in IDS:
        send(chat, tr(L, 'bad_sym'))
        return
    wl = u.setdefault('wlist', {})
    if sym in wl:
        send(chat, tr(L, 'dup', s=sym))
        return
    if len(wl) >= 50 if u.get('vip', 0) > time.time() else len(wl) >= 10:
        send(chat, tr(L, 'limit'))
        return
    d = cg([IDS[sym]])
    px = d.get(IDS[sym], {}).get('usd', 0)
    wl[sym] = {'px': px, 'lt': int(time.time())}
    send(chat, tr(L, 'added', s=sym), kb_menu(L))


def do_remove(u, chat, L, sym):
    wl = u.get('wlist', {})
    if sym in wl:
        del wl[sym]
        send(chat, tr(L, 'removed', s=sym), kb_menu(L))
    else:
        send(chat, tr(L, 'nope'))


def channel_wl_text(watch):
    if not watch:
        return tr('fa', 'wl_head_cmd') + '\n—'
    return tr('fa', 'wl_head_cmd') + '\n' + ', '.join(watch)


def on_message(m, users, watch, bstate):
    fr = m.get('from', {})
    if m.get('chat', {}).get('type') != 'private':
        return
    uid = fr.get('id', 0)
    chat = m['chat']['id']
    u = uget(users, uid, fr.get('first_name', ''))
    L = u.get('lang', 'fa')
    txt = (m.get('text') or '').strip()
    if not txt:
        return
    parts = txt.split()
    cmd = parts[0].split('@')[0].lower()
    arg = parts[1] if len(parts) > 1 else ''
    if cmd == '/start':
        handle_start(uid, u, chat, arg, users)
        return
    if cmd == '/lang':
        send(chat, tr(L, 'lang_pick'), kb_lang())
        return
    if cmd == '/menu':
        u['lang_set'] = True
        send(chat, tr(L, 'menu'), kb_menu(L))
        return
    if cmd == '/help':
        send(chat, tr(L, 'help_t'), kb_menu(L))
        return
    if cmd == '/ref':
        send(chat, tr(L, 'ref_t', link=ref_link(uid), n=u.get('refs', 0)), kb_menu(L))
        return
    if cmd == '/mute':
        u['muted'] = not u.get('muted', False)
        if u.get('muted'):
            send(chat, tr(L, 'muted_on'))
        else:
            send(chat, tr(L, 'muted_off'))
        return
    if cmd == '/price':
        if arg and arg.upper() in IDS:
            s = arg.upper()
            d = cg([IDS[s]]).get(IDS[s], {})
            if d:
                send(chat, '{e} {s}: ${p} ({c:+.2f}%)'.format(
                    e=EMO.get(s, '💲'), s=s, p=format(int(d['usd']), ','),
                    c=d.get('usd_24h_change') or 0.0))
            else:
                send(chat, tr(L, 'nudge'))
        else:
            lines = prices_rows(u)
            send(chat, tr(L, 'prices_t') + '\n' + '\n'.join(lines), kb_menu(L))
        return
    if cmd == '/add':
        if not arg:
            u['await'] = 'add'
            send(chat, tr(L, 'ask_sym'))
            return
        do_add(u, chat, L, arg)
        return
    if cmd == '/watchlist':
        send(chat, channel_wl_text(watch), kb_menu(L))
        return
    if cmd == '/remove':
        if not arg:
            u['await'] = 'del'
            send(chat, tr(L, 'ask_sym'))
            return
        do_remove(u, chat, L, arg.upper())
        return
    if cmd == '/chadd' and arg:
        s = arg.upper()
        if s in IDS and s not in watch:
            watch.append(s)
            send(chat, tr('fa', 'added_ch', s=s, n=len(watch)))
            send(CHAT_ID, tr('fa', 'added_ch', s=s, n=len(watch)))
        return
    if cmd == '/chremove' and arg:
        s = arg.upper()
        if s in watch:
            watch.remove(s)
            send(chat, tr('fa', 'removed_ch', s=s, n=len(watch)))
            send(CHAT_ID, tr('fa', 'removed_ch', s=s, n=len(watch)))
        return
    if u.get('await') == 'add':
        u['await'] = None
        do_add(u, chat, L, txt)
        return
    if u.get('await') == 'del':
        u['await'] = None
        do_remove(u, chat, L, txt.upper())
        return
    send(chat, tr(L, 'nudge'), kb_menu(L))


def on_callback(cb, users):
    cid = cb['id']
    uid = cb['from']['id']
    msg = cb.get('message') or {}
    chat = msg.get('chat', {}).get('id')
    mid = msg.get('message_id')
    data = cb.get('data', '')
    u = uget(users, uid, cb['from'].get('first_name', ''))
    L = u.get('lang', 'fa')
    if data.startswith('lang:'):
        from core import answer
        answer(cid)
        u['lang'] = data.split(':', 1)[1]
        u['lang_set'] = True
        L = u['lang']
        edit2 = tr(L, 'lang_ok') + '\n\n' + tr(L, 'menu')
        from core import edit
        edit(chat, mid, edit2, kb_menu(L))
        return
    if data == 'a:sens:high' and u.get('vip', 0) <= time.time():
        from core import answer
        answer(cid, tr(L, 'vip_only'))
        return
    from core import answer
    answer(cid)
    if data == 'm:menu':
        show_menu(chat, mid, L)
    elif data == 'm:prices':
        show_prices(u, chat, mid, L)
    elif data == 'm:watch':
        show_watch(u, chat, mid, L)
    elif data == 'm:add':
        u['await'] = 'add'
        from core import edit
        edit(chat, mid, tr(L, 'ask_sym'), kb_back(L))
    elif data == 'm:del':
        show_del(u, chat, mid, L)
    elif data.startswith('x:'):
        sym = data[2:]
        if sym in u.get('wlist', {}):
            del u['wlist'][sym]
        show_del(u, chat, mid, L)
    elif data == 'm:alerts':
        show_alerts(u, chat, mid, L)
    elif data == 'a:toggle':
        u['alerts'] = not u.get('alerts', True)
        show_alerts(u, chat, mid, L)
    elif data.startswith('a:sens:'):
        u['sens'] = data.split(':', 2)[2]
        show_alerts(u, chat, mid, L)
    elif data == 'm:set':
        show_set(u, chat, mid, L)
    elif data == 'm:langpick':
        from core import edit
        edit(chat, mid, tr(L, 'lang_pick'), kb_lang())
    elif data == 's:mute':
        u['muted'] = not u.get('muted', False)
        show_set(u, chat, mid, L)
    elif data == 'm:ref':
        show_ref(uid, chat, mid, L, u.get('refs', 0))
    elif data == 'm:help':
        from core import edit
        edit(chat, mid, tr(L, 'help_t'), kb_back(L))
    else:
        show_menu(chat, mid, L)


def run_monitors(users, bstate, watch):
    ids = [IDS[s] for s in watch if s in IDS]
    for u in users.values():
        for s in u.get('wlist', {}):
            if s in IDS:
                ids.append(IDS[s])
    if not ids:
        return
    data = cg(ids)
    now = int(time.time())
    last = bstate.setdefault('LAST', {})
    for s in watch:
        d = data.get(IDS.get(s, ''), {})
        if not d:
            continue
        px = float(d['usd'])
        ch = float(d.get('usd_24h_change') or 0.0)
        st = last.get(s) or {'px': px, 't': 0}
        cooled = (now - st.get('t', 0)) > COOLDOWN
        prev = st.get('px', px) or px
        move = abs(px - prev) / prev * 100
        if cooled and (abs(ch) >= THR24 or move >= MOVE):
            send(CHAT_ID, tr('fa', 'ch_alert', s=s, p='$' + format(int(px), ','),
                             c='{:+.2f}'.format(ch)))
            last[s] = {'px': px, 't': now}
    for uid, u in users.items():
        if not u.get('alerts') or u.get('muted'):
            continue
        th = SENS.get(u.get('sens', 'normal'), 3.0)
        lu = u.get('lang', 'fa')
        for s, ent in u.get('wlist', {}).items():
            d = data.get(IDS.get(s, ''), {})
            if not d:
                continue
            ch = abs(float(d.get('usd_24h_change') or 0.0))
            if ch >= th and (now - ent.get('lt', 0)) >= COOLDOWN:
                send(uid, tr(lu, 'alert_msg', s=s, p='$' + format(int(d['usd']), ','),
                             c='{:+.2f}'.format(ch)))
                ent['lt'] = now


def cycle(users, bstate, watch, timeout):
    off = bstate.get('offset', 0)
    try:
        r = httpx.post(API + '/getUpdates',
                       json={'offset': off, 'timeout': timeout,
                             'allowed_updates': ['message', 'callback_query']},
                       timeout=timeout + 20)
        updates = r.json().get('result', [])
    except Exception as e:
        print('poll err', e)
        updates = []
    for up in updates:
        bstate['offset'] = up['update_id'] + 1
        try:
            if 'callback_query' in up:
                on_callback(up['callback_query'], users)
            elif 'message' in up:
                on_message(up['message'], users, watch, bstate)
        except Exception as e:
            print('handle err', e)
    try:
        run_monitors(users, bstate, watch)
    except Exception as e:
        print('monitor err', e)
    save(USERS_F, users)
    save(BSTATE_F, bstate)
    save(WATCH_F, watch)


def main():
    if not TOKEN:
        raise SystemExit('TG_BOT_TOKEN missing')
    users = load(USERS_F, {})
    watch = load(WATCH_F, ['BTC', 'ETH', 'SOL'])
    bstate = load(BSTATE_F, {'offset': 0, 'LAST': {}})
    if not isinstance(watch, list):
        watch = ['BTC', 'ETH', 'SOL']
    if not isinstance(bstate, dict):
        bstate = {'offset': 0, 'LAST': {}}
    bstate.setdefault('LAST', {})
    if os.environ.get('RUN_ONCE') == '1':
        cycle(users, bstate, watch, 30)
        return
    while True:
        try:
            cycle(users, bstate, watch, 50)
        except Exception as e:
            print('cycle err', e)
            time.sleep(5)


if __name__ == '__main__':
    main()