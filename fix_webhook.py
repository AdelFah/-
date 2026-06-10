import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv(override=True)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def fix():
    bot = Bot(TOKEN)
    info = await bot.get_webhook_info()
    print(f"Вебхук: {info.url}")
    if info.url:
        await bot.delete_webhook()
        print("✅ Вебхук удалён")
    else:
        print("Вебхука нет")
    me = await bot.get_me()
    print(f"Бот: @{me.username} ({me.first_name})")

asyncio.run(fix())
