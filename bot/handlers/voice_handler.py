from telegram import Update
from telegram.ext import ContextTypes
from groq import AsyncGroq
from dotenv import load_dotenv
import os
import tempfile

load_dotenv(override=True)


async def transcribe_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    voice = update.message.voice or update.message.audio
    if not voice:
        return None

    try:
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await file.download_to_drive(tmp_path)

        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

        with open(tmp_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                file=("voice.ogg", audio_file),
                model="whisper-large-v3-turbo",
                language="ru",
            )

        os.unlink(tmp_path)
        return transcription.text.strip()

    except Exception as e:
        print(f"[ОШИБКА транскрибации]: {e}")
        return None


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙 Распознаю голосовое...")

    text = await transcribe_voice(update, context)

    if not text:
        await update.message.reply_text("❌ Не удалось распознать голосовое сообщение.")
        return

    await update.message.reply_text(f"🎙 Распознано: _{text}_", parse_mode="Markdown")

    # Обрабатываем как обычное текстовое сообщение
    update.message.text = text
    from bot.handlers.ai_handler import handle_ai_message
    await handle_ai_message(update, context)
