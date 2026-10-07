# telegram-crypto-bot — Alienpanelsbot v2

Bilingual (فارسی / English) interactive Telegram market bot plus fully automated
bilingual bulletins for the @GalaxiesDrop channel. Runs free on GitHub Actions.

## Automation
- `bulletins.yml` — 04:00 UTC Persian + English morning pair, 19:00 UTC night
  pair, threshold checks at 05/09/14/21 UTC. Photo card generated at runtime
  (Pillow), bulletin text as caption, inline buttons. Snapshot in
  `bulletin_state.json`, committed back after each run.
- `bot.yml` — polls Telegram every 5 minutes (RUN_ONCE mode): inline glass
  menus, language select, personal watchlist + price alerts, referral rewards,
  channel watchlist alerts. Persists `users.json`, `bot_state.json`,
  `watchlist.json` back to the repo.

## Secrets (Settings - Secrets and variables - Actions)
- `TG_BOT_TOKEN` — Alienpanelsbot token
- `TG_CHAT_ID` — channel id (-1001686062564)

## Files
- `main.py` + `core.py` + `menus.py` + `strings.py` — interactive bot v2
- `bulletin.py` — scheduled bulletin engine (full / fullEN / check / dryrun)
- `watchlist.json` — channel-level alert list (edit via repo or /chadd)
- `users.json`, `bot_state.json` — machine-managed bot state

## Local run
    pip install -r requirements.txt
    TG_BOT_TOKEN=... python main.py
    TG_BOT_TOKEN=... python bulletin.py dryrun

## Notes
- Referral deep link: https://t.me/Alienpanelsbot?start=ref<userid> — both
  sides get 7 days VIP (sharp alerts + watchlist up to 50).
- Keep the repo PUBLIC so free Actions minutes stay unlimited ($0). No
  secrets live in code — only in Actions secrets.
