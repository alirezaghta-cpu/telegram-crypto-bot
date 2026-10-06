import os, json, time, asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OR_KEY = os.environ.get("OPENROUTER_KEY", "")
CHAT_ID = os.environ["TARGET_CHAT_ID"]
IDS = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
       "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
       "DOGE": "dogecoin", "AVAX": "avalanche-2", "LINK": "chainlink",
       "DOT": "polkadot", "ARB": "arbitrum", "OP": "optimism"}

def load_wl():
    try:
        with open("watchlist.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return ["BTC", "ETH", "SOL"]

WATCH = load_wl()                 # max 8 symbols
CACHE = {"t": 0.0, "data": {}}
LAST = {}                         # sym -> {"px": float, "t": float}
MUTED = False
TTL, COOLDOWN, THRESH_24H, THRESH_MOVE = 300, 3600, 5.0, 3.0

def save_wl():
    with open("watchlist.json", "w") as f:
        json.dump(WATCH, f)

async def get_prices():
    if time.time() - CACHE["t"] < TTL and CACHE["data"]:
        return CACHE["data"]
    ids = [IDS[s] for s in WATCH if s in IDS]
    if not ids:
        return {}
    async with httpx.AsyncClient(timeout=15) as c:
        for attempt in range(4):
            r = await c.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "usd",
                        "include_24hr_change": "true"})
            if r.status_code == 429:                       # rate limited
                await asyncio.sleep(5 * 2 ** attempt)       # exponential backoff
                continue
            if r.status_code == 200:
                CACHE.update(t=time.time(), data=r.json())
                return CACHE["data"]
            await asyncio.sleep(2 ** attempt)
    return CACHE["data"]

async def ai_note(sym, px, chg):
    line = f"{sym}: ${px:,.2f} ({chg:+.1f}% 24h)"
    if not OR_KEY:
        return line
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}"},
                json={"model": "meta-llama/llama-3.3-70b-instruct",
                      "messages": [{"role": "user",
                                    "content": "1 short sentence in Persian + 1 short sentence in English about this move: " + line}]},
            )
            txt = r.json()["choices"][0]["message"]["content"].strip()
            return txt + "\n" + line
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
        px = float(data[cid]["usd"])
        chg = float(data[cid].get("usd_24h_change") or 0.0)
        last = LAST.get(sym)
        move = abs(px - last["px"]) / last["px"] * 100 if last else 0.0
        cooled = (now - last["t"]) > COOLDOWN if last else True
        if cooled and (abs(chg) >= THRESH_24H or move >= THRESH_MOVE):
            await context.bot.send_message(chat_id=CHAT_ID,
                                           text=await ai_note(sym, px, chg))
        LAST[sym] = {"px": px, "t": now}

def arg(msg):
    parts = msg.text.split(maxsplit=1)
    return parts[1].upper().strip() if len(parts) > 1 else ""

async def cmd_start(u, c):
    await u.message.reply_text(
        f"Watchlist: {', '.join(WATCH)}\nCommands: /price /watchlist /add /remove /mute /help")

async def cmd_price(u, c):
    sym = arg(u.message)
    if sym not in IDS:
        return await u.message.reply_text("Unknown token. Supported: " + ", ".join(IDS))
    d = (await get_prices()).get(IDS[sym])
    if not d:
        return await u.message.reply_text("No data yet, try again in a minute.")
    await u.message.reply_text(
        f"{sym}: ${d['usd']:,.2f} ({(d.get('usd_24h_change') or 0):+.1f}% 24h)")

async def cmd_watch(u, c):
    data = await get_prices()
    lines = []
    for s in WATCH:
        d = data.get(IDS.get(s, ""), {})
        if d:
            lines.append(f"{s}: ${d['usd']:,.2f} ({(d.get('usd_24h_change') or 0):+.1f}%)")
    await u.message.reply_text("\n".join(lines) or "No data yet.")

async def cmd_add(u, c):
    sym = arg(u.message)
    if sym not in IDS:
        return await u.message.reply_text("Supported: " + ", ".join(IDS))
    if len(WATCH) >= 8:
        return await u.message.reply_text("Limit is 8 tokens to stay free. /remove one first.")
    if sym not in WATCH:
        WATCH.append(sym)
        save_wl()
        CACHE["t"] = 0                                  # force refresh
    await u.message.reply_text(f"Added: {sym} | Watchlist: {', '.join(WATCH)}")

async def cmd_remove(u, c):
    sym = arg(u.message)
    if sym in WATCH:
        WATCH.remove(sym)
        save_wl()
    await u.message.reply_text(f"Removed: {sym} | Watchlist: {', '.join(WATCH)}")

async def cmd_mute(u, c):
    global MUTED
    MUTED = not MUTED
    await u.message.reply_text("Alerts " + ("paused" if MUTED else "on"))

async def cmd_help(u, c):
    await u.message.reply_text(
        "/price BTC - live price\n/watchlist - overview\n"
        "/add DOGE or /remove DOGE (max 8)\n/mute - pause alerts\n/help")

app = Application.builder().token(TG_TOKEN).build()
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CommandHandler("price", cmd_price))
app.add_handler(CommandHandler("watchlist", cmd_watch))
app.add_handler(CommandHandler("add", cmd_add))
app.add_handler(CommandHandler("remove", cmd_remove))
app.add_handler(CommandHandler("mute", cmd_mute))
app.add_handler(CommandHandler("help", cmd_help))
app.job_queue.run_repeating(monitor, interval=600, first=10, name="monitor")
app.run_polling()
