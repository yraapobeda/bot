from aiogram import F, Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random
import asyncio
from aiogram.enums import ChatType
from aiogram import BaseMiddleware


from config import *
from config import CREATOR_ID as ADMIN
from JSON import *

router = Router()

def start_menu(uid: int):
    buttons = [
        [KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="🆔 Рефералы")],
        [KeyboardButton(text="💸 Донаты")]
    ]

    if uid in CREATOR_ID:
        buttons.append([KeyboardButton(text="🛠 Админ панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )



    
IGNORE_USERS = [1340806911, 7926367875]
CAPTCHA_SYMBOLS = {
    "🥦": "брoккoли",
    "🥝": "киви",
    "🍑": "пoпa",
    "🧅": "лyк",
    "🏹": "лyк",
    "⛸": "кoньки",
    "🛼": "pолики",
    "🥋": "кимoно",
    "🥭": "манго",
}

def generate_captcha_keyboard():
    items = list(CAPTCHA_SYMBOLS.keys())
    random.shuffle(items)
    buttons = []
    for i in range(0, 9, 3):
        row = [InlineKeyboardButton(text=emoji, callback_data=f"captcha_{emoji}") for emoji in items[i:i+3]]
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


welcome_text = (
    "<b>🕯 Добро пожаловать!</b>\n"
    
)


@router.message(CommandStart())
async def start_cmd(message: types.Message):
    args = message.text.split()
    db = load_db()
    uid = str(message.from_user.id)
    name = message.from_user.full_name
    register_user(message.from_user)

    if message.chat.type == "group" or message.chat.type == "supergroup":
        await message.reply(f"🌐 Я учту твое существование")
        return

    ignore_mode = int(uid) in IGNORE_USERS

    is_new_user = uid not in db

    if is_new_user:
        register_user(message.from_user)
        db = load_db()

    user = db[uid]

    if user.get("banned"):
        return await message.answer("🚫 Вы заблокированы и не можете использовать бота.")

    if not is_new_user:
        return await message.reply(
            welcome_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=start_menu(message.from_user.id)

        )

    if len(args) > 1 and args[1].startswith("ref_"):
        ref_id = args[1].replace("ref_", "")

        if ref_id == uid:
            return await message.reply(
                welcome_text, parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=start_menu(message.from_user.id)

            )

        if ref_id not in db or db[ref_id].get("banned"):
            return await message.reply(
                welcome_text, parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=start_menu(message.from_user.id)

            )

        already_has_referrer = user.get("referrer") is not None
        if already_has_referrer and not ignore_mode:
            return await message.reply(
                welcome_text, parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=start_menu(message.from_user.id)

            )

        emoji, word = random.choice(list(CAPTCHA_SYMBOLS.items()))
        db[uid]["captcha"] = {
            "target": emoji,
            "word": word,
            "ref_id": ref_id,
            "tries": 0
        }
        save_db(db)

        await message.answer(
            f"🧩 Подтверди, что ты не бот!\nВыбери эмодзи для слова: <b>{word}</b>",
            parse_mode="HTML",
            reply_markup=generate_captcha_keyboard()
        )
        return

    await message.reply(
        welcome_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=start_menu(message.from_user.id)

    )


@router.callback_query(F.data.startswith("captcha_"))
async def captcha_callback(callback: CallbackQuery):
    db = load_db()
    uid = str(callback.from_user.id)
    user_data = db.get(uid, {})
    captcha_data = user_data.get("captcha")

    if not captcha_data:
        return await callback.answer("❌ Капча не активна.", show_alert=True)

    chosen = callback.data.replace("captcha_", "")
    correct = captcha_data["target"]
    ref_id = captcha_data["ref_id"]
    tries = captcha_data.get("tries", 0)

    if tries >= 10:
        del db[uid]["captcha"]
        save_db(db)
        await callback.message.edit_text(
            "🚨 Вы заподозрены в том, что вы бот.\n"
            "🔁 Перейдите по реферальной ссылке ещё раз и попробуйте снова."
        )
        return

    if chosen != correct:
        new_emoji, new_word = random.choice(list(CAPTCHA_SYMBOLS.items()))
        db[uid]["captcha"] = {
            "target": new_emoji,
            "word": new_word,
            "ref_id": ref_id,
            "tries": tries + 1
        }
        save_db(db)
        await callback.message.edit_text(
            f"❌ Неверно! Попробуй снова.\n"
            f"🧩 Выбери эмодзи для слова: <b>{new_word}</b>\n"
            f"Ошибок: {tries + 1}/10",
            parse_mode="HTML",
            reply_markup=generate_captcha_keyboard()
        )
        return

    del db[uid]["captcha"]

    if uid not in db:
        register_user(callback.from_user)
        db = load_db()
    

    db[uid]["referrer"] = ref_id
    db[ref_id]["referrals"] = db[ref_id].get("referrals", 0) + 1

    total_refs = db[ref_id]["referrals"]

    progress = total_refs % 10

    if progress == 0 and total_refs != 0:
       progress = 10

    reward_text = ""


    if total_refs % 10 == 0:
       db[ref_id]["rcy"] = db[ref_id].get("rcy", 0) + 5
       reward_text = (
        "\n\n🎁 <b>Награда получена!</b>\n"
        "💰 +5 RCY за 10 приглашённых 👑"
    )
    refs_left = 10  

    save_db(db)


    try:
        await callback.bot.send_message(
            int(ref_id),
            f"🎉 <B>{callback.from_user.full_name}</b> стал(а) вашим рефералом!\n"
            f"🆔 <tg-spoiler>Айди: {uid}</tg-spoiler>\n\n"
            f"👥 Всего рефералов: <b>{total_refs}</b>\n"
            f"📊 Прогресс: <b>{progress}/10</b>",
            parse_mode="HTML"
        )
        await callback.bot.send_message(
            int(ref_id),
            reward_text,
            parse_mode="HTML"
        )
    except:
        pass

    await callback.message.answer("✅ Капча пройдена!", show_alert=True)
    await callback.message.answer(welcome_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=start_menu(callback.from_user.id))
    await callback.message.delete()
    await callback.answer()



@router.message(
    F.text.regexp(r"^/мешочек(\s+.+)?$") |
    F.text.lower().regexp(r"^мешочек(\s+.+)?$")
)
async def cmd_balance(message: Message):
    db = load_db()


    user_id = str(message.from_user.id)
    target_uid = user_id

    if message.from_user.id in CREATOR_ID:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) > 1:
            arg = parts[1].strip()
            if arg.isdigit() and arg in db:
                target_uid = arg
            else:
                for uid, udata in db.items():
                    if udata.get("username") and udata["username"].lower() == arg.lower().lstrip("@"):
                        target_uid = uid
                        break
        elif message.reply_to_message:
            target_uid = str(message.reply_to_message.from_user.id)
    else:
        target_uid = user_id

    if target_uid not in db:
        if target_uid == user_id:
            register_user(message.from_user)
            db = load_db()
        else:
            user_obj = (
                message.reply_to_message.from_user
                if message.reply_to_message and str(message.reply_to_message.from_user.id) == target_uid
                else None
            )
            if user_obj:
                register_user(user_obj)
                db = load_db()
            else:
                db[target_uid] = {"rcy": 0, "keys": 0}
                save_db(db)

    user = db[target_uid]
    text_parts = []

    if message.from_user.id in ADMIN:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) > 1:
            arg = parts[1].strip()
            if arg.isdigit() and arg in db:
                target_uid = arg
            else:
                for uid, udata in db.items():
                    if udata.get("username") and udata["username"].lower() == arg.lower().lstrip("@"):
                        target_uid = uid
                        break
        elif message.reply_to_message:
            target_uid = str(message.reply_to_message.from_user.id)
    else:
        target_uid = user_id

    if target_uid not in db:
        if target_uid == user_id:
            register_user(message.from_user)
            db = load_db()
        else:
            user_obj = (
                message.reply_to_message.from_user
                if message.reply_to_message and str(message.reply_to_message.from_user.id) == target_uid
                else None
            )
            if user_obj:
                register_user(user_obj)
                db = load_db()
            else:
                db[target_uid] = {"potato": 0, "candy": 0, "suitcase_keys": 0}
                save_db(db)

    user = db[target_uid]
    text_parts = []

    if message.from_user.id in ADMIN and user.get("banned"):
        banned_by = user.get("banned_by", "Неизвестно")
        reason = user.get("ban_reason", "Без причины")
        ban_time = user.get("ban_time", "Неизвестно")
        text_parts.append(
            f"🚫 Пользователь находится в бане.\n"
            f"🔨 Забанен админом: <a href='tg://user?id={banned_by}'><b>{get_name(banned_by)}</b></a>\n"
            f"📄 Причина: <b>{reason}</b>\n"
            f"🕒 Время бана: <code>{ban_time}</code>\n"
        )


    text_parts.append(
        f"⚱️ Что в мешочке у <a href='tg://user?id={target_uid}'><b>{get_name(target_uid)}</b></a>?\n"
        f"💰 RCY: {user.get('rcy', 0)}\n"
        f"🗝️ Ключи: {user.get('keys', 0)}"
    )
    

    await message.reply("\n".join(text_parts), parse_mode="HTML")


@router.message(F.text.lower() == "👨‍👧‍👧 рефералы")
async def help_cmd(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    user_data = db.get(uid, {})

    total_refs = user_data.get("referrals", 0)
    progress = total_refs % 10
    if progress == 0 and total_refs != 0:
        progress = 10
    refs_left = 10 - progress if progress != 0 else 0

    ref_link = f"https://t.me/{(await message.bot.me()).username}?start=ref_{uid}"

    text = (
        f"👥 <b>Ваши рефералы:</b>\n"
        f"Всего приглашено: <b>{total_refs}</b>\n"
        f"Прогресс до следующей награды: <b>{progress}/10</b>\n"
        f"Осталось до награды: <b>{refs_left}</b>\n\n"
        f"🔗 Ваша реферальная ссылка:\n"
        f"<code>{ref_link}</code>\n\n"
        "Приглашайте друзей и получайте награды!"
    )

    await message.answer(text, parse_mode="HTML")








from aiogram.types import ChatMemberUpdated
from pathlib import Path


GROUPS_FILE = Path("bd/groups.json")


VIDEO_NOTE_ID = "DQACAgQAAxkBAAEggelpX1XVEV5KdF_m04wCwP6N-LB3JAAC2RUAAjLfsVAqoOAUcVIiCzgE"

@router.my_chat_member()
async def on_bot_added(event: ChatMemberUpdated, bot):
    new_status = event.new_chat_member.status

    if new_status not in ("member", "administrator"):
        return

    chat = event.chat

    if chat.type not in ("group", "supergroup"):
        return

    chat_id = str(chat.id)
    chat_username = f"@{chat.username}" if chat.username else None

    if GROUPS_FILE.exists():
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            groups = json.load(f)
    else:
        groups = {}

    if chat_id not in groups and (not chat_username or chat_username not in groups):
        try:
            await asyncio.sleep(1)
            await bot.send_message(
                chat.id,
                "❌ <b>Этот бот не разрешён для использования в этой группе.</b>",
                parse_mode="HTML"
            )
            await asyncio.sleep(1.5)

            await bot.send_video_note(
                chat.id,
                VIDEO_NOTE_ID
            )

            await asyncio.sleep(1)
        except:
            pass

        await bot.leave_chat(chat.id)
        return

    try:
        await bot.send_message(
            chat.id,
            "👋 <b>Привет!</b>\n\n"
            "Бот успешно активирован в этой группе ✅\n"
            "Готов к работе 🚀\n\n"
            "⚠️ Добавьте меня в администраторы для корректной работы",
            parse_mode="HTML"
        )
    except:
        pass



class GroupGuardMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data.get("bot")
        chat = None

        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None

        if not chat:
            return await handler(event, data)

        if chat.type == "private":
            return await handler(event, data)

        if chat.type not in ("group", "supergroup"):
            return await handler(event, data)

        chat_id = str(chat.id)
        chat_username = f"@{chat.username}" if chat.username else None

        try:
            with open(GROUPS_FILE, "r", encoding="utf-8") as f:
                groups = json.load(f)
        except Exception:
            groups = {}

        if chat_id not in groups and (not chat_username or chat_username not in groups):
            try:
                await asyncio.sleep(1)
                await bot.send_message(
                    chat.id,
                    "❌ <b>Эта группа не разрешена для работы бота.</b>\nБот покинет группу.",
                    parse_mode="HTML"
                )
                await asyncio.sleep(1.5)
                await bot.send_video_note(
                chat.id,
                VIDEO_NOTE_ID
            )
                await asyncio.sleep(1)
                await bot.leave_chat(chat.id)
            except Exception:
                pass
            return 
        return await handler(event, data)
    
    
