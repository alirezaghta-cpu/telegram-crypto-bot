"""GalaxiesDrop scheduled market bulletins for GitHub Actions.
Usage: python bulletin.py full|fullEN|check|dryrun
No source attribution in posts. English text uses UTC. Photo card generated
at runtime with Pillow; falls back to plain text if anything fails.
"""
import datetime as dt
import io
import json
import os
import random
import sys
import time

import httpx

TOKEN = os.environ.get('TG_BOT_TOKEN', '')
CHAT = os.environ.get('TG_CHAT_ID', '-1001686062564')
STATE_F = 'bulletin_state.json'
UA = {'User-Agent': 'Mozilla/5.0 GalaxiesDropBulletin/2.0'}
TEH = dt.timezone(dt.timedelta(hours=3, minutes=30))
MONTHS_FA = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
             'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
DAYS_FA = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه']
DAYS_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December']
BUTTONS = {'inline_keyboard': [[
    {'text': '🤖 ربات اختصاصی', 'url': 'https://t.me/Alienpanelsbot'},
    {'text': '📣 کانال', 'url': 'https://t.me/GalaxiesDrop'},
]]}
THRESH = {'dollar': 1.0, 'ons': 1.0, 'silver': 1.5, 'btc': 3.0, 'eth': 3.0}
NAMES = {'dollar': 'دلار آزاد', 'ons': 'انس طلا', 'silver': 'انس نقره',
         'btc': 'بیت‌کوین', 'eth': 'اتریوم'}
EMOJI = {'dollar': '🇺🇸', 'ons': '🥇', 'silver': '🥈', 'btc': '🟠', 'eth': '🔷'}
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')


def log(*a):
    print(*a, flush=True)


def first_num(s):
    s = str(s).translate(DIGITS)
    i = 1 if s[:1] == '-' else 0
    out = s[:i]
    started = False
    for c in s[i:]:
        if c.isdigit() or (c in '.,' and started):
            out += c
            started = True
        else:
            break
    try:
        return float(out.replace(',', ''))
    except ValueError:
        return None


def strip_tags(html):
    txt = html
    while '<' in txt:
        a = txt.find('<')
        b = txt.find('>', a)
        if b < 0:
            break
        txt = txt[:a] + ' ' + txt[b + 1:]
    return ' '.join(txt.translate(DIGITS).split())


def fetch_dollar(c):
    last = ''
    for _i in range(2):
        try:
            r = c.get('https://serviceprovider.tgju.org/fa/partial/market-home-currency-regional?tab=1')
            r.raise_for_status()
            txt = strip_tags(r.text)
            v = None
            k = txt.find('قیمت به ریال')
            if k > 0:
                v = first_num(txt[max(0, k - 30):k])
            if v is None and k >= 0:
                v = first_num(txt[k:k + 30])
            chg = ''
            k2 = txt.find('تغییر روزانه')
            if k2 >= 0:
                seg = txt[k2 + 12:k2 + 32].split(' ')
                if seg:
                    chg = seg[0]
            clk = ''
            k3 = txt.find('ساعت')
            if k3 >= 0:
                seg = txt[k3 + 4:k3 + 16].split(' ')
                if seg:
                    clk = seg[0]
            if v:
                return {'rial': v, 'chg': chg, 't': clk}
            last = 'pattern miss in: ' + txt[:120]
        except Exception as e:
            last = str(e)
        time.sleep(2)
    raise RuntimeError('dollar source failed: ' + last)


def row_age_min(tstr, now):
    try:
        tstr = (tstr or '').strip()
        if not tstr:
            return 999
        if len(tstr) > 8:
            row = dt.datetime.fromisoformat(tstr)
            if row.tzinfo is None:
                row = row.replace(tzinfo=TEH)
            else:
                row = row.astimezone(TEH)
        else:
            hms = tstr.split(':')
            row = now.astimezone(TEH).replace(
                hour=int(hms[0]), minute=int(hms[1]), second=0, microsecond=0)
        return (now.astimezone(TEH) - row).total_seconds() / 60.0
    except Exception:
        return 999


def fetch_table(c, slug):
    now = dt.datetime.now(dt.timezone.utc)
    for _i in range(2):
        try:
            r = c.get('https://api.tgju.org/v1/market/indicator/today-table-data/'
                      + slug + '?lang=fa&nc=' + str(int(time.time() * 1000)))
            r.raise_for_status()
            data = r.json().get('data') or []
            if data and data[0]:
                px = first_num(data[0][0])
                tstr = str(data[0][1]) if len(data[0]) > 1 else ''
                if px is not None and row_age_min(tstr, now) <= 30:
                    return {'px': px, 't': tstr}
        except Exception as e:
            log('table err', slug, e)
        time.sleep(2)
    code = 'XAU' if slug == 'ons' else 'XAG'
    r = c.get('https://gold-api.com/price/' + code)
    r.raise_for_status()
    px = first_num(r.json().get('price', ''))
    if px is None:
        raise RuntimeError('ounce source failed: ' + slug)
    log('fallback gold-api for', slug)
    return {'px': px, 't': ''}


def fetch_cg(c):
    for _i in range(2):
        r = c.get('https://api.coingecko.com/api/v3/simple/price',
                  params={'ids': 'bitcoin,ethereum', 'vs_currencies': 'usd',
                          'include_24hr_change': 'true'})
        if r.status_code == 200:
            j = r.json()
            return {'btc': {'px': float(j['bitcoin']['usd']),
                            'chg': float(j['bitcoin'].get('usd_24h_change') or 0.0)},
                    'eth': {'px': float(j['ethereum']['usd']),
                            'chg': float(j['ethereum'].get('usd_24h_change') or 0.0)}}
        time.sleep(3)
    raise RuntimeError('coingecko failed')


def fetch_fng(c):
    r = c.get('https://api.alternative.me/fng/?limit=1')
    r.raise_for_status()
    d = r.json()['data'][0]
    return {'v': int(d['value']),
            'cls': d.get('value_classification') or d.get('classification') or ''}


def fetch_all(c, need_dollar=True):
    d = {}
    if need_dollar:
        d['dollar'] = fetch_dollar(c)
    d['ons'] = fetch_table(c, 'ons')
    d['silver'] = fetch_table(c, 'silver')
    d.update(fetch_cg(c))
    d['fng'] = fetch_fng(c)
    return d


def snapshot(d):
    s = {'ons': d['ons']['px'], 'silver': d['silver']['px'],
         'btc': d['btc']['px'], 'eth': d['eth']['px'], 'fng': d['fng']['v'],
         't': int(time.time())}
    if 'dollar' in d:
        s['dollar'] = d['dollar']['rial']
    return s


def load_state():
    try:
        with open(STATE_F) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    with open(STATE_F, 'w') as f:
        json.dump(s, f, ensure_ascii=False)


def rial_fmt(v):
    v = int(round(v))
    if v >= 10 ** 12:
        return '{:.2f} تریلیون ریال'.format(v / 10 ** 12)
    if v >= 10 ** 9:
        return '{:.2f} میلیارد ریال'.format(v / 10 ** 9)
    if v >= 10 ** 6:
        return '{:.2f} میلیون ریال'.format(v / 10 ** 6)
    return '{:,} ریال'.format(v)


def pct(ch):
    return '{:+.2f}%'.format(ch)


def arrow(ch):
    if ch > 0.1:
        return 'رو به بالا 📈'
    if ch < -0.1:
        return 'رو به پایین 📉'
    return 'بدون تغییر محسوس ➖'


def arrow_en(ch):
    if ch > 0.1:
        return 'up 📈'
    if ch < -0.1:
        return 'down 📉'
    return 'flat ➖'


def compose_full(d, kind, now_utc):
    teh = now_utc.astimezone(TEH)
    try:
        import jdatetime
        jd = jdatetime.date.fromgregorian(date=theh.date())
        date_fa = '{} {} {} {}'.format(DAYS_FA[theh.weekday()], jd.day,
                                       MONTHS_FA[jd.month - 1], jd.year)
    except Exception:
        date_fa = teh.strftime('%Y-%m-%d')
    head = '🌅 بولتن صبحگاهی بازار' if kind == 'morning' else '🌙 بولتن شبانه بازار'
    btc_ch = d['btc']['chg']
    eth_ch = d['eth']['chg']
    summary = '✍️ جمع‌بندی: رمزارزها {} — اگه نوسان مهمی پیش بیاد همینجا خودکار اعلام می‌شه.'.format(
        arrow((btc_ch + eth_ch) / 2))
    lines = [
        '<b>{}</b>'.format(head),
        '📆 {} | 🕖 {} به وقت تهران'.format(date_fa, teh.strftime('%H:%M')),
        '',
        '🇺🇸 <b>دلار آزاد:</b> {:,} ریال{}{}'.format(
            int(d['dollar']['rial']),
            ' ({})'.format(d['dollar']['chg']) if d['dollar']['chg'] else '',
            ' — ساعت {}'.format(d['dollar']['t']) if d['dollar']['t'] else ''),
        '🥇 <b>انس جهانی طلا:</b> ${:,.2f}/oz — ارزش ریالی {}'.format(
            d['ons']['px'], rial_fmt(d['ons']['px'] * d['dollar']['rial'])),
        '🥈 <b>انس نقره:</b> ${:,.2f}/oz — ارزش ریالی {}'.format(
            d['silver']['px'], rial_fmt(d['silver']['px'] * d['dollar']['rial'])),
        '🟠 <b>بیت‌کوین:</b> ${:,} ({} ۲۴ ساعت)'.format(int(d['btc']['px']), pct(btc_ch)),
        '🔷 <b>اتریوم:</b> ${:,} ({} ۲۴ ساعت)'.format(int(d['eth']['px']), pct(eth_ch)),
        '🌡 <b>شاخص ترس و طمع:</b> {} — {}'.format(d['fng']['v'], d['fng']['cls']),
        '',
        summary,
    ]
    return '\n'.join(lines)


def compose_fullEN(d, kind, now_utc):
    u = now_utc.astimezone(dt.timezone.utc)
    head = '☀️ Morning Market Brief' if kind == 'morning' else '🌙 Night Market Brief'
    btc_ch = d['btc']['chg']
    eth_ch = d['eth']['chg']
    summary = '✍️ Summary: crypto is {} over 24h; big move ahead and it gets posted here.'.format(
        arrow_en((btc_ch + eth_ch) / 2))
    lines = [
        '<b>{}</b>'.format(head),
        '📆 {}, {} {}, {} | 🕓 {} UTC'.format(
            DAYS_EN[u.weekday()], MONTHS_EN[u.month - 1], u.day, u.year,
            u.strftime('%H:%M')),
        '',
        '🥇 World Gold: ${:,.2f}/oz'.format(d['ons']['px']),
        '🥈 World Silver: ${:,.2f}/oz'.format(d['silver']['px']),
        '🟠 Bitcoin: ${:,} ({} 24h)'.format(int(d['btc']['px']), pct(btc_ch)),
        '🔷 Ethereum: ${:,} ({} 24h)'.format(int(d['eth']['px']), pct(eth_ch)),
        '🌡 Fear & Greed: {} — {}'.format(d['fng']['v'], d['fng']['cls']),
        '',
        summary,
    ]
    return '\n'.join(lines)


def compose_check(d, snap):
    msgs = []
    teh = dt.datetime.now(dt.timezone.utc).astimezone(TEH)
    for key in ('dollar', 'ons', 'silver', 'btc', 'eth'):
        cur = d[key]['rial'] if key == 'dollar' else d[key]['px']
        prev = snap.get(key)
        if not prev or cur <= 0:
            continue
        mv = (cur - prev) / prev * 100
        if abs(mv) < THRESH[key]:
            continue
        if key == 'dollar':
            body = '{:,} ریال'.format(int(cur))
        elif key in ('ons', 'silver'):
            body = '${:,.2f}/oz — ارزش ریالی {}'.format(
                cur, rial_fmt(cur * d['dollar']['rial']))
        else:
            body = '${:,}'.format(int(cur))
        msgs.append(
            '{} <b>تغییر مهم {}</b>\n{}: {} ({:+.2f}٪ نسبت به آخرین پست)\n🕒 {} به وقت تهران'.format(
                EMOJI[key], NAMES[key], NAMES[key], body, mv, teh.strftime('%H:%M')))
    return msgs


def make_card(kind, d):
    try:
        from PIL import Image, ImageDraw, ImageFont
        W, H = 1200, 630
        if kind == 'morning':
            c1, c2 = (250, 140, 50), (180, 70, 25)
        else:
            c1, c2 = (13, 30, 66), (78, 45, 130)
        img = Image.new('RGB', (W, H))
        dr = ImageDraw.Draw(img)
        for y in range(H):
            t = y / float(H - 1)
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            dr.line([(0, y), (W, y)], fill=col)
        if kind == 'morning':
            dr.ellipse([W - 300, -110, W + 110, 300], fill=(255, 233, 170))
        else:
            rnd = random.Random(7)
            for _i in range(80):
                x = rnd.randrange(W)
                y = rnd.randrange(H)
                r = rnd.choice([1, 1, 2])
                dr.ellipse([x, y, x + r, y + r], fill=(225, 228, 255))
            dr.ellipse([W - 300, 60, W - 150, 210], fill=(238, 236, 214))
        font_paths = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                      '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf']
        f_big = None
        f_small = None
        for p in font_paths:
            try:
                f_big = ImageFont.truetype(p, 46)
                f_small = ImageFont.truetype(p, 26)
                break
            except Exception:
                continue
        if f_big is None:
            return None
        title = 'MORNING MARKET BRIEF' if kind == 'morning' else 'NIGHT MARKET BRIEF'
        dr.text((48, 40), title, font=f_big, fill=(255, 255, 255))
        cells = [('WORLD GOLD', '${:,.2f}'.format(d['ons']['px']), 48, 170),
                 ('SILVER', '${:,.2f}'.format(d['silver']['px']), 620, 170),
                 ('BITCOIN', '${:,}'.format(int(d['btc']['px'])), 48, 380),
                 ('ETHEREUM', '${:,}'.format(int(d['eth']['px'])), 620, 380)]
        for lab, val, x, y in cells:
            dr.text((x, y), lab, font=f_small, fill=(255, 244, 224))
            dr.text((x, y + 34), val, font=f_big, fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        return buf.getvalue()
    except Exception as e:
        log('card fail', e)
        return None


def tg(method, **kw):
    with httpx.Client(timeout=50, headers=UA) as c:
        r = c.post('https://api.telegram.org/bot' + TOKEN + '/' + method, json=kw)
        j = r.json()
        if not j.get('ok'):
            raise RuntimeError('telegram {}: {} {}'.format(
                method, j.get('error_code'), j.get('description')))
        return j


def send_text(text, buttons=True):
    kw = {'chat_id': CHAT, 'text': text, 'parse_mode': 'HTML'}
    if buttons:
        kw['reply_markup'] = json.dumps(BUTTONS, ensure_ascii=False)
    return tg('sendMessage', **kw)


def send_bulletin(text, kind, d):
    if len(text) <= 1020:
        img = make_card(kind, d)
        if img:
            try:
                with httpx.Client(timeout=60, headers=UA) as c:
                    r = c.post('https://api.telegram.org/bot' + TOKEN + '/sendPhoto',
                               data={'chat_id': CHAT, 'caption': text,
                                     'parse_mode': 'HTML',
                                     'reply_markup': json.dumps(BUTTONS, ensure_ascii=False)},
                               files={'photo': ('card.png', img, 'image/png')})
                    j = r.json()
                    if j.get('ok'):
                        return j
                    log('sendPhoto failed, text fallback', j.get('description'))
            except Exception as e:
                log('sendPhoto err', e)
    return send_text(text)


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else 'dryrun'
    if kind not in ('full', 'fullEN', 'check', 'dryrun'):
        log('invalid type: ' + kind)
        sys.exit(2)
    if not TOKEN and kind != 'dryrun':
        log('TG_BOT_TOKEN missing')
        sys.exit(2)
    now = dt.datetime.now(dt.timezone.utc)
    hour = now.astimezone(TEH).hour
    wkind = 'morning' if hour < 12 else 'night'
    if kind == 'dryrun':
        with httpx.Client(timeout=30, headers=UA, follow_redirects=True) as c:
            d = fetch_all(c)
        st = load_state()
        log('FULL_FA:\n' + compose_full(d, wkind, now))
        log('FULL_EN:\n' + compose_fullEN(d, wkind, now))
        snap = st.get('snapshot') or {}
        if snap:
            cm = compose_check(d, snap)
            log('CHECK:\n' + ('\n---\n'.join(cm) if cm else 'nothing crossed'))
        else:
            log('CHECK: no snapshot yet (would seed)')
        log('DRYRUN_OK')
        return
    with httpx.Client(timeout=30, headers=UA, follow_redirects=True) as c:
        d = fetch_all(c, need_dollar=(kind != 'fullEN'))
    st = load_state()
    if kind == 'full':
        send_bulletin(compose_full(d, wkind, now), wkind, d)
    elif kind == 'fullEN':
        send_bulletin(compose_fullEN(d, wkind, now), wkind, d)
    elif kind == 'check':
        snap = st.get('snapshot')
        if not snap:
            st['snapshot'] = snapshot(d)
            st['updated'] = int(time.time())
            save_state(st)
            log('check seeded, nothing sent')
            return
        msgs = compose_check(d, snap)
        for m in msgs:
            send_text(m)
        log('check sent ' + str(len(msgs)))
    st['snapshot'] = snapshot(d)
    st['updated'] = int(time.time())
    save_state(st)
    log(kind + ' done')


if __name__ == '__main__':
    main()