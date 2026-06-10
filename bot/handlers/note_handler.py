from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import date
from bot.services.note_service import (
    get_note_today, save_note, append_note,
    delete_note, get_recent_notes,
)
from bot.keyboards.main_keyboard import main_menu_keyboard


async def show_notes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = await get_note_today(update.effective_user.id)
    today = date.today().strftime("%d.%m.%Y")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Написать заметку", callback_data="note_write")],
        [InlineKeyboardButton("➕ Добавить к заметке", callback_data="note_append")],
        [InlineKeyboardButton("🗑 Удалить заметку", callback_data="note_delete")],
        [InlineKeyboardButton("📚 Последние 7 дней", callback_data="note_history")],
    ])

    if note:
        text = (
            f"📓 *Заметка на сегодня* ({today}):\n\n"
            f"{note.text}\n\n"
            f"_Обновлено: {note.updated_at.strftime('%H:%M')}_"
        )
    else:
        text = (
            f"📓 *Заметки* — {today}\n\n"
            f"На сегодня заметок нет.\n"
            f"Напиши свои мысли, планы или важную информацию о дне!"
        )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_note_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "note_write":
        context.user_data["note_mode"] = "write"
        await query.edit_message_text(
            "✏️ *Напиши свою заметку:*\n\n"
            "Отправь текст — он заменит текущую заметку на сегодня.",
            parse_mode="Markdown"
        )

    elif data == "note_append":
        context.user_data["note_mode"] = "append"
        await query.edit_message_text(
            "➕ *Добавить к заметке:*\n\n"
            "Отправь текст — он добавится к текущей заметке.",
            parse_mode="Markdown"
        )

    elif data == "note_delete":
        success = await delete_note(user_id)
        msg = "🗑 Заметка удалена." if success else "Заметки на сегодня нет."
        await query.edit_message_text(msg)

    elif data == "voice_to_note":
        text = context.user_data.get("last_voice_text")
        if not text:
            await query.edit_message_text("❌ Текст голосового не найден.")
            return
        await save_note(user_id, text)
        await query.edit_message_text(
            f"📓 *Заметка сохранена из голосового!*\n\n{text}",
            parse_mode="Markdown",
        )

    elif data == "voice_append_note":
        text = context.user_data.get("last_voice_text")
        if not text:
            await query.edit_message_text("❌ Текст голосового не найден.")
            return
        note = await append_note(user_id, text)
        await query.edit_message_text(
            f"➕ *Добавлено к заметке из голосового!*\n\n{note.text}",
            parse_mode="Markdown",
        )

    elif data == "note_history":
        notes = await get_recent_notes(user_id)
        if not notes:
            await query.edit_message_text("📚 Заметок пока нет.")
            return
        lines = ["📚 *Заметки за последние дни:*\n"]
        for note in notes:
            try:
                from datetime import datetime
                d = datetime.strptime(note.date, "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                d = note.date
            preview = note.text[:80] + "..." if len(note.text) > 80 else note.text
            lines.append(f"📅 *{d}*\n{preview}\n")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")


async def handle_note_input(update: Update, context: ContextTypes.DEFAULT_TYPE, voice_text: str = None) -> bool:
    mode = context.user_data.get("note_mode")
    if not mode:
        return False

    user_id = update.effective_user.id
    text = voice_text or update.message.text
    if not text:
        return False
    context.user_data.pop("note_mode")

    if mode == "write":
        await save_note(user_id, text)
        await update.message.reply_text(
            f"📓 *Заметка сохранена!*\n\n{text}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    elif mode == "append":
        note = await append_note(user_id, text)
        await update.message.reply_text(
            f"➕ *Добавлено к заметке!*\n\n{note.text}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    return True
