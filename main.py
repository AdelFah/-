import asyncio
import os
from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.models.database import init_db
from bot.handlers.start_handler import start_command, help_command
from bot.handlers.task_handler import handle_task_callback
from bot.handlers.note_handler import handle_note_callback
from bot.handlers.voice_handler import handle_voice_message
from bot.handlers.ai_handler import handle_ai_message
from bot.services.reminder_service import setup_scheduler

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан!")

    await init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_note_callback, pattern="^note_"))
    app.add_handler(CallbackQueryHandler(handle_task_callback))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_message))

    scheduler = setup_scheduler(app.bot)
    scheduler.start()

    try:
        await app.bot.set_my_commands([
            BotCommand("start", "Запустить бота"),
            BotCommand("help", "Помощь"),
        ])
    except Exception as e:
        print(f"⚠️ Не удалось установить команды: {e}")

    print("✅ База данных инициализирована")
    print("✅ Планировщик запущен")
    print("🚀 Бот запущен!")

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()  # бесконечное ожидание
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
