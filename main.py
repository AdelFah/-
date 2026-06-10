import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, *args):
            pass
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан!")

    # HTTP сервер запускаем первым — Render должен увидеть порт
    threading.Thread(target=run_health_server, daemon=True).start()
    print("✅ Health server запущен")

    await init_db()
    from bot.services.history_service import clear_old_history
    await clear_old_history(days=7)

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
