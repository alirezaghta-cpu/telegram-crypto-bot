# Telegram Crypto Bot — Alien Market Bot v2

> Fully automated bilingual (Persian + English) Telegram market bulletin bot.
> Built end-to-end from zero to production as a completed project + public tutorial.
> THIS REPOSITORY IS PUBLIC DOCUMENTATION. No real credentials are (or ever should be) included.

## 1. What it does

Four routine posts per day, fully automatic, never cancelled:

| Post | Language | UTC | Tehran |
|---|---|---|---|
| Morning bulletin | Persian | 04:00 | 07:30 |
| Morning bulletin | English | 04:00 | 07:30 |
| Price check + alerts | Persian | 05/09/14/21 | 08:30/12:30/17:30/00:30 |
| Evening bulletin | Persian | 19:00 | 22:30 |
| Evening bulletin | English | 19:00 | 22:30 |

Golden rule: late is acceptable, cancelled is not. Any threat to the routine is reported to the steward immediately. After every scheduler cycle, the cadence is re-anchored to the next event + ~2 minutes; absolute priority is the 19:00 UTC evening bulletin.

### Post contract (final)
- 4 fully distinct images per cycle; each post carries its own image(s) related to that post's news only.
- Persian numerals + Jalali/Tehran dates in Persian posts; UTC in English posts.
- Rial prices for USD, gold, silver, oil. Crypto stays USD-only.
- Hashtags: relevant to that post's news, never repeated between posts, different every time.
- If news is missing, the routine post still goes out.
- After any change: one Persian + one English test post to the channel immediately.

## 2. Architecture

- `bot.py` — python-telegram-bot v21 entrypoint, polling + job queue
- `core.py` — config, state, i18n, Jalali date, GitHub state sync
- `data.py` — async httpx fetchers: CoinGecko, tgju.org, Yahoo Finance, alternative.me
- `monitor.py` — 10-minute pump/threshold alert scanner
- `handlers.py` — commands: /start /price /fng /watchlist /add /remove /settings /ref /lang /help
- `screens_a.py` / `screens_b.py` — inline keyboard screens
- `strings_fa.py` / `strings_en.py` — bilingual UI
- `game.py` — daily check-in
- `state/*.json` — runtime state pushed back to repo

### Data sources (verified)
- USD/Toman, gold ounce, silver: tgju.org JSON with cache-buster (nc=<timestamp>)
- BTC/ETH: CoinGecko simple price; charts: Binance klines
- Fear & Greed: alternative.me/fng
- Oil and other commodities: Yahoo Finance chart API
- Persian news: BBC Persian and reputable wires
- Charts: QuickChart — ALWAYS `POST /chart/create` for a short URL (long percent-encoded URLs break Telegram downloads)
- Rial conversion: non-crypto assets x live free-market USD rate

## 3. Run it yourself (placeholders only)

1. Create a bot via @BotFather -> TELEGRAM_BOT_TOKEN
2. Create a channel, add bot as admin with posting rights -> CHAT_ID
3. Fork this repo; never commit secrets
4. Create a fine-grained PAT scoped to this repo only
5. Put TELEGRAM_BOT_TOKEN, CHAT_ID, GITHUB_TOKEN, GITHUB_REPOSITORY in env vars (Railway/Actions secrets)
6. `pip install -r requirements.txt && python bot.py`
7. Verify: `/price BTC ETH`, then `/start` in the channel

## 4. Bugs hit and fixes (lessons log)

1. Telegram album InputMedia field must be `media`, not `photo` -> HTTP 400 otherwise. Fixed.
2. Long QuickChart URLs break Telegram media download -> POST /chart/create, use the short render URL.
3. Thousands separators inside floats (4,120.45) broke parsing/display -> strip separators before float().
4. Base64 round-tripped through an LLM corrupts files (single-character drift) -> push plain-text blobs only.
5. Raw git references (/dev/null) were skipped by tooling but still needed updates -> normalize references.
6. First bulletin was late (07:21 vs 04:00) because the scheduler was not re-anchored -> after every cycle, set cadence to next event + ~2 min.
7. gold-api.com price paths (e.g. /price/XAG) return 404 -> dead endpoint; silver comes from tgju. Fail over, don't retry dead endpoints.

## 5. Security rules (non-negotiable)

1. Never put bot tokens, PATs, Railway tokens or private channel ids in code, repo, public docs or chat.
2. Public docs are setup tutorials with placeholder credentials only.
3. Credentials exposed in chat must be rotated; store only in secure env vars.
4. Strong DB password in env only; bot token never in a repo file.
5. The deployed repo/branch that Railway pulls from must never be deleted.

## 6. Operations notes

- Production runs on Railway (service: telegram-bot from this repo, main branch). Trial plan — upgrade or replace before lapse.
- Duplicate Railway project with deleted deploy: leave untouched.
- state/*.json is committed back so action-based runs keep user lists/referrals.
- Routine posts are triggered by the operator scheduler with per-event cadence anchoring.

## 7. Roadmap (owner-approved)

- Anomaly-alert layer: jump > X% or key-level break -> a smarter newspaper.
- Next project: trading bot (starts after this repo is frozen + documented).
- Referral program: paused, coming soon.
- Daily game reduced to daily check-in.
- Watchlist categories: currency / commodities-metals / crypto.

---

Built by kapa (mind, @hellominds) with steward dlux5404. Frozen as completed project, tutorial and resume. Next: the trading bot.
