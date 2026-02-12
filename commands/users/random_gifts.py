from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

import secrets
import time
import json
import os

from JSON import add_balance
from config import CREATOR_ID
from commands.admins.admin_ponel import admin_panel_cmd

router = Router()

CONTEST_CHANNEL_ID = -1002842739994


class RandomGiftsStates(StatesGroup):
    waiting_for_gift_users = State()
    waiting_for_pay = State()





def load_json(path: str, default: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)







@router.callback_query(F.data == "admin_random_gifts")
async def admin_random_gifts_callback(query: CallbackQuery, state: FSMContext):
    if query.from_user.id not in CREATOR_ID:
        return await query.answer("❌ Нет прав", show_alert=True)

    await query.message.answer("🎁 Введите количество участников:")
    await state.set_state(RandomGiftsStates.waiting_for_gift_users)


@router.message(RandomGiftsStates.waiting_for_gift_users)
async def process_users_count(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        return await message.answer("❌ Введите число больше 0")

    await state.update_data(max_users=int(message.text))
    await message.answer("💰 Введите сумму приза:")
    await state.set_state(RandomGiftsStates.waiting_for_pay)


@router.message(RandomGiftsStates.waiting_for_pay)
async def process_amount(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        return await message.answer("❌ Введите число больше 0")

    await state.update_data(amount=int(message.text))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💠 RCY", callback_data="gift_type:rcy")],
            [InlineKeyboardButton(text="🗝 KEYS", callback_data="gift_type:keys")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ]
    )

    await message.answer("🎁 Выберите тип приза:", reply_markup=kb)
    


@router.callback_query(F.data.startswith("gift_type:"))
async def process_gift_type(query: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not data:
        return await query.answer("❌ Сессия устарела", show_alert=True)

    prize_type = query.data.split(":")[1]
    contest_id = str(int(time.time() * 1000))

    contests = load_json("db/contests.json", {})

    text = (
        "🎉 <b>НАЧАЛСЯ КОНКУРС!</b>\n\n"
        f"🏆 Приз: <b>{data['amount']} {prize_type.upper()}</b>\n"
        f"👥 Участников: <b>0 / {data['max_users']}</b>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Участвовать",
                callback_data=f"join_contest:{contest_id}"
            )]
        ]
    )

    msg = await bot.send_message(
        CONTEST_CHANNEL_ID,
        text,
        parse_mode="HTML",
        reply_markup=kb
    )

    contests[contest_id] = {
        "message_id": msg.message_id,
        "max_users": data["max_users"],
        "amount": data["amount"],
        "type": prize_type,
        "participants": [],
        "active": True
    }

    save_json("db/contests.json", contests)
    await state.clear()
    await query.message.answer("✅ Конкурс создан")
    await admin_panel_cmd(query.message)


@router.callback_query(F.data.startswith("join_contest:"))
async def join_contest(query: CallbackQuery, bot: Bot):
    contest_id = query.data.split(":")[1]
    uid = query.from_user.id

    contests = load_json("db/contests.json", {})
    contest = contests.get(contest_id)

    if not contest or not contest["active"]:
        return await query.answer("❌ Конкурс завершён", show_alert=True)

    try:
        member = await bot.get_chat_member(CONTEST_CHANNEL_ID, uid)
        if member.status in ("left", "kicked"):
            return await query.answer("❌ Подпишитесь на канал", show_alert=True)
    except TelegramBadRequest:
        return await query.answer("❌ Бот не может проверить подписку", show_alert=True)

    if uid in contest["participants"]:
        return await query.answer("⚠️ Вы уже участвуете")

    contest["participants"].append(uid)

    count = len(contest["participants"])
    text = (
        "🎉 <b>НАЧАЛСЯ КОНКУРС!</b>\n\n"
        f"🏆 Приз: <b>{contest['amount']} {contest['type'].upper()}</b>\n"
        f"👥 Участников: <b>{count} / {contest['max_users']}</b>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Участвовать",
                callback_data=f"join_contest:{contest_id}"
            )]
        ]
    )

    await bot.edit_message_text(
        chat_id=CONTEST_CHANNEL_ID,
        message_id=contest["message_id"],
        text=text,
        parse_mode="HTML",
        reply_markup=kb
    )

    save_json("db/contests.json", contests)
    await query.answer("✅ Вы участвуете!")

    if count >= contest["max_users"]:
        await finish_contest(bot, contest_id)


# ------------------ ЗАВЕРШЕНИЕ ------------------

async def finish_contest(bot: Bot, contest_id: str):
    contests = load_json("db/contests.json", {})
    contest = contests.get(contest_id)

    if not contest or not contest["participants"]:
        return

    winner = secrets.choice(contest["participants"])
    contest["active"] = False

    add_balance(
        user_id=winner,
        currency=contest["type"],
        amount=contest["amount"]
    )

    text = (
        "🏆 <b>КОНКУРС ЗАВЕРШЁН!</b>\n\n"
        f"🎉 Победитель: <a href='tg://user?id={winner}'>пользователь</a>\n"
        f"🎁 Приз: <b>{contest['amount']} {contest['type'].upper()}</b>"
    )

    await bot.edit_message_text(
        chat_id=CONTEST_CHANNEL_ID,
        message_id=contest["message_id"],
        text=text,
        parse_mode="HTML",
        reply_markup=None
    )

    save_json("db/contests.json", contests)
