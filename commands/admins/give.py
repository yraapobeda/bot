from aiogram import Router, F, types
from aiogram.filters import Command

from JSON import load_db, save_db, register_user, get_name
from config import CREATOR_ID

router = Router()



ITEMS = {
    "rcy": "rcy",
    "cry": "rcy",
    "ключ": "keys",
    "ключи": "keys",
    "ключей": "keys",
    "keys": "keys",
    "1": "rcy",
    "2": "keys"
}

@router.message(F.text.lower().startswith("выдать"))
async def give_command(message: types.Message):
    if message.from_user.id not in CREATOR_ID:
        return await message.reply("❌ У вас нет прав")

    if not message.reply_to_message:
        return await message.reply("❗ Используй команду ответом на сообщение")

    args = message.text.split()
    if len(args) != 3:
        return await message.reply(
            "❗ Формат:\n"
            "<code>выдать <количество> <ресурс></code>\n"
            "Пример: <code>выдать 5 rcy</code>",
            parse_mode="HTML"
        )

    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.reply("❌ Количество должно быть числом больше 0")

    item_input = args[2].lower()
    item = ITEMS.get(item_input)

    if not item:
        return await message.reply("❌ Неизвестный ресурс")

    target = message.reply_to_message.from_user
    uid = str(target.id)

    db = load_db()
    register_user(target)

    user = db.get(uid)
    user[item] = user.get(item, 0) + amount
    save_db(db)

    emoji = "💠" if item == "rcy" else "🗝️"

    await message.reply(
        f"✅ <b>Выдано!</b>\n\n"
        f"👤 Пользователь: <a href='tg://user?id={uid}'>{get_name(uid)}</a>\n"
        f"{emoji} {item.upper()}: +{amount}",
        parse_mode="HTML"
    )


@router.message(F.text.lower().startswith("забрать"))
async def take_command(message: types.Message):
    if message.from_user.id not in CREATOR_ID:
        return await message.reply("❌ У вас нет прав")

    if not message.reply_to_message:
        return await message.reply("❗ Используй команду ответом на сообщение")

    args = message.text.split()
    if len(args) != 3:
        return await message.reply(
            "❗ Формат:\n"
            "<code>забрать <количество> <ресурс></code>\n"
            "Пример: <code>забрать 5 rcy</code>",
            parse_mode="HTML"
        )

    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.reply("❌ Количество должно быть числом больше 0")

    item_input = args[2].lower()
    item = ITEMS.get(item_input)
    if not item:
        return await message.reply("❌ Неизвестный ресурс")

    target = message.reply_to_message.from_user
    uid = str(target.id)

    db = load_db()
    register_user(target)

    user = db.get(uid)
    current_amount = user.get(item, 0)

    if current_amount <= 0:
        return await message.reply("❌ У пользователя нет этого ресурса")

    user[item] = max(0, current_amount - amount)
    save_db(db)

    emoji = "💠" if item == "rcy" else "🗝️"

    await message.reply(
        f"✅ <b>Забрано!</b>\n\n"
        f"👤 Пользователь: <a href='tg://user?id={uid}'>{get_name(uid)}</a>\n"
        f"{emoji} {item.upper()}: -{amount}",
        parse_mode="HTML"
    )
