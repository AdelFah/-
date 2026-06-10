import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv(override=True)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"✅ Получено сообщение: {update.message.text}")
    await update.message.reply_text(f"Эхо: {update.message.text}")

app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, echo))
print("🚀 Тест запущен. Напиши боту что-нибудь...")
app.run_polling(drop_pending_updates=True)
