from telethon import TelegramClient, events, types
import asyncio

# =======================
# 🔑 Настройки
# =======================
api_id = 123456       # твой API_ID из my.telegram.org
api_hash = 'API_HASH' # твой API_HASH из my.telegram.org
log_chat_id = 'me'    # куда пересылать сообщения (можно 'me' для себя)

# =======================
# 📦 Клиент
# =======================
client = TelegramClient('userbot_session', api_id, api_hash)

# Хранилище сообщений
messages = {}  # {message_id: {"sender": str, "text": str}}

# =======================
# 📝 Событие: новые сообщения
# =======================
@client.on(events.NewMessage(incoming=True))
async def new_message(event):
    msg = event.message
    sender = await msg.get_sender()
    sender_name = sender.username or sender.first_name or "Unknown"

    messages[msg.id] = {
        "sender": sender_name,
        "text": msg.text or "<Нет текста>"
    }

# =======================
# 🛡 Событие: редактированные сообщения
# =======================
@client.on(events.MessageEdited)
async def message_edited(event):
    msg = event.message
    old = messages.get(msg.id, {"text": "<неизвестно>"})
    new_text = msg.text or "<Нет текста>"
    
    messages[msg.id] = {"sender": old.get("sender", "Unknown"), "text": new_text}
    
    await client.send_message(log_chat_id,
        f"✏️ Сообщение от @{old.get('sender')} было изменено:\n"
        f"Старое: {old.get('text')}\nНовое: {new_text}"
    )

# =======================
# 🗑 Событие: удалённые сообщения
# =======================
@client.on(events.MessageDeleted)
async def message_deleted(event):
    for msg_id in event.deleted_ids:
        info = messages.get(msg_id)
        if info:
            await client.send_message(log_chat_id,
                f"🗑 Сообщение от @{info.get('sender')} было удалено:\n"
                f"{info.get('text')}"
            )
            # Можно удалить из памяти после пересылки
            del messages[msg_id]

# =======================
# 🚀 Запуск
# =======================
async def main():
    print("Userbot запущен. Ловим сообщения...")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
