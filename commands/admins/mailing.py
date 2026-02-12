from aiogram import F, Router, Bot, types
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from JSON import load_db
from config import CREATOR_ID

router = Router()


class MailingStates(StatesGroup):
    text = State()
    media = State()
    buttons = State()
    preview = State()
    edit_text = State()
    edit_media = State()
    edit_buttons = State()



def empty_mailing():
    return {
        "text": "",
        "media": [],
        "buttons": []
    }



def media_kb(count):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Готово ({count}/3)", callback_data="media_done")]
    ])


def edit_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Текст", callback_data="edit_text")],
        [InlineKeyboardButton(text="🖼 Медиа", callback_data="edit_media")],
        [InlineKeyboardButton(text="🔘 Кнопки", callback_data="edit_buttons")],
        [InlineKeyboardButton(text="📤 Разослать", callback_data="send_mailing")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_mailing")]
    ])



@router.callback_query(F.data == "admin_mailing")
async def admin_menu(q: CallbackQuery):
    if q.from_user.id not in CREATOR_ID:
        return await q.answer("❌", show_alert=True)

    await q.message.answer(
        "<b>📮 Меню рассылки</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Создать рассылку", callback_data="create_mailing")]
        ])
    )
    await q.answer()


@router.callback_query(F.data == "create_mailing")
async def create(q: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(mailing=empty_mailing())
    await state.set_state(MailingStates.text)

    await q.message.answer(
        "<b>✏️ Отправь текст рассылки</b>\n"
        "Поддерживается <b>Markdown</b>",
        parse_mode="HTML"
    )
    await q.answer()



@router.message(MailingStates.text)
@router.message(MailingStates.edit_text)
async def set_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    data["mailing"]["text"] = msg.text
    await state.update_data(mailing=data["mailing"])

    await state.set_state(MailingStates.media)
    await msg.answer(
        "<b>🖼 Отправь до 3 фото / видео</b>",
        parse_mode="HTML",
        reply_markup=media_kb(0)
    )



@router.message(MailingStates.media)
@router.message(MailingStates.edit_media)
async def set_media(msg: Message, state: FSMContext):
    data = await state.get_data()
    mailing = data["mailing"]

    if len(mailing["media"]) >= 3:
        return

    if msg.photo:
        mailing["media"].append(("photo", msg.photo[-1].file_id))
    elif msg.video:
        mailing["media"].append(("video", msg.video.file_id))
    else:
        return

    await state.update_data(mailing=mailing)

    await msg.answer(
        f"📎 Добавлено: <b>{len(mailing['media'])}/3</b>",
        parse_mode="HTML",
        reply_markup=media_kb(len(mailing["media"]))
    )


@router.callback_query(F.data == "media_done")
async def media_done(q: CallbackQuery, state: FSMContext):
    await state.set_state(MailingStates.buttons)
    await q.message.answer(
        "<b>🔘 Отправь кнопки</b>\n"
        "<code>Текст | https://site.ru</code>\n"
        "до 5 шт или напиши <b>пропустить</b>",
        parse_mode="HTML"
    )
    await q.answer()



@router.message(MailingStates.buttons)
@router.message(MailingStates.edit_buttons)
async def set_buttons(msg: Message, state: FSMContext):
    data = await state.get_data()
    mailing = data["mailing"]
    mailing["buttons"] = []

    if msg.text.lower() != "пропустить":
        for line in msg.text.splitlines():
            if "|" not in line or len(mailing["buttons"]) >= 5:
                continue
            t, u = line.split("|", 1)
            mailing["buttons"].append((t.strip(), u.strip()))

    await state.update_data(mailing=mailing)
    await show_preview(msg, state)



async def show_preview(msg: Message, state: FSMContext):
    data = await state.get_data()
    m = data["mailing"]

    kb = None
    if m["buttons"]:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t, url=u)] for t, u in m["buttons"]]
        )

    if m["media"]:
        media = []
        for i, (t, fid) in enumerate(m["media"]):
            caption = m["text"] if i == 0 else None
            if t == "photo":
                media.append(InputMediaPhoto(media=fid, caption=caption, parse_mode="MarkdownV2"))
            else:
                media.append(InputMediaVideo(media=fid, caption=caption, parse_mode="MarkdownV2"))

        msgs = await msg.answer_media_group(media)
        if kb:
            await msgs[-1].edit_reply_markup(reply_markup=kb)

    else:
        await msg.answer(m["text"], parse_mode="MarkdownV2", reply_markup=kb)

    await msg.answer(
        "<b>⚙️ Управление рассылкой</b>",
        parse_mode="HTML",
        reply_markup=edit_kb()
    )

    await state.set_state(MailingStates.preview)



@router.callback_query(F.data.startswith("edit_"))
async def edit(q: CallbackQuery, state: FSMContext):
    action = q.data.replace("edit_", "")
    await state.set_state(getattr(MailingStates, f"edit_{action}"))

    text = {
        "text": "✏️ Отправь новый текст",
        "media": "🖼 Отправь новые медиа",
        "buttons": "🔘 Отправь новые кнопки"
    }[action]

    await q.message.answer(text, parse_mode="HTML")
    await q.answer()


@router.callback_query(F.data == "send_mailing")
async def send(q: CallbackQuery, bot: Bot, state: FSMContext):
    if q.from_user.id not in CREATOR_ID:
        return await q.answer("❌", show_alert=True)

    data = await state.get_data()
    m = data["mailing"]
    db = load_db()

    for uid in db:
        try:
            kb = None
            if m["buttons"]:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=t, url=u)] for t, u in m["buttons"]]
                )

            if m["media"]:
                media = []
                for i, (t, fid) in enumerate(m["media"]):
                    caption = m["text"] if i == 0 else None
                    cls = InputMediaPhoto if t == "photo" else InputMediaVideo
                    media.append(cls(media=fid, caption=caption, parse_mode="MarkdownV2"))

                msgs = await bot.send_media_group(uid, media)
                if kb:
                    await bot.edit_message_reply_markup(uid, msgs[-1].message_id, reply_markup=kb)
            else:
                await bot.send_message(uid, m["text"], parse_mode="MarkdownV2", reply_markup=kb)

        except:
            continue

    await state.clear()
    await q.message.answer("✅ <b>Рассылка завершена</b>", parse_mode="HTML")
    await q.answer()


@router.callback_query(F.data == "cancel_mailing")
async def cancel(q: CallbackQuery, state: FSMContext):
    await state.clear()
    await q.message.answer("❌ Рассылка отменена", parse_mode="HTML")
    await q.answer()
