# 🛸 Alien Market Bot v2

ربات بازار تلگرام — دوزبانه (فارسی/English)، منوی دکمه‌ای شیشه‌ای، هشدارهای هوشمند و شاخص ترس و طمع. کاملاً رایگان.

## امکانات

- 🎬 انتخاب زبان هنگام استارت — تایم پیام‌های انگلیسی UTC (جهانی)
- 📊 قیمت‌های لحظه‌ای: دلار آزاد، انس طلا و نقره، بیت‌کوین، اتریوم و ۱۴ رمزارز (دکمه 🔄 بروزرسانی)
- 🔔 هشدار خودکار برای هر کاربر: تغییر ۲۴ ساعته ≥۵٪ یا جابه‌جایی ≥۳٪ نسبت به آخرین هشدار (بررسی هر ۱۰ دقیقه، با cooldown ۴ ساعته، دکمه 🔇 خاموش/روشن)
- 😨 شاخص ترس و طمع
- 📣 دعوت دوستان (رفرال/زیرمجموعه‌گیری): فعلاً غیرفعال — دکمه «به‌زودی»؛ در آینده با ایده بهتر و جذاب‌تر برمی‌گردد
- 📱 منوی دکمه‌ای کامل + فهرست دستورات: /start /price /fng /watchlist /add /remove /settings /ref /lang /help

## ساختار کد

`bot.py` (ورودی) شامل ۹ ماژول: `core`, `strings_fa`, `strings_en`, `ui`, `data`, `screens_a`, `screens_b`, `handlers`, `monitor`. حالت کاربران/لیست‌ها در `state/` ذخیره و به ریپو کامیت می‌شود.

## راه‌اندازی رایگان (GitHub Actions)

1. ریپو را **Public** کنید تا دقایق Actions نامحدود و رایگان باشد:
   Settings → Danger Zone → Change repository visibility → Public
2. Settings → Secrets and variables → Actions → New repository secret:
   - `TELEGRAM_BOT_TOKEN` (الزامی) — توکن ربات از BotFather
   - `CHAT_ID` (اختیاری) — آیدی عددی چنل برای هشدارهای قدیمی
3. فایل `.github/workflows/bot.yml` هر ۵ دقیقه ربات را اجرا می‌کند (concurrency: تداخل ندارد).
4. اجرای دستی: Actions → bot-poller → Run workflow

## اجرای محلی

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=123:abc
python bot.py
```

## نکته امنیتی

توکن ربات فقط در Secrets نگه داشته شود؛ هرگز در کد کامیت نشود.
