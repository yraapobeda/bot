from aiogram import F, Router, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import random

from JSON import *

router = Router()

@router.message(F.text.lower() == "/openc")
async def open_command(message: types.Message, bot: Bot):
    db = load_db()
    id = message.from_user.id
    register_user(message.from_user)

    if message.chat.type != "group" and message.chat.type != "supergroup":
        return await message.reply("❗ Эта команда доступна только в группах.")
    
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Открыть чемодан", callback_data=f"open_case:{id}")]
        ]
    )

    text = (
        f"🧳<b> Чемодан?</b>\n\n"
        f"Вы можете открыть свой чемодан который будет стоить 3 ключ и получить призы:\n"
        f"<blockquote>• RCY (от 0 до 10 💠)\n"
        f"• Ключики (от 0 до 7 🗝️)</blockquote>\n\n"

        f"Чтобы открыть чемодан нажмите на кнопку ниже."
        )
    await message.answer(text, reply_markup=kd, parse_mode="HTML", reply_to_message_id=message.message_id)



@router.callback_query(F.data.startswith("open_case:"))
async def open_case_callback(callback: CallbackQuery, bot: Bot):
    db = load_db()
    uid = str(callback.from_user.id)

    if callback.data.split(":")[1] != uid:
        return await callback.answer("❌ Это не ваш чемодан", show_alert=True)

    user = db.get(uid)
    if not user:
        return await callback.answer("❌ Пользователь не найден", show_alert=True)

    if user.get("keys", 0) < 3:
        return await callback.answer(f"❌ У вас нет ключей, у вас {user.get('keys', 0)}/3", show_alert=True)

    msg = await callback.message.edit_text("🧳 <b>Открытие чемодана.</b>", parse_mode="HTML")
    for dots in ["..", "...", "..", "."]:
        await asyncio.sleep(0.5)
        await msg.edit_text(f"🧳 <b>Открытие чемодана{dots}</b>", parse_mode="HTML")
    await asyncio.sleep(0.5)

    roll_type = random.uniform(0, 100)

    if roll_type <= 30:
        reward_type = "rcy"
        pool = [(i, max(0.05, 1 - i / 4)) for i in range(0, 11)]
    else:
        reward_type = "keys"
        pool = [(i, max(0.05, 1 - i / 3)) for i in range(0, 8)]

    amounts, weights = zip(*pool)
    amount = random.choices(amounts, weights=weights, k=1)[0]

    user[reward_type] = user.get(reward_type, 0) + amount
    user["keys"] -= 3
    save_db(db)

    await msg.delete()

    prize_text = (
        f"💠 <b>{amount} RCY</b>"
        if reward_type == "rcy"
        else f"🗝️ <b>{amount} ключ(а)</b>"
    )

    await callback.message.answer(
        f"🎉 <b>Поздравляем <a href='tg://user?id={uid}'>{get_name(uid)}</a></b>\n\n"
        f"🧳 Вы открыли чемодан и получили:\n"
        f"{prize_text}",
        parse_mode="HTML"
    )

    await callback.answer()

