'''Daily check-in game: settle yesterday's BTC pick, then make today's pick.'''
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core import lang_of, STATE, save
from data import fetch_prices
from ui import out

DAY = 86400
WIN = 10
STREAK_BONUS = 5

TXT = {
    'fa': {
        'head': '🎲 <b>چک روزانه بازار</b>\n\n🎯 هر روز یک‌بار بیا، نتیجه دیروز رو ثبت کن و جهت بیت‌کوین رو برای امروز حدس بزن — اگه درست بگی <b>+۱۰ امتیاز</b> و با هر برد پیاپی پاداش بیشتر!\n\n💰 قیمت الان BTC: <b>{px}</b> دلار\n🏆 امتیاز شما: <b>{pts}</b> | 🔥 پیاپی: {streak}\n\n⚙️ فقط امتیاز بازیه، خبری از پول واقعی نیست.',
        'picked': '✅ حدس امروز ثبت شد: <b>{pick}</b>\n⏳ فردا برگرد تا نتیجه مشخص بشه (شروع: <b>{px}</b> دلار).\n🏆 امتیاز شما: <b>{pts}</b>',
        'wait': '⏳ حدس دیروز ({pick}) هنوز بازه — فردا که بیای نتیجه ثبت می‌شه (شروع: <b>{px}</b> دلار).',
        'win': '✅ درست حدس زدی! <b>+{gain}</b> امتیاز 🎉\nBTC: {a} ➡️ {b} دلار',
        'lose': '❌ این دفعه نشد. حدست <b>{pick}</b> بود ولی BTC: {a} ➡️ {b} دلار.',
        'flat': '➖ تقریباً بدون تغییر — امتیازی کم نشد.',
        'board': '🏆 <b>جدول امتیازها</b>\n\n{rows}',
        'board_empty': 'هنوز کسی بازی نکرده — اولین نفر باش! 🚀',
        'up': '📈 بالا',
        'down': '📉 پایین',
        'btn_board': '🏆 جدول امتیازها',
        'btn_back': '🔙 منو',
        'no_px': '⚠️ قیمت BTC الان در دسترس نیست — چند لحظه دیگه دوباره بزن.',
    },
    'en': {
        'head': '🎲 <b>Daily market check-in</b>\n\n🎯 Come back once a day: yesterday\'s result settles, then pick where bitcoin goes today — get it right and earn <b>+10 points</b>, with a bonus for every consecutive win!\n\n💰 BTC now: <b>{px}</b> USD\n🏆 Your points: <b>{pts}</b> | 🔥 Streak: {streak}\n\n⚙️ Points only — no real money involved.',
        'picked': '✅ Today\'s pick locked: <b>{pick}</b>\n⏳ Come back tomorrow for the result (start: <b>{px}</b> USD).\n🏆 Your points: <b>{pts}</b>',
        'wait': '⏳ Yesterday\'s pick ({pick}) is still open — it settles when you return tomorrow (start: <b>{px}</b> USD).',
        'win': '✅ Correct! <b>+{gain}</b> points 🎉\nBTC: {a} ➡️ {b} USD',
        'lose': '❌ Not this time. You picked <b>{pick}</b> but BTC: {a} ➡️ {b} USD.',
        'flat': '➖ Almost flat — no points lost.',
        'board': '🏆 <b>Leaderboard</b>\n\n{rows}',
        'board_empty': 'Nobody has played yet — be the first! 🚀',
        'up': '📈 Up',
        'down': '📉 Down',
        'btn_board': '🏆 Leaderboard',
        'btn_back': '🔙 Menu',
        'no_px': '⚠️ BTC price unavailable right now — try again in a moment.',
    },
}


def _kb(uid, waiting=False):
    t = TXT[lang_of(uid)]
    rows = []
    if not waiting:
        rows.append([InlineKeyboardButton(t['up'], callback_data='game:up'),
                     InlineKeyboardButton(t['down'], callback_data='game:down')])
    rows.append([InlineKeyboardButton(t['btn_board'],
                                      callback_data='game:board')])
    rows.append([InlineKeyboardButton(t['btn_back'], callback_data='menu')])
    return InlineKeyboardMarkup(rows)


def _settle(uid, t, px, now):
    '''Settle a pick from a previous day; returns (result_text, record).'''
    g = STATE.setdefault('game', {})
    rec = g.get(str(uid), {})
    if not rec.get('ts') or now - rec['ts'] < DAY:
        return '', rec
    base = rec.get('btc') or 0
    pick = rec.get('pick') or 'up'
    result = ''
    if base and abs(px - base) / base > 0.0005:
        won = (pick == 'up' and px > base) or (pick == 'down' and px < base)
        if won:
            streak = rec.get('streak', 0) + 1
            gain = WIN + STREAK_BONUS * (streak - 1)
            rec['streak'] = streak
            rec['pts'] = rec.get('pts', 0) + gain
            rec['won'] = rec.get('won', 0) + 1
            result = t['win'].format(gain=gain, a=f"{base:,.0f}",
                                     b=f"{px:,.0f}")
        else:
            rec['streak'] = 0
            result = t['lose'].format(
                pick=t['up'] if pick == 'up' else t['down'],
                a=f"{base:,.0f}", b=f"{px:,.0f}")
    else:
        result = t['flat']
    rec['played'] = rec.get('played', 0) + 1
    rec.pop('ts', None)
    rec.pop('pick', None)
    rec.pop('btc', None)
    g[str(uid)] = rec
    save('game')
    return result, rec


async def show_game(u, edit=False):
    uid = u.effective_user.id
    t = TXT[lang_of(uid)]
    prices = await fetch_prices()
    px = (prices.get('bitcoin') or {}).get('usd') or 0
    rec = STATE.setdefault('game', {}).get(str(uid), {})
    result = ''
    if px:
        result, rec = _settle(uid, t, px, time.time())
    body = t['head'].format(px=f"{px:,.0f}" if px else '—',
                            pts=rec.get('pts', 0), streak=rec.get('streak', 0))
    if result:
        body = result + '\n\n' + body
    if rec.get('ts'):
        pick = t['up'] if rec.get('pick') == 'up' else t['down']
        body += '\n\n' + t['wait'].format(
            pick=pick, px=f"{rec.get('btc') or 0:,.0f}")
    await out(u, body, _kb(uid, waiting=bool(rec.get('ts'))), edit)


async def game_action(u, data, edit=True):
    uid = u.effective_user.id
    t = TXT[lang_of(uid)]
    act = data.split(':', 1)[1] if ':' in data else 'show'
    g = STATE.setdefault('game', {})
    rec = g.get(str(uid), {})
    if act == 'board':
        top = sorted(g.items(),
                     key=lambda kv: (kv[1] or {}).get('pts', 0),
                     reverse=True)[:5]
        rows = []
        for i, (k, r) in enumerate(top, 1):
            name = (STATE.get('users', {}).get(k, {}) or {}).get('name') or k
            rows.append(f"{i}. {str(name)[:18]} — {r.get('pts', 0)} "
                        f"✅{r.get('won', 0)}")
        text = (t['board'].format(rows='\n'.join(rows)) if rows
                else t['board_empty'])
        await out(u, text, _kb(uid), edit)
        return
    if act in ('up', 'down'):
        if rec.get('ts') and time.time() - rec['ts'] < DAY:
            pick = t['up'] if rec.get('pick') == 'up' else t['down']
            await out(u, t['wait'].format(
                          pick=pick, px=f"{rec.get('btc') or 0:,.0f}"),
                      _kb(uid, waiting=True), edit)
            return
        prices = await fetch_prices()
        px = (prices.get('bitcoin') or {}).get('usd') or 0
        if not px:
            await out(u, t['no_px'], _kb(uid), edit)
            return
        result, rec = _settle(uid, t, px, time.time())
        rec.update(ts=time.time(), btc=px, pick=act)
        g[str(uid)] = rec
        save('game')
        pick = t['up'] if act == 'up' else t['down']
        text = t['picked'].format(pick=pick, px=f"{px:,.0f}",
                                  pts=rec.get('pts', 0))
        if result:
            text = result + '\n\n' + text
        await out(u, text, _kb(uid, waiting=True), edit)
        return
    await show_game(u, edit=edit)