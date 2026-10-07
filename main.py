import os, json, time, asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TG_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
OR_KEY = os.environ.get('OPENROUTER_KEY', '')
CHAT_ID = os.environ['TARGET_CHAT_ID']
IDS = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
       'BNB': 'binancecoin', 'XRP': 'ripple', 'ADA': 'cardano',
       'DOGE': 'dogecoin', 'AVAX': 'avalanche-2', 'LINK': 'chainlink',
       'DOT': 'polkadot', 'ARB': 'arbitrum', 'OP': 'optimism'}

WL_LIMIT = 8
TTL, COOLDOWN, THRESH_24H, THRESH_MOVE = 300, 3600, 5.0, 3.0
NOTIFY_HINT = ('پیام کانال ارسال نشد: ربات باید ادمین کانال باشه و دسترسی '
               'ارسال پیام داشته باشه، یا مقدار TARGET_CHAT_ID درست نیست.')

def load_wl():
    try:
        with open('watchlist.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return ['BTC', 'ETH', 'SOL']

WATCH = load_wl()
CACHE = {'t': 0.0, 'data': {}}
LAST = {}
MUTED = False

def save_wl():
    with open('watchlist.json', 'w') as f:
        json.dump(WATCH, f)

def supported():
    return ', '.join(IDS)

def fmt_wl():
    return ', '.join(WATCH) if WATCH else '(خالی)'

async def get_prices():
    if time.time() - CACHE['t'] < TTL and CACHE['data']:
        return CACHE['data']
    ids = [IDS[s] for s in WATCH if s in IDS]
    if not ids:
        return {}
    async with httpx.AsyncClient(timeout=15) as c:
        for attempt in range(4):
            r = await c.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={'ids': ','.join(ids), 'vs_currencies': 'usd',
                        'include_24hr_change': 'true'})
            if r.status_code == 429:
                await asyncio.sleep(5 * 2 ** attempt)
                continue
            if r.status_code == 200:
                CACHE.update(t=time.time(), data=r.json())
                return CACHE['data']
            await asyncio.sleep(2 ** attempt)
    return CACHE['data']

async def ai_note(sym, px, chg):
    line = f'{sym}: ${px:,.2f} ({chg:+.1f}% 24h)'
    if not OR_KEY:
        return line
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={'Authorization': 'Bearer ' + OR_KEY},
                json={'model': 'meta-llama/llama-3.3-70b-instruct',
                      'messages': [{'role': 'user',
                                    'content': '1 short sentence in Persian + 1 short sentence in English about this move: ' + line}]})
            txt = r.json()['choices'][0]['message']['content'].strip()
            return txt + '\n' + line
    except Exception:
        return line

async def monitor(context: ContextTypes.DEFAULT_TYPE):
    if MUTED:
        return
    data = await get_prices()
    now = time.time()
    for sym in list(WATCH):
        cid = IDS.get(sym)
        if not cid or cid not in data:
            continue
        px = float(data[cid]['usd'])
        chg = float(data[cid].get('usd_24h_change') or 0.0)
        last = LAST.get(sym)
        move = abs(px - last['px']) / last['px'] * 100 if last else 0.0
        cooled = (now - last['t']) > COOLDOWN if last else True
        if cooled and (abs(chg) >= THRESH_24H or move >= THRESH_MOVE):
            await context.bot.send_message(chat_id=CHAT_ID,
                                           text=await ai_note(sym, px, chg))
        LAST[sym] = {'px': px, 't': now}

def arg(msg):
    parts = msg.text.split(maxsplit=1)
    return parts[1].upper().strip() if len(parts) > 1 else ''

async def announce(c, u, text):
    ec = u.effective_chat
    if ec is None or str(ec.id) == str(CHAT_ID):
        return True
    try:
        await c.bot.send_message(chat_id=CHAT_ID, text=text)
        return True
    except Exception:
        return False

async def cmd_start(u, c):
    await u.message.reply_text(
        'سلام! من ربات پایش قیمت تو هستم.\n'
        '\n'
        'چطور کار می‌کنم؟\n'
        f'هر ۱۰ دقیقه واچ‌لیستت رو چک می‌کنم و فقط وقتی خبر مهمی باشه '
        f'(تغییر ۲۴ ساعته {THRESH_24H:.0f}٪ به بالا، یا جابه‌جایی {THRESH_MOVE:.0f}٪ نسبت به آخرین قیمت) '
        'اعلان می‌دم؛ بقیه وقت‌ها ساکتم.\n'
        '\n'
        f'واچ‌لیست فعلی ({len(WATCH)}/{WL_LIMIT}): {fmt_wl()}\n'
        '\n'
        'دستورات:\n'
        '/price BTC — قیمت لحظه‌ای\n'
        '/watchlist — نمای کلی قیمت‌ها\n'
        '/add DOGE — اضافه کردن (حداکثر ۸ نماد)\n'
        '/remove DOGE — حذف از واچ‌لیست\n'
        '/mute — توقف یا ادامه اعلان‌ها\n'
        '/help — راهنمای کامل')

async def cmd_price(u, c):
    sym = arg(u.message)
    if not sym:
        return await u.message.reply_text(
            'فرمت درست:\n/price BTC\n\n'
            f'نمادهای موجود:\n{supported()}')
    if sym not in IDS:
        return await u.message.reply_text(
            f'نماد «{sym}» پشتیبانی نمی‌شه.\n\n'
            f'نمادهای موجود:\n{supported()}')
    d = (await get_prices()).get(IDS[sym])
    if not d:
        return await u.message.reply_text(
            'هنوز داده‌ای ندارم؛ یک دقیقه دیگه دوباره بزن.')
    usd = d['usd']
    ch = d.get('usd_24h_change') or 0
    await u.message.reply_text(f'{sym}: ${usd:,.2f} ({ch:+.1f}% 24h)')

async def cmd_watch(u, c):
    if not WATCH:
        return await u.message.reply_text(
            'واچ‌لیست خالیه. با /add BTC شروع کن.')
    data = await get_prices()
    lines = []
    for s in WATCH:
        d = data.get(IDS.get(s, ''), {})
        if d:
            usd = d['usd']
            ch = d.get('usd_24h_change') or 0
            lines.append(f'{s}: ${usd:,.2f} ({ch:+.1f}%)')
    await u.message.reply_text(
        '\n'.join(lines) or 'هنوز داده‌ای ندارم؛ یک دقیقه دیگه دوباره بزن.')

async def cmd_add(u, c):
    sym = arg(u.message)
    if not sym:
        return await u.message.reply_text(
            'فرمت درست:\n/add DOGE\n\n'
            f'نمادهای موجود:\n{supported()}\n\n'
            f'واچ‌لیست فعلی ({len(WATCH)}/{WL_LIMIT}): {fmt_wl()}')
    if sym not in IDS:
        return await u.message.reply_text(
            f'نماد «{sym}» پشتیبانی نمی‌شه.\n\n'
            f'نمادهای موجود:\n{supported()}')
    if sym in WATCH:
        return await u.message.reply_text(
            f'{sym} همین الان توی واچ‌لیسته.\nواچ‌لیست: {fmt_wl()}')
    if len(WATCH) >= WL_LIMIT:
        return await u.message.reply_text(
            f'سقف {WL_LIMIT} توکن پره. اول یکی رو /remove کن.\n'
            f'واچ‌لیست: {fmt_wl()}')
    WATCH.append(sym)
    save_wl()
    CACHE['t'] = 0
    await u.message.reply_text(
        f'اضافه شد: {sym}\nواچ‌لیست: {fmt_wl()}')
    ok = await announce(c, u, f'واچ‌لیست بروزرسانی شد — «{sym}» اضافه شد.\nحالا: {fmt_wl()}')
    if not ok:
        await u.message.reply_text(NOTIFY_HINT)

async def cmd_remove(u, c):
    sym = arg(u.message)
    if not sym:
        return await u.message.reply_text(
            'فرمت درست:\n/remove DOGE\n\n'
            f'واچ‌لیست فعلی: {fmt_wl()}')
    if sym not in WATCH:
        return await u.message.reply_text(
            f'نماد «{sym}» توی واچ‌لیست نیست.\nواچ‌لیست: {fmt_wl()}')
    WATCH.remove(sym)
    save_wl()
    await u.message.reply_text(
        f'حذف شد: {sym}\nواچ‌لیست: {fmt_wl()}')
    ok = await announce(c, u, f'واچ‌لیست بروزرسانی شد — «{sym}» حذف شد.\nحالا: {fmt_wl()}')
    if not ok:
        await u.message.reply_text(NOTIFY_HINT)

async def cmd_mute(u, c):
    global MUTED
    MUTED = not MUTED
    if MUTED:
        await u.message.reply_text('اعلان‌ها متوقف شد. برای ادامه دوباره /mute بزن.')
    else:
        await u.message.reply_text('اعلان‌ها روشن شد. برای توقف دوباره /mute بزن.')

async def cmd_help(u, c):
    await u.message.reply_text(
        'راهنما:\n'
        '/price BTC — قیمت لحظه‌ای یک نماد\n'
        '/watchlist — قیمت همه واچ‌لیست\n'
        '/add DOGE — اضافه کردن به واچ‌لیست\n'
        '/remove DOGE — حذف از واچ‌لیست\n'
        '/mute — توقف یا ادامه اعلان‌ها\n'
        '\n'
        'اعلان خودکار:\n'
        f'ربات هر ۱۰ دقیقه قیمت‌ها رو چک می‌کنه و وقتی تغییر ۲۴ ساعته {THRESH_24H:.0f}٪ به بالا '
        f'یا جابه‌جایی {THRESH_MOVE:.0f}٪ نسبت به آخرین قیمت باشه، پست جدید می‌زنه.\n'
        '\n'
        f'سقف واچ‌لیست: {WL_LIMIT} نماد\n'
        f'نمادهای موجود:\n{supported()}')

app = Application.builder().token(TG_TOKEN).build()
app.add_handler(CommandHandler('start', cmd_start))
app.add_handler(CommandHandler('price', cmd_price))
app.add_handler(CommandHandler('watchlist', cmd_watch))
app.add_handler(CommandHandler('add', cmd_add))
app.add_handler(CommandHandler('remove', cmd_remove))
app.add_handler(CommandHandler('mute', cmd_mute))
app.add_handler(CommandHandler('help', cmd_help))
app.job_queue.run_repeating(monitor, interval=600, first=10, name='monitor')
app.run_polling()