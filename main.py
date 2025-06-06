import re
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 🔹 Credentials & Config
api_id = 23171051
api_hash = "10331d5d712364f57ffdd23417f4513c"
BOT_TOKEN = "7674047505:AAE4A4GwREYoQ9i5T_JX0jxAqec4grp-39g"

destination_channel = -1002624205281 # ✅ Replace with your channel ID 
admin_id = 123456789                   # ✅ Replace with your Telegram user ID

# 🔴 Blacklist Keywords (add more if needed)
blacklist_keywords = ["deposit", "contact", "whatsapp", "upi", "payment", "telegram", "join"]

# Initialize Clients
userbot = TelegramClient("session", api_id, api_hash)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
media_queue = asyncio.Queue()

async def ensure_userbot_auth():
    await userbot.connect()
    if not await userbot.is_user_authorized():
        logger.warning("🔐 Userbot not authorized, trying to log in...")
        await userbot.start()

async def get_joined_channels():
    dialogs = await userbot.get_dialogs()
    joined = [dialog.id for dialog in dialogs if dialog.is_channel and not dialog.is_user]
    logger.info(f"✅ Joined channels: {joined}")
    return joined

@userbot.on(events.NewMessage())
async def queue_media(event):
    joined_channels = await get_joined_channels()
    if event.chat_id in joined_channels:
        text = (event.message.text or "").lower()
        if any(keyword in text for keyword in blacklist_keywords):
            logger.warning(f"🚫 Skipped blacklisted message in {event.chat.title}")
            return
        if event.message.media or event.message.text:
            await media_queue.put(event.message)
            logger.info(f"📥 Queued message from {event.chat.title}")

async def fetch_unread_media():
    joined_channels = await get_joined_channels()
    for channel_id in joined_channels:
        async for message in userbot.iter_messages(channel_id, limit=50, reverse=True):
            text = (message.text or "").lower()
            if any(keyword in text for keyword in blacklist_keywords):
                continue
            if message.media or message.text:
                await media_queue.put(message)
                logger.info(f"📥 (Restart) Queued message from {channel_id}")

async def process_media_queue():
    while True:
        message = await media_queue.get()
        logger.info("⏳ Processing next message...")
        try:
            await forward_media(message)
            logger.info("✅ Forwarded successfully")
        except FloodWaitError as e:
            logger.warning(f"😴 Flood wait for {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
            await forward_media(message)
        except Exception as e:
            logger.error(f"❌ Error: {e}")
        media_queue.task_done()
        await asyncio.sleep(2)

async def forward_media(message):
    try:
        new_caption = re.sub(r"@\w+", "", message.text or "").strip()
        new_caption = re.sub(r"https?://\S+", ".", new_caption) 

        sent = await userbot.send_message(
            destination_channel,
            new_caption,
            file=message.media if message.media else None
        )

        await notify_admin(message.chat.title, sent.id)
        await userbot.send_read_acknowledge(message.chat_id, message=message)

    except Exception as e:
        logger.error(f"⚠️ forward_media error: {e}")

async def notify_admin(source_chat, msg_id):
    try:
        link = f"https://t.me/c/{str(destination_channel)[4:]}/{msg_id}"
        notify_text = (
            f"📢 <b>Forwarded from:</b> {source_chat}\n"
            f"🔗 <a href='{link}'>View in Channel</a>"
        )
        await bot.send_message(admin_id, notify_text, disable_web_page_preview=True)
        logger.info("📨 Admin notified")
    except Exception as e:
        logger.error(f"⚠️ notify_admin error: {e}")

async def main():
    await ensure_userbot_auth()
    logger.info("🤖 Userbot Running...")
    await fetch_unread_media()
    asyncio.create_task(process_media_queue())
    await userbot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped gracefully.")
