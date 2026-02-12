from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from aiogram.methods.refund_star_payment import RefundStarPayment
from aiogram.types.labeled_price import LabeledPrice
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, ContentType, Message, PreCheckoutQuery
)


from JSON import *
from config import *

router = Router()
TOKEN_DATA = {}

class PaymentStates(StatesGroup):
    waiting_for_kru_amount = State()






def payment_kb(invoice_link: str, amount: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатить {amount} Stars", url=invoice_link)]
    ])


@router.message(F. text.lower() == "💸 донаты")
async def donate_command(message: types.Message, state: FSMContext):
    register_user(message.from_user)
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text= "Отмена", callback_data="cancel_donate")]
        ]
    )
    await message.answer("💠 Сколько RCY вы хотите приобрести?\n\n💰 Курс: 10 RCY = 1 ⭐ Stars\n\nВведите число (например, 10):", reply_markup=kd)
    await state.set_state(PaymentStates.waiting_for_kru_amount)

@router.message(PaymentStates.waiting_for_kru_amount)
async def process_kru_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        kru_amount = int(message.text)
        if kru_amount <= 0:
            await message.answer("❌ Количество должно быть положительным числом.")
            return
        if kru_amount < 10:
            await message.answer("❌ Минимальное количество RCY за одну покупку: 10.")
            return
        if kru_amount > 10000:
            await message.answer("❌ Максимальное количество RCY за одну покупку: 10,000.")
            return
        if kru_amount % 10 != 0:
            await message.answer("❌ Количество RCY должно быть кратно 10\n10-20-30-40-50-60-70-80-90-100.")
            return
    except ValueError:
        await message.answer("❌ Введите корректное число.")
        return

    stars_amount = kru_amount // 10
    payload = f"purchase_{message.from_user.id}_{kru_amount}"

    TOKEN_DATA[payload] = {
        "target_user_id": message.from_user.id,
        "kru_amount": kru_amount,
        "stars_amount": stars_amount
    }

    prices = [LabeledPrice(label="Stars", amount=stars_amount)]
    link = await bot.create_invoice_link(
        title=f"{kru_amount} RCY 💠",
        description=f"Оплата {stars_amount} Stars за {kru_amount} RCY",
        payload=payload,
        currency="XTR",
        prices=prices
    )

    await message.answer(
        f"💠 Вы выбрали: {kru_amount} RCY\n💰 Стоимость: {stars_amount} ⭐ Stars\n\nНажмите кнопку ниже для оплаты:",
        reply_markup=payment_kb(link, stars_amount)
    )
    await state.clear()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: PreCheckoutQuery):
    token = pre_checkout.invoice_payload
    data = TOKEN_DATA.get(token)
    
    if not data:
        await pre_checkout.answer(ok=False, error_message="Error: payment not found")
        return

    if pre_checkout.from_user.id != data.get("target_user_id"):
        await pre_checkout.answer(ok=False, error_message="This payment is intended for another user")
        return
        
    await pre_checkout.answer(ok=True)



@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: Message):
    payment_info = message.successful_payment

    if not payment_info:
        await message.answer("⚠️ Ошибка: данные платежа отсутствуют.")
        return

    token = payment_info.invoice_payload
    data = TOKEN_DATA.get(token)
    if not data:
        await message.answer("⚠️ Ошибка: информация о платеже не найдена.")
        return

    amount = payment_info.total_amount
    user_id = message.from_user.id
    provider_id = payment_info.provider_payment_charge_id

    db = load_db()
    db[str(user_id)]["rcy"] = db[str(user_id)].get("rcy", 0) + data["kru_amount"]
    save_db(db)

    await message.answer(
        f"✅ Платёж <b>{amount}</b> ⭐ успешно получен!\n"
        f"💠 На ваш баланс зачислено: <b>{data['kru_amount']} CRY💠</b>\n\n"
        f"Спасибо за покупку ❤️\n\n"
        f"<code>{message.successful_payment.telegram_payment_charge_id}</code>",
        parse_mode='html'
    )

@router.callback_query(F.data == "cancel_donate")
async def cancel_donate_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()
    await callback.answer("❌ Покупка отменена.", show_alert=True)





@router.message(F. text.startswith("/refund"))
async def refund_stars(message: types.Message, bot: Bot):
    if message.from_user.id not in CREATOR_ID:
        return 

    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("❌ Неверный формат.\nИспользуй: /refund <user_id> <transaction_id>")

    try:
        user_id = int(parts[1])
        transaction_id = parts[2]

        result = await bot(RefundStarPayment(
            user_id=user_id,
            telegram_payment_charge_id=transaction_id
        ))

        if result:
            await message.reply(f"✅ Возврат выполнен успешно!\n🧾 ID транзакции: `{transaction_id}`", parse_mode="Markdown")
        else:
            await message.reply(f"⚠️ Возврат не выполнен. Telegram API вернул False.")

    except TelegramAPIError as e:
        await message.reply(f"🚫 Ошибка Telegram API:\n`{e}`", parse_mode="Markdown")

    except Exception as e:
        await message.reply(f"⚠️ Произошла непредвиденная ошибка:\n`{e}`", parse_mode="Markdown")