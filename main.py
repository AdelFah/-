import asyncio
import os
from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.models.database import init_db
from bot.handlers.start_handler import start_command, help_command
from bot.handlers.task_handler import handle_task_callback
from bot.handlers.note_handler import handle_note_callback
from bot.handlers.ai_handler import handle_ai_message
from bot.services.reminder_service import setup_scheduler

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def post_init(application: Application):
    await init_db()
    scheduler = setup_scheduler(application.bot)
    scheduler.start()
    try:
        await application.bot.set_my_commands([
            BotCommand("start", "Запустить бота"),
            BotCommand("help", "Помощь и список команд"),
        ])
    except Exception as e:
        print(f"⚠️ Не удалось установить команды: {e}")
    print("✅ База данных инициализирована")
    print("✅ Планировщик напоминаний запущен")
    print("✅ Бот запущен!")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env файле!")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_note_callback, pattern="^note_"))
    app.add_handler(CallbackQueryHandler(handle_task_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_message))

    print("🚀 Запуск AI-планировщика...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
