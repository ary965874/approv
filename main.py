import re
import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Env vars
api_id = 23171051
api_hash = '10331d5d712364f57ffdd23417f4513c'
BOT_TOKEN = '7674047505:AAE4A4GwREYoQ9i5T_JX0jxAqec4grp-39g'
STRING_SESSION = "1BVtsOKEBu6MYzUuezBv_iPMuzTKhOaRTNQVLOtElXWxT-Clr5xAm0abVjlWTDtZPQ-axdUMNug6t6p9ZR0zRrmZcQHUW7AiZnDrJv1ManRu8QxeF3gGz2oMVI5QSnKgTMderc1iPVJEaDd3Mh6bzzTfVMYKMMAsUIuC3XsRVk-qfKNHQ8TGptTx0aurduv4Zne9Z2EOwO-cK-MgjLF9MpfkhPq912_Gtg3wqarVtlsI1YXUu_muuET5jFlRGnx8--091MmbZVyXZTRRb4L4oWu3ow6jiDg82bRynXoMQIhWtfoaMnQYW2Yv1IVncjlQt4TXIIEpH38VtMZT5GZwgHkiJKT3RqcM="

destination_channel = -1002624205281
admin_id = 123456789

# Blacklist filter
blacklist_keywords = ["deposit", "contact", "whatsapp", "upi", "payment", "telegram", "join"]

# Init clients
userbot = TelegramClient(StringSession(STRING_SESSION), api_id, api_hash)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
media_queue = asyncio.Queue()

async def ensure_userbot_auth():
    await userbot.connect()
    if not await userbot.is_user_authorized():
        raise Exception("❌ Authorization failed: Invalid STRING_SESSION")

async def get_joined_channels():
    dialogs = await userbot.get_dialogs()
    return [dialog.id for dialog in dialogs if dialog.is_channel and not dialog.is_user]

@userbot.on(events.NewMessage())
async def handle_new_message(event):
    joined_channels = await get_joined_channels()
    if event.chat_id in joined_channels:
        text = (event.message.text or "").lower()
        if any(keyword in text for keyword in blacklist_keywords):
            return
        if event.message.media or event.message.text:
            await media_queue.put(event.message)
            logger.info(f"📥 Queued message from {event.chat.title}")

async def process_media_queue():
    while True:
        message = await media_queue.get()
        try:
            await forward_media(message)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 5)
            await forward_media(message)
        except Exception as e:
            logger.error(f"❌ Error forwarding: {e}")
        media_queue.task_done()
        await asyncio.sleep(2)

async def forward_media(message):
    try:
        new_caption = re.sub(r"@\w+", "", message.text or "").strip()
        new_caption = re.sub(r"https?://\S+", ".", new_caption)
        sent = await userbot.send_message(destination_channel, new_caption, file=message.media if message.media else None)
        await notify_admin(message.chat.title, sent.id)
        await userbot.send_read_acknowledge(message.chat_id, message=message)
    except Exception as e:
        logger.error(f"⚠️ forward_media error: {e}")

async def notify_admin(source_chat, msg_id):
    try:
        link = f"https://t.me/c/{str(destination_channel)[4:]}/{msg_id}"
        await bot.send_message(admin_id, f"📢 <b>From:</b> {source_chat}\n🔗 <a href='{link}'>View</a>", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"⚠️ notify_admin error: {e}")

async def main():
    await ensure_userbot_auth()
    logger.info("✅ Userbot is running...")
    asyncio.create_task(process_media_queue())
    await userbot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped.")
