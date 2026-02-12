from aiogram import Router, F, types, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram import BaseMiddleware

from pathlib import Path
from datetime import datetime
import json
import asyncio
from typing import Callable, Awaitable, Dict, Any

from config import CREATOR_ID

router = Router()

SUBS_FILE = Path("bd/required_subs.json")
SUBS_FILE.parent.mkdir(parents=True, exist_ok=True)

if not SUBS_FILE.exists():
    SUBS_FILE.write_text("{}", encoding="utf-8")


def load_subs():
    with open(SUBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_subs(data):
    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def now():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def normalize_link(text: str) -> str:
    text = text.strip()
    if text.startswith("@"):
        return f"https://t.me/{text[1:]}"
    return text


class SubscriptionStates(StatesGroup):
    choosing_type = State()
    waiting_for_link = State()
    waiting_for_chat_id = State()


@router.callback_query(F.data == "admin_subscription")
async def admin_subscription_cmd(callback: CallbackQuery):
    if callback.from_user.id not in CREATOR_ID:
        return

    subs = load_subs()
    keyboard = []

    if subs:
        row = []
        for sid in subs:
            row.append(
                InlineKeyboardButton(
                    text=f"🔗 {sid}",
                    callback_data=f"sub_info:{sid}"
                )
            )
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить", callback_data="sub_add")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="admin_panel")
    ])

    await callback.message.edit_text(
        "👑 <b>Админ-панель — Обязательная подписка</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "sub_add")
async def sub_add(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in CREATOR_ID:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Канал", callback_data="sub_type:channel"),
            InlineKeyboardButton(text="👥 Группа", callback_data="sub_type:group")
        ],
        [
            InlineKeyboardButton(text="⬅ Назад", callback_data="admin_subscription")
        ]
    ])

    await callback.message.edit_text(
        "➕ <b>Выберите тип</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.choosing_type)


@router.callback_query(F.data.startswith("sub_type:"))
async def sub_choose_type(callback: CallbackQuery, state: FSMContext):
    sub_type = callback.data.split(":")[1]
    await state.update_data(type=sub_type)

    await callback.message.edit_text(
        "🔗 Отправьте ссылку или @username канала/группы",
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.waiting_for_link)


@router.message(SubscriptionStates.waiting_for_link)
async def sub_get_link(message: Message, state: FSMContext):
    if message.from_user.id not in CREATOR_ID:
        return

    link = normalize_link(message.text)

    if not link.startswith("https://t.me/"):
        return await message.reply("❌ Отправьте ссылку или @username")

    await state.update_data(link=link)

    await message.answer(
        "🆔 Теперь отправьте <b>ID канала / группы</b>\n\n"
        "⚠️ <i>Бот должен быть добавлен в чат (желательно админом)</i>",
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.waiting_for_chat_id)


@router.message(SubscriptionStates.waiting_for_chat_id)
async def sub_check_chat(message: Message, state: FSMContext):
    if message.from_user.id not in CREATOR_ID:
        return

    chat_id = message.text.strip()
    data = await state.get_data()
    bot = message.bot

    try:
        await bot.get_chat(chat_id)
    except (TelegramForbiddenError, TelegramBadRequest):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Повторить", callback_data="sub_retry"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscription")
            ]
        ])
        return await message.answer(
            "❌ <b>Бот не видит этот чат</b>\n\n"
            "➡️ Добавьте бота в канал/группу и сделайте администратором",
            reply_markup=kb,
            parse_mode="HTML"
        )

    subs = load_subs()
    new_id = str(len(subs) + 1)

    subs[new_id] = {
        "type": data["type"],
        "link": data["link"],
        "chat_id": chat_id,
        "added_at": now()
    }

    save_subs(subs)
    await state.clear()

    await message.answer(
        "✅ <b>Подписка успешно добавлена</b>\n\n"
        "⚠️ Убедитесь, что бот — администратор",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "sub_retry")
async def sub_retry(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🆔 Отправьте ID канала / группы ещё раз",
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.waiting_for_chat_id)


@router.callback_query(F.data.startswith("sub_info:"))
async def sub_info(callback: CallbackQuery):
    sid = callback.data.split(":")[1]
    subs = load_subs()
    sub = subs.get(sid)

    if not sub:
        return await callback.answer("❌ Не найдено", show_alert=True)

    text = (
        "📌 <b>Подписка</b>\n\n"
        f"🆔 ID: <code>{sid}</code>\n"
        f"📍 Тип: {sub['type']}\n"
        f"🔗 {sub['link']}\n"
        f"🆔 Chat ID: <code>{sub['chat_id']}</code>\n"
        f"📅 {sub['added_at']}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"sub_delete:{sid}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="admin_subscription")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("sub_delete:"))
async def sub_delete(callback: CallbackQuery):
    sid = callback.data.split(":")[1]
    subs = load_subs()

    if sid in subs:
        del subs[sid]
        save_subs(subs)

    await callback.answer("🗑 Удалено")
    await callback.message.edit_text("✅ Подписка удалена")











async def is_subscribed(bot, user_id: int, chat_id: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False


def build_keyboard(subs: dict, missing: list, check=False, uid=None):
    kb = []

    for sid in missing:
        sub = subs[sid]
        kb.append([
            InlineKeyboardButton(
                text="🔔 Подписаться",
                url=sub["link"]
            )
        ])

    if check and uid:
        kb.append([
            InlineKeyboardButton(
                text="✅ Проверить подписку",
                callback_data=f"check_subs:{uid}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=kb)


async def safe_edit_message(message, new_kb: InlineKeyboardMarkup):
    try:
        old_kb = message.reply_markup
        if old_kb and old_kb.to_python() == new_kb.to_python():
            return 

        await message.edit_reply_markup(reply_markup=new_kb)
    except Exception as e:
        print("Safe edit failed:", e)

        





class SubscriptionMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ):

        if isinstance(event, CallbackQuery):
            return await handler(event, data)

        if not isinstance(event, Message):
            return await handler(event, data)

        if not event.from_user:
            return await handler(event, data)

        if event.text and event.text.startswith("/start"):
            return await handler(event, data)

        subs = load_subs()
        if not subs:
            return await handler(event, data)

        bot = event.bot
        user_id = event.from_user.id
        chat_type = event.chat.type

        missing = []
        for sid, sub in subs.items():
            if not await is_subscribed(bot, user_id, sub["chat_id"]):
                missing.append(sid)

        if not missing:
            return await handler(event, data)

        if chat_type == "private":
            sent = await event.answer(
                "❌ <b>Вы не подписаны на обязательные каналы</b>\n\n"
                "Подпишитесь, чтобы продолжить ⬇️",
                reply_markup=build_keyboard(subs, missing),
                parse_mode="HTML"
            )

            prev_keyboard = build_keyboard(subs, missing)

            while True:
                await asyncio.sleep(1)

                still_missing = []
                for sid, sub in subs.items():
                    if not await is_subscribed(bot, user_id, sub["chat_id"]):
                        still_missing.append(sid)

                if not still_missing:
                    try:
                        await sent.delete()
                    except:
                        pass

                    await event.answer(
                        "✅ <b>Вы успешно подписались на все каналы!</b>",
                        parse_mode="HTML"
                    )
                    break

                new_keyboard = build_keyboard(subs, still_missing)
                if new_keyboard != prev_keyboard:
                    try:
                        await sent.edit_reply_markup(reply_markup=new_keyboard)
                        prev_keyboard = new_keyboard
                    except:
                        pass

            return

        if chat_type in ("group", "supergroup"):
            await event.reply(
                "❌ <b>Для общения подпишитесь на каналы</b>",
                reply_markup=build_keyboard(subs, missing),
                parse_mode="HTML"
            )
            return






        

@router.callback_query(lambda c: c.data.startswith("check_subs:"))
async def check_subs(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])

    if callback.from_user.id != uid:
        return await callback.answer("❌ Это не для вас", show_alert=True)

    subs = load_subs()
    bot = callback.bot

    missing = []

    for sid, sub in subs.items():
        if not await is_subscribed(bot, uid, sub["chat_id"]):
            missing.append(sid)

    if not missing:
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            "✅ <b>Вы успешно подписались на все каналы!</b>",
            parse_mode="HTML"
        )
        return

    await callback.message.edit_reply_markup(
        reply_markup=build_keyboard(
            subs,
            missing,
            check=True,
            uid=uid
        )
    )

    await callback.answer("🔄 Проверено")
