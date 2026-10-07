'''Keyboards, share links and message helpers.'''
from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core import T, lang_of


def menu_kb(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T(uid, 'btn_prices'), callback_data='prices'),
         InlineKeyboardButton(T(uid, 'btn_fng'), callback_data='fng')],
        [InlineKeyboardButton(T(uid, 'btn_list'), callback_data='list'),
         InlineKeyboardButton(T(uid, 'btn_add'), callback_data='add')],
        [InlineKeyboardButton(T(uid, 'btn_set'), callback_data='settings'),
         InlineKeyboardButton(T(uid, 'btn_ref'), callback_data='ref')],
        [InlineKeyboardButton(T(uid, 'btn_help'), callback_data='help'),
         InlineKeyboardButton(T(uid, 'btn_lang'), callback_data='langpick')],
        [InlineKeyboardButton('🎲 بازی روز' if lang_of(uid) == 'fa'
                              else '🎲 Daily game', callback_data='game')],
    ])


def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🇮🇷 فارسی', callback_data='lang:fa'),
         InlineKeyboardButton('🇬🇧 English', callback_data='lang:en')],
    ])


def back_kb(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T(uid, 'btn_refresh'), callback_data='prices'),
         InlineKeyboardButton(T(uid, 'btn_back'), callback_data='menu')],
    ])


def share_url(text, link):
    return f'https://t.me/share/url?url={quote(link)}&text={quote(text)}'


async def out(u, text, kb, edit=False):
    if edit and u.callback_query:
        try:
            await u.callback_query.edit_message_text(
                text, parse_mode='HTML', reply_markup=kb)
            return
        except Exception:
            pass
    await u.effective_message.reply_text(
        text, parse_mode='HTML', reply_markup=kb)
