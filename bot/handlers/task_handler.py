from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from bot.services.task_service import (
    get_tasks_today, get_tasks_week, get_pending_tasks,
    complete_task, delete_task, reschedule_task, rename_task,
    delete_all_tasks, delete_today_tasks, update_task_priority, update_task_category,
    format_task, get_stats, get_task_by_id, PRIORITY_LABEL, CATEGORY_EMOJI,
)
from bot.keyboards.main_keyboard import task_action_keyboard, tasks_list_keyboard, priority_keyboard, category_keyboard

DAYS_RU = {
    "Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда",
    "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"
}


def tasks_keyboard(tasks: list, show_delete_today: bool = False, show_delete_all: bool = False) -> InlineKeyboardMarkup:
    keyboard = []
    for task in tasks[:10]:
        status = "✅" if task.status == "done" else "⏳"
        display_num = task.task_number if task.task_number is not None else task.id
        keyboard.append([
            InlineKeyboardButton(
                f"{status} #{display_num} {task.title[:28]}",
                callback_data=f"task_{task.id}"
            )
        ])
    if show_delete_today:
        keyboard.append([
            InlineKeyboardButton("🗑 Удалить все задачи на сегодня", callback_data="confirm_del_today")
        ])
    if show_delete_all:
        keyboard.append([
            InlineKeyboardButton("🗑 Удалить все задачи", callback_data="confirm_del_all")
        ])
    return InlineKeyboardMarkup(keyboard)


async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = await get_tasks_today(user_id)

    if not tasks:
        await update.message.reply_text(
            "📅 На сегодня задач нет.\n\nНапиши мне что запланировать — например:\n«Добавь задачу прогулка в 18:00»"
        )
        return

    lines = [f"📅 *Задачи на сегодня* ({len(tasks)} шт.):\n"]
    for task in tasks:
        lines.append(format_task(task))
        lines.append("")
    lines.append("👇 Выбери задачу для управления:")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=tasks_keyboard(tasks, show_delete_today=True),
    )


async def show_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = await get_tasks_week(user_id)

    if not tasks:
        await update.message.reply_text("📆 На эту неделю задач нет.")
        return

    by_day = {}
    day_sort_key = {}
    for task in tasks:
        if task.scheduled_at:
            day_en = task.scheduled_at.strftime("%A")
            day_ru = DAYS_RU.get(day_en, day_en)
            day = task.scheduled_at.strftime("%d.%m ") + day_ru
            day_sort_key[day] = task.scheduled_at.date()
        else:
            day = "Без времени"
            day_sort_key[day] = __import__("datetime").date.max
        by_day.setdefault(day, []).append(task)

    by_day = dict(sorted(by_day.items(), key=lambda x: day_sort_key[x[0]]))

    lines = [f"📆 *Задачи на неделю* ({len(tasks)} шт.):\n"]
    for day, day_tasks in by_day.items():
        lines.append(f"*{day}*")
        for task in day_tasks:
            time_str = task.scheduled_at.strftime("%H:%M") if task.scheduled_at else "──"
            display_num = task.task_number if task.task_number is not None else task.id
            lines.append(f"  🕐 {time_str} — {task.title} [{task.category}] #{display_num}")
        lines.append("")
    lines.append("👇 Выбери задачу для управления:")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=tasks_keyboard(tasks),
    )


async def show_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = await get_pending_tasks(user_id)

    if not tasks:
        await update.message.reply_text("🎉 Все задачи выполнены! Отличная работа!")
        return

    lines = [f"📋 *Невыполненные задачи* ({len(tasks)} шт.):\n"]
    for task in tasks[:15]:
        lines.append(format_task(task))
        lines.append("")
    lines.append("👇 Выбери задачу для управления:")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=tasks_keyboard(tasks, show_delete_all=True),
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = await get_stats(user_id)

    total = stats["total"]
    done = stats["done"]
    pending = stats["pending"]
    pct = round(done / total * 100) if total > 0 else 0

    bar_filled = pct // 10
    bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)

    text = (
        f"📊 *Твоя статистика:*\n\n"
        f"📌 Всего задач: {total}\n"
        f"✅ Выполнено: {done}\n"
        f"⏳ В ожидании: {pending}\n\n"
        f"Прогресс: {pct}%\n{bar}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("done_"):
        task_id = int(data.split("_")[1])
        success = await complete_task(task_id, user_id)
        msg = f"✅ Задача #{task_id} выполнена! Молодец!" if success else "❌ Задача не найдена."
        await query.edit_message_text(msg)

    elif data.startswith("del_"):
        task_id = int(data.split("_")[1])
        success = await delete_task(task_id, user_id)
        msg = f"🗑 Задача #{task_id} удалена." if success else "❌ Задача не найдена."
        await query.edit_message_text(msg)

    elif data.startswith("move_"):
        task_id = int(data.split("_")[1])
        task = await get_task_by_id(task_id, user_id)
        if task:
            context.user_data["reschedule_task_id"] = task_id
            await query.edit_message_text(
                f"🔄 *Перенос задачи:* {task.title}\n\n"
                f"Напиши новое время — например:\n"
                f"_«завтра в 15:00»_ или _«12.06 в 10:30»_",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Задача не найдена.")

    elif data.startswith("rename_"):
        task_id = int(data.split("_")[1])
        task = await get_task_by_id(task_id, user_id)
        if task:
            context.user_data["rename_task_id"] = task_id
            await query.edit_message_text(
                f"✏️ *Переименование задачи*\n\n"
                f"Текущее название: _{task.title}_\n\n"
                f"Напиши новое название:",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Задача не найдена.")

    elif data.startswith("task_"):
        task_id = int(data.split("_")[1])
        task = await get_task_by_id(task_id, user_id)
        if task:
            await query.edit_message_text(
                format_task(task),
                parse_mode="Markdown",
                reply_markup=task_action_keyboard(task_id),
            )
        else:
            await query.edit_message_text("❌ Задача не найдена.")

    # --- Подтверждение удаления всех задач на сегодня ---
    elif data == "confirm_del_today":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data="do_del_today"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
            ]
        ])
        await query.edit_message_text(
            "⚠️ *Удалить все задачи на сегодня?*\nЭто действие нельзя отменить.",
            parse_mode="Markdown",
            reply_markup=kb,
        )

    elif data == "do_del_today":
        count = await delete_today_tasks(user_id)
        await query.edit_message_text(
            f"🗑 Удалено задач на сегодня: *{count}*",
            parse_mode="Markdown",
        )

    # --- Подтверждение удаления всех задач ---
    elif data == "confirm_del_all":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, удалить всё", callback_data="do_del_all"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
            ]
        ])
        await query.edit_message_text(
            "⚠️ *Удалить абсолютно все задачи?*\nЭто действие нельзя отменить.",
            parse_mode="Markdown",
            reply_markup=kb,
        )

    elif data == "do_del_all":
        count = await delete_all_tasks(user_id)
        await query.edit_message_text(
            f"🗑 Удалено задач: *{count}*",
            parse_mode="Markdown",
        )

    elif data.startswith("priority_"):
        task_id = int(data.split("_")[1])
        task = await get_task_by_id(task_id, user_id)
        if task:
            await query.edit_message_text(
                f"🎯 *Выбери приоритет для:* _{task.title}_",
                parse_mode="Markdown",
                reply_markup=priority_keyboard(task_id),
            )
        else:
            await query.edit_message_text("❌ Задача не найдена.")

    elif data.startswith("setpri_"):
        parts = data.split("_")
        priority, task_id = parts[1], int(parts[2])
        success = await update_task_priority(task_id, user_id, priority)
        if success:
            task = await get_task_by_id(task_id, user_id)
            await query.edit_message_text(
                f"🎯 Приоритет изменён на *{PRIORITY_LABEL[priority]}*\n\n{format_task(task)}",
                parse_mode="Markdown",
                reply_markup=task_action_keyboard(task_id),
            )
        else:
            await query.edit_message_text("❌ Задача не найдена.")

    elif data.startswith("category_"):
        task_id = int(data.split("_")[1])
        task = await get_task_by_id(task_id, user_id)
        if task:
            await query.edit_message_text(
                f"📂 *Выбери категорию для:* _{task.title}_",
                parse_mode="Markdown",
                reply_markup=category_keyboard(task_id),
            )
        else:
            await query.edit_message_text("❌ Задача не найдена.")

    elif data.startswith("setcat_"):
        parts = data.split("_")
        category, task_id = parts[1], int(parts[2])
        success = await update_task_category(task_id, user_id, category)
        if success:
            task = await get_task_by_id(task_id, user_id)
            emoji = CATEGORY_EMOJI.get(category, "📌")
            await query.edit_message_text(
                f"📂 Категория изменена на *{emoji} {category.capitalize()}*\n\n{format_task(task)}",
                parse_mode="Markdown",
                reply_markup=task_action_keyboard(task_id),
            )
        else:
            await query.edit_message_text("❌ Задача не найдена.")

    elif data == "cancel":
        await query.edit_message_text("Отменено.")
