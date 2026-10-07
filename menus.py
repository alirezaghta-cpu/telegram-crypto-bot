"""Inline keyboards and menu views for bot v2."""
import time

from core import (BOT_USER, EMO, IDS, SENS_KEY, cg, edit, is_vip, tr)


def kb_back(L):
    return [[{'text': tr(L, 'b_back'), 'callback_data': 'm:menu'}]]


def kb_menu(L):
    return [
        [{'text': tr(L, 'b_prices'), 'callback_data': 'm:prices'},
         {'text': tr(L, 'b_watch'), 'callback_data': 'm:watch'}],
        [{'text': tr(L, 'b_add'), 'callback_data': 'm:add'},
         {'text': tr(L, 'b_del'), 'callback_data': 'm:del'}],
        [{'text': tr(L, 'b_alerts'), 'callback_data': 'm:alerts'},
         {'text': tr(L, 'b_set'), 'callback_data': 'm:set'}],
        [{'text': tr(L, 'b_ref'), 'callback_data': 'm:ref'},
         {'text': tr(L, 'b_help'), 'callback_data': 'm:help'}],
    ]


def kb_lang():
    return [[{'text': '🇮🇷 فارسی', 'callback_data': 'lang:fa'},
             {'text': '🇬🇧 English', 'callback_data': 'lang:en'}]]


def kb_alerts(u, L):
    cur = u.get('sens', 'normal')
    rows = [[{'text': tr(L, 'b_off') if u.get('alerts') else tr(L, 'b_on'),
              'callback_data': 'a:toggle'}]]
    row = []
    for k in ('relax', 'normal', 'high'):
        lab = tr(L, SENS_KEY[k])
        if cur == k:
            lab = '• ' + lab
        row.append({'text': lab, 'callback_data': 'a:sens:' + k})
    rows.append(row)
    rows.append(kb_back(L)[0])
    return rows


def prices_rows(u):
    syms = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP'] + list(u.get('wlist', {}).keys())
    seen = []
    for s in syms:
        if s not in seen:
            seen.append(s)
    data = cg([IDS.get(s) for s in seen])
    lines = []
    for s in seen:
        d = data.get(IDS.get(s, ''), {})
        if not d:
            continue
        ch = d.get('usd_24h_change') or 0.0
        lines.append('{e} {s}: ${p} ({c:+.2f}%)'.format(
            e=EMO.get(s, '💲'), s=s, p=format(int(d['usd']), ','), c=ch))
    return lines


def show_menu(chat, mid, L):
    edit(chat, mid, tr(L, 'menu'), kb_menu(L))


def show_prices(u, chat, mid, L):
    lines = prices_rows(u)
    if lines:
        txt = tr(L, 'prices_t') + '\n' + '\n'.join(lines)
    else:
        txt = tr(L, 'prices_t') + '\n—'
    edit(chat, mid, txt, kb_back(L))


def show_watch(u, chat, mid, L):
    wl = u.get('wlist', {})
    if not wl:
        edit(chat, mid, tr(L, 'watch_t') + tr(L, 'watch_empty'), kb_back(L))
        return
    data = cg([IDS.get(s) for s in wl])
    lines = []
    for s in wl:
        d = data.get(IDS.get(s, ''), {})
        px = d.get('usd')
        if px:
            lines.append('{e} {s}: ${p}'.format(
                e=EMO.get(s, ''), s=s, p=format(int(px), ',')))
        else:
            lines.append('{e} {s}'.format(e=EMO.get(s, ''), s=s))
    edit(chat, mid, tr(L, 'watch_t') + '\n' + '\n'.join(lines), kb_back(L))


def show_del(u, chat, mid, L):
    wl = list(u.get('wlist', {}).keys())
    if not wl:
        edit(chat, mid, tr(L, 'no_wl_item'), kb_back(L))
        return
    rows = [[{'text': '🗑 ' + s, 'callback_data': 'x:' + s}] for s in wl]
    rows.append(kb_back(L)[0])
    edit(chat, mid, tr(L, 'b_del'), rows)


def show_alerts(u, chat, mid, L):
    st = u.get('sens', 'normal')
    if u.get('muted'):
        status = tr(L, 's_muted')
    elif u.get('alerts'):
        status = tr(L, 's_on')
    else:
        status = tr(L, 's_off')
    txt = tr(L, 'alerts_t', st=status, sn=tr(L, SENS_KEY[st]))
    edit(chat, mid, txt, kb_alerts(u, L))


def show_set(u, chat, mid, L):
    mt = tr(L, 's_muted') if u.get('muted') else tr(L, 's_on')
    if is_vip(u):
        vp = tr(L, 'vp_on', d=time.strftime('%Y-%m-%d', time.gmtime(u.get('vip', 0))))
    else:
        vp = tr(L, 'vp_no')
    rows = [[{'text': tr(L, 'b_lang'), 'callback_data': 'm:langpick'},
             {'text': tr(L, 'b_mute_off') if u.get('muted') else tr(L, 'b_mute_on'),
              'callback_data': 's:mute'}]]
    rows.append(kb_back(L)[0])
    edit(chat, mid, tr(L, 'set_t', lg=tr(L, 'lg_' + u.get('lang', 'fa')), mt=mt, vp=vp), rows)


def show_ref(uid, chat, mid, L, n):
    link = 'https://t.me/' + BOT_USER + '?start=ref' + str(uid)
    edit(chat, mid, tr(L, 'ref_t', link=link, n=n), kb_back(L))