from telegram import Update
from telegram.ext import ContextTypes
from bot.services.task_service import get_or_create_user
from bot.keyboards.main_keyboard import main_menu_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_or_create_user(user.id, user.full_name)

    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я — твой ИИ-ассистент для планирования задач.\n\n"
        "Что я умею:\n"
        "📅 Планировать день и неделю\n"
        "✅ Управлять задачами\n"
        "🔔 Напоминать о важных делах\n"
        "🤖 Давать советы по продуктивности\n\n"
        "Просто напиши мне что нужно сделать — например:\n"
        "_«Добавь задачу помыть посуду сегодня в 18:00»_\n"
        "_«Напомни о тренировке завтра в 7:00»_\n"
        "_«Покажи задачи на сегодня»_"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Как пользоваться ботом:*\n\n"
        "*Кнопки меню:*\n"
        "📅 Сегодня — задачи на сегодня\n"
        "📆 Неделя — задачи на неделю\n"
        "➕ Добавить задачу — создать новую задачу\n"
        "📋 Все задачи — список невыполненных\n"
        "🤖 Спросить ИИ — совет по расписанию\n"
        "📊 Аналитика — анализ продуктивности\n\n"
        "*Примеры команд:*\n"
        "• Добавь задачу «сходить в магазин» сегодня в 17:00\n"
        "• Напомни о встрече завтра в 10:00 за 30 минут\n"
        "• Покажи невыполненные задачи\n"
        "• Выполни задачу #5\n"
        "• Перенеси задачу #3 на завтра в 15:00\n"
        "• Проанализируй моё расписание"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
