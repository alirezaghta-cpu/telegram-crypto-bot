'''Command, callback-query and plain-text handlers.'''
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core import (T, STATE, IDS, EXTRA, ensure_user, lang_set, save, wl_limit)
from ui import menu_kb, lang_kb, out
from screens_a import show_menu, show_prices, show_fng, show_list
from screens_b import (ask_add, show_cat, add_symbol, show_settings,
                       show_ref, show_help, show_langpick, toggle_mute)
from game import show_game, game_action


async def on_start(u, c):
    uid = u.effective_user.id
    us = ensure_user(uid, u.effective_user.full_name or '')
    # بخش رفرال/زیرمجموعه‌گیری فعلاً لغو شد — به‌زودی با ایده بهتر برمی‌گردد.
    if not lang_set(uid):
        await u.effective_message.reply_text(
            T(uid, 'pick', name=us.get('name', '')), reply_markup=lang_kb())
        return
    await u.effective_message.reply_text(
        T(uid, 'welcome') + '\n\n' + T(uid, 'menu'),
        parse_mode='HTML', reply_markup=menu_kb(uid))


async def on_cb(u, c):
    q = u.callback_query
    if not q:
        return
    await q.answer()
    data = q.data or ''
    uid = u.effective_user.id
    if data.startswith('lang:'):
        us = ensure_user(uid, u.effective_user.full_name or '')
        us['lang'] = data[5:]
        save('users')
        bonus = c.user_data.pop('bonus', '')
        await out(u, T(uid, 'lang_ok') + '\n\n' + T(uid, 'menu') + bonus,
                  menu_kb(uid), edit=True)
        return
    if data.startswith('del:'):
        s = data[4:]
        lst = STATE['lists'].get(str(uid), [])
        if s in lst:
            lst.remove(s)
            save('lists')
        await show_list(u, edit=True)
        return
    if data.startswith('cat:'):
        await show_cat(u, data[4:], edit=True)
        return
    if data.startswith('as:'):
        await add_symbol(u, data[3:], edit=True)
        return
    if data.startswith('game:'):
        await game_action(u, data, edit=True)
        return
    if data == 'add':
        c.user_data['wait'] = 'add'
        await ask_add(u, edit=True)
        return
    routes = {'menu': show_menu, 'prices': show_prices, 'fng': show_fng,
              'list': show_list, 'settings': show_settings, 'ref': show_ref,
              'help': show_help, 'langpick': show_langpick,
              'mute': toggle_mute, 'game': show_game}
    fn = routes.get(data)
    if fn:
        await fn(u, edit=True)
    else:
        await show_menu(u, edit=True)


async def on_text(u, c):
    uid = u.effective_user.id
    us = ensure_user(uid, u.effective_user.full_name or '')
    if not lang_set(uid):
        await u.effective_message.reply_text(
            T(uid, 'pick', name=us.get('name', '')), reply_markup=lang_kb())
        return
    if c.user_data.get('wait') == 'add':
        c.user_data['wait'] = None
        await add_symbol(u, u.effective_message.text or '')
        return
    await u.effective_message.reply_text(
        T(uid, 'hint'), reply_markup=menu_kb(uid))


async def on_help(u, c):
    await show_help(u)


async def on_cmd_prices(u, c):
    await show_prices(u)


async def on_cmd_fng(u, c):
    await show_fng(u)


async def on_cmd_list(u, c):
    await show_list(u)


async def on_cmd_add(u, c):
    c.user_data['wait'] = 'add'
    await ask_add(u)


async def on_cmd_remove(u, c):
    uid = u.effective_user.id
    lst = STATE['lists'].get(str(uid), [])
    if c.args and c.args[0].upper() in lst:
        s = c.args[0].upper()
        lst.remove(s)
        save('lists')
        await u.effective_message.reply_text(
            T(uid, 'del_ok', s=s), reply_markup=menu_kb(uid))
        return
    await show_list(u)


async def on_cmd_settings(u, c):
    await show_settings(u)


async def on_cmd_ref(u, c):
    await show_ref(u)


async def on_cmd_lang(u, c):
    await show_langpick(u)
