import json
from datetime import datetime
from typing import Optional
from aiogram import Router, F, BaseMiddleware
from aiogram.types import Message
from JSON import load_db, save_db, register_user, get_name
from config import CREATOR_ID as ADMIN_IDS

router = Router()

ALLOWED_FOR_BANNED = []


def save_db_wrapper(db):
    save_db(db)


def resolve_target_by_username(db: dict, username: str) -> Optional[str]:
    uname = username.lstrip("@").lower()
    for uid, data in db.items():
        if data.get("username", "").lower() == uname:
            return uid
    return None


async def resolve_target(message: Message, arg: Optional[str]) -> Optional[str]:
    db = load_db()

    if message.reply_to_message:
        return str(message.reply_to_message.from_user.id)

    if arg:
        a = arg.strip()
        if a.isdigit() and a in db:
            return a
        if a.startswith("@"):
            return resolve_target_by_username(db, a)
        else:
            return resolve_target_by_username(db, "@" + a)

    return None


def set_ban(uid: str, banned_by: int, reason: Optional[str] = None):
    db = load_db()
    if uid not in db:
        register_user(int(uid))
        db = load_db()

    if db[uid].get("banned", False):
        return False  

    ban_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    db[uid]["banned"] = True
    db[uid]["ban_reason"] = reason or "Без причины"
    db[uid]["banned_by"] = banned_by
    db[uid]["ban_time"] = ban_time
    save_db_wrapper(db)
    return True


def unset_ban(uid: str):
    db = load_db()
    if uid not in db or not db[uid].get("banned", False):
        return False  

    db[uid]["banned"] = False
    db[uid].pop("ban_reason", None)
    db[uid].pop("banned_by", None)
    db[uid].pop("ban_time", None)
    save_db_wrapper(db)
    return True


def is_banned(uid: str) -> bool:
    db = load_db()
    user = db.get(uid)
    return bool(user and user.get("banned", False))


@router.message(F.text.regexp(r"^/mban(\s+.+)?$"))
async def cmd_cban(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return 

    parts = (message.text or "").split(maxsplit=2)
    arg = parts[1] if len(parts) > 1 else None
    reason = parts[2] if len(parts) > 2 else ""

    target = await resolve_target(message, arg)
    if not target:
        return await message.reply("❌ Не удалось определить пользователя (ID, @username или ответ).")

    ok = set_ban(str(target), banned_by=message.from_user.id, reason=reason)
    if not ok:
        return await message.reply("⚠️ Пользователь уже забанен.")

    name = get_name(int(target))
    ban_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    await message.reply(
        f"🔨 Пользователь <b>{name}</b> (<code>{target}</code>) был забанен.\n"
        f"🕒 Время: <code>{ban_time}</code>\n"
        f"📄 Причина: <b>{reason or 'Без причины'}</b>",
        parse_mode="HTML"
    )

    try:
        await message.bot.send_message(
            target,
            f"🚫 Вы были <b>забанены</b> в боте.\n"
            f"🕒 Время: <code>{ban_time}</code>\n"
            f"📄 Причина: <b>{reason or 'Без причины'}</b>",
            parse_mode="HTML"
        )
    except:
        pass


@router.message(F.text.regexp(r"^/munban(\s+.+)?$"))
async def cmd_cunban(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return 

    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1] if len(parts) > 1 else None

    target = await resolve_target(message, arg)
    if not target:
        return await message.reply("❌ Не удалось определить пользователя (ID, @username или ответ).")

    ok = unset_ban(str(target))
    if not ok:
        return await message.reply("⚠️ Этот пользователь не забанен.")

    name = get_name(int(target))
    await message.reply(
        f"✅ Пользователь <b>{name}</b> (<code>{target}</code>) был разбанен.",
        parse_mode="HTML"
    )

    try:
        await message.bot.send_message(
            target,
            "✅ Вы были <b>разбанены</b> и теперь можете снова использовать бота.",
            parse_mode="HTML"
        )
    except:
        pass


from aiogram import BaseMiddleware

class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data.get("bot")
        if not bot:
            return await handler(event, data)

        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if not user_id:
            return await handler(event, data)

        from JSON import load_db  
        db = load_db()
        user = db.get(str(user_id))

        if user and user.get("banned", False):
            chat_type = getattr(getattr(event, "chat", None), "type", "private")

            if chat_type in ["group", "supergroup"]:
                return  

            text = getattr(event, "text", "")
            if text and any(text.startswith(cmd) for cmd in ALLOWED_FOR_BANNED):
                return await handler(event, data)

            reason = user.get("ban_reason", "Без причины")
            time = user.get("ban_time", "Неизвестно")
            msg = (
                f"🚫 Вы забанены.\n"
                f"📄 Причина: <b>{reason}</b>\n"
                f"🕒 Время: <code>{time}</code>"
            )
            try:
                await bot.send_message(user_id, msg, parse_mode="HTML")
            except:
                pass

            return

        return await handler(event, data)
