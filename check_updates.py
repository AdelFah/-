import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv(override=True)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def check():
    bot = Bot(TOKEN)
    print("Жду сообщений 30 секунд... Напиши боту в Telegram прямо сейчас!")
    updates = await bot.get_updates(timeout=30, limit=5)
    if updates:
        for u in updates:
            print(f"✅ Сообщение: {u.message.text if u.message else 'не текст'} от {u.message.from_user.id if u.message else '?'}")
    else:
        print("❌ Сообщений не получено за 30 секунд")

asyncio.run(check())
