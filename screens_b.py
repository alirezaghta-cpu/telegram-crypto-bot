'''Screens B: add-symbol prompt, settings, referral, help, language.'''
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core import (T, lang_of, wl_limit, is_vip, ref_count,
                   STATE, ensure_user, save)
from ui import out, back_kb, share_url, lang_kb
import core


async def ask_add(u, edit=False):
    uid = u.effective_user.id
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')],
    ])
    await out(u, T(uid, 'add_ask', syms=', '.join(core.IDS)), kb, edit)


async def show_settings(u, edit=False):
    uid = u.effective_user.id
    muted = STATE['users'].get(str(uid), {}).get('muted', False)
    state = T(uid, 'off') if muted else T(uid, 'on')
    level = T(uid, 'vip') if is_vip(uid) else T(uid, 'std')
    mute_label = T(uid, 'btn_unmute') if muted else T(uid, 'btn_mute')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(mute_label, callback_data='mute')],
        [InlineKeyboardButton(T(uid, 'btn_ref'), callback_data='ref'),
         InlineKeyboardButton(T(uid, 'btn_lang'), callback_data='langpick')],
        [InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')],
    ])
    await out(u, T(uid, 'set_head', state=state, level=level), kb, edit)


async def show_ref(u, edit=False):
    # رفرال/زیرمجموعه‌گیری فعلاً لغو شد — فقط پیام «به‌زودی» نمایش داده می‌شود.
    uid = u.effective_user.id
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')],
    ])
    await out(u, T(uid, 'ref_soon'), kb, edit)


async def show_help(u, edit=False):
    uid = u.effective_user.id
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T(uid, 'btn_channel'),
                              url='https://t.me/GalaxiesDrop')],
        [InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')],
    ])
    await out(u, T(uid, 'help_head'), kb, edit)


async def show_langpick(u, edit=False):
    uid = u.effective_user.id
    name = STATE['users'].get(str(uid), {}).get('name', '')
    text = T(uid, 'pick', name=name)
    kb = lang_kb()
    if u.callback_query:
        try:
            await u.callback_query.edit_message_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await u.effective_message.reply_text(text, reply_markup=kb)


async def toggle_mute(u, edit=False):
    uid = u.effective_user.id
    us = ensure_user(uid)
    us['muted'] = not us.get('muted', False)
    save('users')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T(uid, 'btn_back'), callback_data='settings')],
    ])
    await out(u, T(uid, 'mute_on' if us['muted'] else 'mute_off'), kb, edit)
