from aiogram import F, Router, types, Bot
import urllib.parse
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from JSON import *

router = Router()

@router.message(F.text.lower() == "👤 профиль")
async def profile_cmd(message: types.Message): 
    register_user(message.from_user)
    db = load_db()
    uid = str(message.from_user.id)
    user_data = db.get(uid, {})

    if message.chat.type != "private":
        return

    reg_date = user_data.get("registered_at") or "¯\_(ツ)_/¯"

    text = (
        "👤 <b>Ваш профиль:</b>\n"
        f"<blockquote><b>🚹 Имя:</b> {get_name(message.from_user.id)}\n"
        f"<b>🆔 ID:</b> <code>{user_data.get('id', 'Не указано')}</code>\n"
        f"<b>🪪 Username:</b> @{user_data['username'] if user_data.get('username') else 'НН'}</blockquote>\n"
        f"<blockquote><b>💰 RCY:</b> {user_data.get('rcy', 0)}\n"
        f"<b>🗝️ Ключи:</b> {user_data.get('keys', 0)}</blockquote>\n"
        f"<blockquote><b>👨‍👧‍👧 Рефералы:</b> {user_data.get('referrals', 0)}</blockquote>\n\n"
        f"<blockquote><b>📅 Зарегистрирован:</b> {reg_date}</blockquote>"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(F.text.lower() == "🆔 рефералы")
async def referrals_cmd(message: types.Message, bot: Bot):
    register_user(message.from_user)
    db = load_db()
    uid = str(message.from_user.id)
    user_data = db.get(uid, {})

    if message.chat.type != "private":
        return
    ref_link = f"https://t.me/{(await message.bot.me()).username}?start=ref_{uid}"
    referrals_count = user_data.get("referrals", 0)
    referrer_id = user_data.get("referrer")

    text = (
        "🆔 <b>Ваша реферальная система:</b>\n\n"
        f"<b>👨‍👧‍👧 Количество рефералов:</b> {referrals_count}\n"
    )

    if referrer_id:
        referrer_name = get_name(referrer_id)
        text += f"<b> Ваш реферер:</b> {referrer_name} (ID: <code>{referrer_id}</code>)\n"
    else:
        text += "<b> Ваш реферер:</b> Нету\n\n"

    text += f"🔗 Ваша реферальная ссылка: <code>{ref_link}</code>"

    text_inl = (
        "Лучший бот🎁\n"
        f" Только тут → {ref_link}"
    )
    encoded_text = urllib.parse.quote(text_inl)
    share_url = f"https://t.me/share/url?text={encoded_text}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛜 Поделиться", url=share_url)]
        ]
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


def get_top_by_rcy(db, limit=10):
    users = [
        (uid, data.get("rcy", 0))
        for uid, data in db.items()
        if data.get("rcy", 0) > 0
    ]
    users.sort(key=lambda x: x[1], reverse=True)
    return users[:limit]


def get_top_by_referrals(db, limit=10):
    users = [
        (uid, data.get("referrals", 0))
        for uid, data in db.items()
        if data.get("referrals", 0) > 0
    ]
    users.sort(key=lambda x: x[1], reverse=True)
    return users[:limit]


@router.message(F.text.in_(["топ", "топ10", "top", "top10"]))
async def top_rcy_handler(message: Message):
    db = load_db()
    top = get_top_by_rcy(db)

    if not top:
        return await message.answer("📭 Топ пуст.")

    medals = ["1️⃣", "2️⃣", "3️⃣"]
    text = "🏆 <b>Топ-10 по балансу RCY 💠</b>\n\n"

    for i, (uid, balance) in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        text += f"{prefix} {get_name(uid)} — <b>{balance} 💠</b>\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👨‍👧‍👧 Топ по рефералам",
                    callback_data=f"top_refs:{message.from_user.id}"
                )
            ]
        ]
    )

    await message.answer(text, parse_mode="HTML", reply_markup=kb)



@router.callback_query(F.data.startswith("top_refs:"))
async def top_refs_callback(query: CallbackQuery):
    owner_id = int(query.data.split(":")[1])

    if query.from_user.id != owner_id:
        return await query.answer("❌", show_alert=True)

    db = load_db()
    top = get_top_by_referrals(db)

    if not top:
        return await query.answer("📭 Топ пуст.", show_alert=True)

    medals = ["1️⃣", "2️⃣", "3️⃣"]
    text = "👨‍👧‍👧 <b>Топ-10 по рефералам</b>\n\n"

    for i, (uid, refs) in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        text += f"{prefix} {get_name(uid)} — <b>{refs}</b>\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💠 Топ по балансу",
                    callback_data=f"top_rcy:{owner_id}"
                )
            ]
        ]
    )

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("top_rcy:"))
async def top_rcy_callback(query: CallbackQuery):
    owner_id = int(query.data.split(":")[1])

    if query.from_user.id != owner_id:
        return await query.answer("❌", show_alert=True)

    db = load_db()
    top = get_top_by_rcy(db)

    if not top:
        return await query.answer("📭 Топ пуст.", show_alert=True)

    medals = ["1️⃣", "2️⃣", "3️⃣"]
    text = "🏆 <b>Топ-10 по балансу RCY 💠</b>\n\n"

    for i, (uid, balance) in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        text += f"{prefix} {get_name(uid)} — <b>{balance} 💠</b>\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👨‍👧‍👧 Топ по рефералам",
                    callback_data=f"top_refs:{owner_id}"
                )
            ]
        ]
    )

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await query.answer()
