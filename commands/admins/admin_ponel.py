from aiogram import F, Router, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from JSON import *
from config import CREATOR_ID

router = Router()

class AdminPanelStates(StatesGroup):
    waiting_for_give_id = State()
    waiting_for_give_type = State()
    waiting_for_give_amount = State()
    # ==================================================
    waiting_for_profile_id = State()
    # ==================================================
    waiting_for_promo_code = State()
    waiting_for_promo_currency = State()
    waiting_for_promo_amount = State()
    waiting_for_promo_max_uses = State()

    waiting_for_promo_id_or_code = State()
    waiting_for_promo_confirm = State()
    # ==================================================
    waiting_for_group_id_or_username = State()
    waiting_for_group_id_or_username_delete = State()
    waiting_for_group_id_delete = State()
    # ==================================================




DB_DIR = Path("bd")
PROMO_DB_FILE = DB_DIR / "promocodes.json"

DB_DIR.mkdir(parents=True, exist_ok=True)

if not PROMO_DB_FILE.exists():
    PROMO_DB_FILE.write_text("{}", encoding="utf-8")


def load_promo_db():
    with open(PROMO_DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_promo_db(data):
    with open(PROMO_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)




async def admin_panel_cmd(message: types.Message):

    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Выдать деньги", callback_data="admin_give")],
            [InlineKeyboardButton(text="🚹 Профили", callback_data="admin_profiles"), InlineKeyboardButton(text="🎁 Промокоды", callback_data="admin_create_promo")],
            [InlineKeyboardButton(text="👨‍👩‍👦‍👦 Группы", callback_data="admin_grops"), InlineKeyboardButton(text="👮 Обязательная подписка", callback_data="admin_subscription")],
            [InlineKeyboardButton(text="Рандомайзер", callback_data="admin_random_gifts")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        ]
    )

    text = (
        f"🛠 <b>Админ панель</b>\n\n"
    )
    await message.answer(text, reply_markup=kd, parse_mode="HTML", reply_to_message_id=message.message_id)


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in CREATOR_ID:
        return
    await admin_panel_cmd(callback.message)
    await state.clear()
@router.message(F.text.lower() == "🛠 админ панель")
async def admin_panel_message(message: types.Message, state: FSMContext):
    if message.from_user.id not in CREATOR_ID:
        return
    await admin_panel_cmd(message)
    await state.clear()

#==================================================================

@router.callback_query(F.data == "admin_give")
async def admin_give_callback(callback: CallbackQuery, state: FSMContext):
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")]
        ]
    )
    await callback.message.edit_text(
        f"Введите id/@username пользователя которому хотите выдать деньги.", reply_markup=kd
    )
    await state.set_state(AdminPanelStates.waiting_for_give_id)

@router.message(AdminPanelStates.waiting_for_give_id)
async def admin_give_message(message: types.Message, state: FSMContext):
    db = load_db()
    text = message.text.strip().lstrip("@")

    user = None
    uid = None

    if text.isdigit():
        uid = text
        user = db.get(uid)
    else:
        for k, v in db.items():
            if v.get("username") and v["username"].lower() == text.lower():
                uid = k
                user = v
                break

    if not user:
        return await message.reply("❌ Пользователь не найден")

    await state.update_data(target_uid=uid)

    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💠 RCY", callback_data="give_type:rcy"),
                InlineKeyboardButton(text="🗝️ Keys", callback_data="give_type:keys")
            ],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="admin_panel")]
        ]
    )

    await message.answer(
        f"👤 <b>Пользователь <a href='tg://openmessage?user_id={uid}'>{get_name(uid)}</a></b>\n\n"
        "💰 <b>Баланс:</b>\n"
        f"💠 RCY: {user.get('rcy', 0)}\n"
        f"🗝️ Keys: {user.get('keys', 0)}\n\n"
        "👇 <b>Что выдать?</b>",
        reply_markup=kd,
        parse_mode="HTML"
    )

    await state.set_state(AdminPanelStates.waiting_for_give_type)

@router.callback_query(
    AdminPanelStates.waiting_for_give_type,
    F.data.startswith("give_type:")
)
async def admin_give_type(callback: CallbackQuery, state: FSMContext):
    give_type = callback.data.split(":")[1]
    tip = {
        "rcy": "💠 RCY",
        "keys": "🗝️ Keys",
    }
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data="admin_panel")]
        ])

    await state.update_data(give_type=give_type)

    await callback.message.edit_text(
        f"✏️ <b>Введите количество для выдачи</b>\n\n"
        f"Тип: {tip[give_type]}",
        parse_mode="HTML",
        reply_markup=kd
    )

    await state.set_state(AdminPanelStates.waiting_for_give_amount)
    await callback.answer()

@router.message(AdminPanelStates.waiting_for_give_amount)
async def admin_give_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.reply("❌ Введите число")

    amount = int(message.text)
    if amount <= 0:
        return await message.reply("❌ Количество должно быть больше 0")

    data = await state.get_data()
    uid = data["target_uid"]
    give_type = data["give_type"]

    db = load_db()
    user = db.get(uid)

    user[give_type] = user.get(give_type, 0) + amount
    save_db(db)

    emoji = "💠" if give_type == "rcy" else "🗝️"

    await message.answer(
        "✅ <b>Успешно выдано</b>\n\n"
        f"👤 ID: <code>{uid}</code>\n"
        f"{emoji} {give_type.upper()}: +{amount}",
        parse_mode="HTML"
    )

    await state.clear()
    await admin_panel_cmd(message)


#==================================================================
@router.callback_query(F.data == "admin_profiles")
async def admin_profiles_callback(callback: CallbackQuery, state: FSMContext):
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")]]
    )
    await callback.message.edit_text(
        f"Введите id/@username пользователя для просмотра профиля.", reply_markup=kd)
    await state.set_state(AdminPanelStates.waiting_for_profile_id)


@router.message(AdminPanelStates.waiting_for_profile_id)
async def admin_profile_message(message: types.Message, state: FSMContext):
    db = load_db()
    text = message.text.strip().lstrip("@")

    uid = None
    user = None

    if text.isdigit():
        uid = text
        user = db.get(uid)
    else:
        for k, v in db.items():
            if v.get("username") and v["username"].lower() == text.lower():
                uid = k
                user = v
                break

    if not user:
        return await message.reply("❌ Пользователь не найден")

    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Выдать", callback_data=f"admin_give:{uid}"),
                InlineKeyboardButton(text="⭕ Обнулить балансы", callback_data=f"admin_reset_user:{uid}")
            ],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="admin_panel")]
        ]
    )

    reg_date = user.get("registered_at") or "¯\\_(ツ)_/¯"

    profile_text = (
        "👤 <b>Профиль пользователя:</b>\n"
        f"<blockquote><b>🚹 Имя:</b> {get_name(uid)}\n"
        f"<b>🆔 ID:</b> <code>{uid}</code>\n"
        f"<b>🪪 Username:</b> @{user.get('username', 'НН')}</blockquote>\n"
        f"<blockquote><b>💰 RCY:</b> {user.get('rcy', 0)}\n"
        f"<b>🗝️ Ключи:</b> {user.get('keys', 0)}</blockquote>\n"
        f"<blockquote><b>👨‍👧‍👧 Рефералы:</b> {user.get('referrals', 0)}</blockquote>\n\n"
        f"<blockquote><b>📅 Зарегистрирован:</b> {reg_date}</blockquote>"
    )

    await message.answer(profile_text, reply_markup=kd, parse_mode="HTML")
    await state.clear()


@router.callback_query(F.data.startswith("admin_reset_user:"))
async def admin_reset_user_callback(callback: CallbackQuery, state: FSMContext):
    uid = callback.data.split(":")[1]
    db = load_db()
    user = db.get(uid)

    if not user:
        return await callback.message.answer("❌ Пользователь не найден")

    user["rcy"] = 0
    user["keys"] = 0
    save_db(db)

    await callback.message.answer(
        "✅ <b>Баланс пользователя обнулен</b>\n\n"
        f"👤 ID: <code>{uid}</code>\n"
        f"💠 RCY: 0\n"
        f"🗝️ Keys: 0",
        parse_mode="HTML"
    )

#================================================

def promo_currency_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💠 RCY", callback_data="promo_currency:rcy")],
            [InlineKeyboardButton(text="🗝️ Ключи", callback_data="promo_currency:keys")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ]
    )

@router.callback_query(F.data == 'admin_create_promo')
async def create_promo(call: CallbackQuery, state: FSMContext):
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promoes"), InlineKeyboardButton(text='⭕ удалить промо', callback_data="admin_delete_promo")],
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")]
        ]
    )
    await call.message.edit_text(
        f"Выберите действие:", reply_markup=kd
    )
    return

@router.callback_query(F.data == 'admin_create_promoes')
async def start_create_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Введите название промокода</b>\n"
        "Одним сообщением, без пробелов",
        parse_mode="HTML"
    )
    await state.set_state(AdminPanelStates.waiting_for_promo_code)

@router.message(AdminPanelStates.waiting_for_promo_code)
async def promo_code_name(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()

    if len(code) < 3:
        return await message.answer("❌ Слишком короткое название")

    await state.update_data(code=code)

    await message.answer(
        "💰 <b>Выберите валюту</b>",
        reply_markup=promo_currency_kb(),
        parse_mode="HTML"
    )

    await state.set_state(AdminPanelStates.waiting_for_promo_currency)

@router.callback_query(
    AdminPanelStates.waiting_for_promo_currency,
    F.data.startswith("promo_currency:")
)
async def promo_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split(":")[1]

    await state.update_data(currency=currency)

    await callback.message.edit_text(
        "🔢 <b>Введите количество</b>",
        parse_mode="HTML"
    )

    await state.set_state(AdminPanelStates.waiting_for_promo_amount)
    await callback.answer()

@router.message(AdminPanelStates.waiting_for_promo_amount)
async def promo_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Введите число")

    amount = int(message.text)
    if amount <= 0:
        return await message.answer("❌ Количество должно быть больше 0")

    await state.update_data(amount=amount)

    await message.answer(
        "👥 <b>Введите максимальное количество пользователей</b>",
        parse_mode="HTML"
    )

    await state.set_state(AdminPanelStates.waiting_for_promo_max_uses)

@router.message(AdminPanelStates.waiting_for_promo_max_uses)
async def promo_max_uses(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Введите число")

    max_uses = int(message.text)
    if max_uses <= 0:
        return await message.answer("❌ Должно быть больше 0")

    data = await state.get_data()

    promo_db = load_promo_db()

    next_id = str(max(map(int, promo_db.keys()), default=0) + 1)

    promo_db[next_id] = {
        "code": data["code"],
        "reward_type": data["currency"],
        "amount": data["amount"],
        "max_uses": max_uses,
        "used": 0,
        "users": []
    }

    save_promo_db(promo_db)
    types_name_pay = {
        "rcy": "💠 RCY",
        "keys": "🗝️ Keys"
    }

    await message.answer(
        "✅ <b>Промокод создан!</b>\n\n"
        f"🏷 Код: <code>{data['code']}</code>\n"
        f"💰 Валюта: {types_name_pay.get(data['currency'], data['currency'])}\n"
        f"🔢 Количество: {data['amount']}\n"
        f"👥 Лимит: {max_uses}",
        parse_mode="HTML"
    )

    await state.clear()
    await admin_panel_cmd(message)




def promo_delete_confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data="promo_delete_yes")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="promo_delete_no")]
        ]
    )

@router.callback_query(F.data == "admin_delete_promo")
async def start_delete_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🗑 <b>Введите ID или название промокода</b>",
        parse_mode="HTML"
    )
    await state.set_state(AdminPanelStates.waiting_for_promo_id_or_code)

@router.message(AdminPanelStates.waiting_for_promo_id_or_code)
async def promo_find(message: types.Message, state: FSMContext):
    text = message.text.strip()

    promo_db = load_promo_db()

    found_id = None
    promo = None

    if text.isdigit() and text in promo_db:
        found_id = text
        promo = promo_db[text]

    else:
        for pid, data in promo_db.items():
            if data["code"].lower() == text.lower():
                found_id = pid
                promo = data
                break

    if not promo:
        return await message.answer("❌ Промокод не найден")

    await state.update_data(promo_id=found_id)

    await message.answer(
        "⚠️ <b>Вы уверены, что хотите удалить промокод?</b>\n\n"
        f"🆔 ID: <code>{found_id}</code>\n"
        f"🏷 Код: <code>{promo['code']}</code>\n"
        f"💰 Валюта: {promo['reward_type']}\n"
        f"🔢 Количество: {promo['amount']}\n"
        f"👥 Лимит: {promo['max_uses']}",
        reply_markup=promo_delete_confirm_kb(),
        parse_mode="HTML"
    )

    await state.set_state(AdminPanelStates.waiting_for_promo_confirm)

@router.callback_query(AdminPanelStates.waiting_for_promo_confirm)
async def promo_delete_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    promo_id = data["promo_id"]

    if callback.data == "promo_delete_no":
        await callback.message.edit_text("❌ Удаление отменено")
        await admin_panel_cmd(callback.message)
        await state.clear()
        
        return await callback.answer()

    promo_db = load_promo_db()

    if promo_id not in promo_db:
        await callback.message.edit_text("❌ Промокод уже удалён")
        await admin_panel_cmd(callback.message)
        await state.clear()
        
        return await callback.answer()

    del promo_db[promo_id]
    save_promo_db(promo_db)

    await callback.message.edit_text(
        f"🗑 <b>Промокод удалён</b>\n"
        f"🆔 ID: <code>{promo_id}</code>",
        parse_mode="HTML"
    )

    await state.clear()
    await admin_panel_cmd(callback.message)
    await callback.answer("Удалено")
    





import re

@router.message(F.text.regexp(r"#(\w+)$"))
async def activate_promo(message: Message):
    promo_code = re.search(r"#(\w+)$", message.text).group(1)

    db = load_db()
    promo_db = load_promo_db()

    uid = str(message.from_user.id)

    if uid not in db:
        register_user(message.from_user)
        db = load_db()

    promo_id = None
    promo = None

    for pid, data in promo_db.items():
        if data["code"].lower() == promo_code.lower():
            promo_id = pid
            promo = data
            break

    if not promo:
        return 

    if uid in promo.get("users", []):
        return await message.reply("⚠️ Вы уже активировали этот промокод")

    if promo["used"] >= promo["max_uses"]:
        return await message.reply("❌ Лимит активаций исчерпан")

    reward_type = promo["reward_type"]
    amount = promo["amount"]

    db[uid][reward_type] = db[uid].get(reward_type, 0) + amount

    promo["used"] += 1
    promo.setdefault("users", []).append(uid)

    save_db(db)
    save_promo_db(promo_db)

    emoji = "💠" if reward_type == "rcy" else "🗝️"

    await message.reply(
        "🎉 <b>Промокод активирован!</b>\n"
        f"🎁 Награда: <b>{amount} {reward_type.upper()} {emoji}</b>",
        parse_mode="HTML"
    )


#===========================================================


def get_users_stats():
    db = load_db()

    total_users = len(db)
    premium_users = 0
    came_alone = 0
    came_by_ref = 0
    referrers = 0

    for user in db.values():
        if user.get("is_premium"):
            premium_users += 1

        if user.get("referrer"):
            came_by_ref += 1
        else:
            came_alone += 1

        if user.get("referrals", 0) > 0:
            referrers += 1

    return {
        "total": total_users,
        "premium": premium_users,
        "alone": came_alone,
        "by_ref": came_by_ref,
        "referrers": referrers
    }

@router.callback_query(F.data == "admin_stats")
async def stats_cmd(callback: types.CallbackQuery):
    if callback.from_user.id not in CREATOR_ID:
        return
    
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Рассылка", callback_data="admin_mailing")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ]
    )

    stats = get_users_stats()

    await callback.message.edit_text(
        "📊 <b>Статистика бота</b>\n\n"
        f"<blockquote>👥 Всего пользователей: <b>{stats['total']}</b>\n"
        f"⭐ Премиум: <b>{stats['premium']}</b></blockquote>\n\n"
        f"<blockquote>🚶 Пришли сами: <b>{stats['alone']}</b>\n"
        f"🔗 По рефералке: <b>{stats['by_ref']}</b></blockquote>\n\n"
        f"<blockquote>🧲 Рефераловоды: <b>{stats['referrers']}</b></blockquote>",
        parse_mode="HTML",
        reply_markup=kd
    )
















#===========================================================

@router.callback_query(F.data == "admin_grops")
async def admin_groups_callback(callback: CallbackQuery, state: FSMContext):
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить группу", callback_data="admin_add_group"), InlineKeyboardButton(text="❌ Удалить группу", callback_data="admin_delete_group")],
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")]]
    )
    await callback.message.edit_text(
        f"Выберите действие:", reply_markup=kd)
    return

@router.callback_query(F.data == "admin_add_group")
async def admin_add_group_callback(callback: CallbackQuery, state: FSMContext):
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_grops")]
        ]
    )
    await callback.message.edit_text(
        f"Введите ID группы для добавления в формате -100..........\nПример <b>-1003111732314</b>", reply_markup=kd, parse_mode="HTML")
    await state.set_state(AdminPanelStates.waiting_for_group_id_or_username)

@router.message(AdminPanelStates.waiting_for_group_id_or_username)
async def admin_add_group_message(message: types.Message, state: FSMContext):
    group_id_or_username = message.text.strip()

    DB_DIR = Path("bd")
    DB_FILE = DB_DIR / "groups.json"

    DB_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_FILE.exists():
        DB_FILE.write_text("{}", encoding="utf-8")

    with open(DB_FILE, "r", encoding="utf-8") as f:
        groups_db = json.load(f)

    if group_id_or_username in groups_db:
        return await message.answer("❌ Эта группа уже добавлена.")

    now = datetime.now()

    groups_db[group_id_or_username] = {
        "group": group_id_or_username,
        "added_by": str(message.from_user.id),
        "added_at": now.strftime("%d.%m.%Y %H:%M"),
        "timestamp": int(now.timestamp())
    }

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(groups_db, f, ensure_ascii=False, indent=4)

    await message.answer(
        f"✅ Группа <b>{group_id_or_username}</b> успешно добавлена!",
        parse_mode="HTML"
    )

    await state.clear()
    await admin_panel_cmd(message)

@router.callback_query(F.data == "admin_delete_group")
async def admin_delete_group_callback(callback: CallbackQuery, state: FSMContext):
    kd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_grops")]
        ]
    )
    await callback.message.edit_text(
        f"Введите ID группы для удаления в формате -100..........\nПример <b>-1003111732314</b>", reply_markup=kd, parse_mode="HTML")
    await state.set_state(AdminPanelStates.waiting_for_group_id_or_username_delete)

@router.message(AdminPanelStates.waiting_for_group_id_or_username_delete)
async def admin_delete_group_input(message: types.Message, state: FSMContext):
    group_key = message.text.strip()

    DB_FILE = Path("bd/groups.json")

    if not DB_FILE.exists():
        return await message.answer("❌ База групп пуста.")

    with open(DB_FILE, "r", encoding="utf-8") as f:
        groups_db = json.load(f)

    if group_key not in groups_db:
        return await message.answer("❌ Группа не найдена.")

    group = groups_db[group_key]

    await state.update_data(group_key=group_key)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_group"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_ponel")
            ]
        ]
    )

    await message.answer(
        "⚠ <b>Подтвердите удаление группы</b>\n\n"
        f"👥 Группа: <b>{group_key}</b>\n"
        f"👤 Добавил: <code>{group['added_by']}</code>\n"
        f"📅 Дата: {group['added_at']}",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await state.set_state(AdminPanelStates.waiting_for_group_id_delete)

@router.callback_query(F.data == "confirm_delete_group")
async def admin_confirm_delete_group(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    group_key = data["group_key"]

    DB_FILE = Path("bd/groups.json")

    with open(DB_FILE, "r", encoding="utf-8") as f:
        groups_db = json.load(f)

    if group_key not in groups_db:
        await callback.answer("❌ Группа уже удалена", show_alert=True)
        await state.clear()
        return

    del groups_db[group_key]

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(groups_db, f, ensure_ascii=False, indent=4)

    await callback.message.edit_text(
        f"✅ Группа <b>{group_key}</b> успешно удалена.",
        parse_mode="HTML"
    )

    await state.clear()
    await admin_panel_cmd(callback.message)
