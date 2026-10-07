'''Entry point: wiring, startup and polling for Alien Market Bot v2.'''
from telegram import BotCommand, Update
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters)

import core
from core import load_all, TOKEN, log
from monitor import monitor
from handlers import (on_start, on_help, on_cb, on_text, on_cmd_prices,
                      on_cmd_fng, on_cmd_list, on_cmd_add, on_cmd_remove,
                      on_cmd_settings, on_cmd_ref, on_cmd_lang)


async def post_init(app):
    me = await app.bot.get_me()
    core.BOT_UNAME = me.username
    cmds = [('start', 'شروع / Start'), ('price', 'قیمت‌ها / Prices'),
            ('fng', 'ترس و طمع / Fear-Greed'),
            ('watchlist', 'لیست من / My list'),
            ('add', 'افزودن / Add symbol'), ('remove', 'حذف / Remove'),
            ('settings', 'تنظیمات / Settings'), ('ref', 'دعوت / Invite'),
            ('lang', 'زبان / Language'), ('help', 'راهنما / Help')]
    await app.bot.set_my_commands([BotCommand(k, v) for k, v in cmds])
    log.info('bot ready as @%s', me.username)


def main():
    load_all()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', on_start))
    app.add_handler(CommandHandler('help', on_help))
    app.add_handler(CommandHandler(['price', 'prices'], on_cmd_prices))
    app.add_handler(CommandHandler('fng', on_cmd_fng))
    app.add_handler(CommandHandler(['watchlist', 'list'], on_cmd_list))
    app.add_handler(CommandHandler('add', on_cmd_add))
    app.add_handler(CommandHandler(['remove', 'rm'], on_cmd_remove))
    app.add_handler(CommandHandler('settings', on_cmd_settings))
    app.add_handler(CommandHandler(['ref', 'invite'], on_cmd_ref))
    app.add_handler(CommandHandler('lang', on_cmd_lang))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    if app.job_queue:
        app.job_queue.run_repeating(monitor, interval=600, first=15,
                                    name='monitor')
    log.info('polling started')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
