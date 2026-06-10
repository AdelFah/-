from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from bot.ai.claude_ai import process_message, analyze_schedule
from bot.services.task_service import (
    create_task, complete_task, delete_task, reschedule_task,
    get_tasks_today, get_tasks_week, get_pending_tasks, format_task,
    get_or_create_user,
)
from bot.keyboards.main_keyboard import main_menu_keyboard, task_action_keyboard
from bot.handlers.note_handler import show_notes_menu, handle_note_input


def _parse_datetime_natural(text: str) -> datetime | None:
    from datetime import date, timedelta
    import re
    now = datetime.now()
    text = text.lower().strip()

    time_match = re.search(r'(\d{1,2})[:\.](\d{2})', text)
    if not time_match:
        return None
    hour, minute = int(time_match.group(1)), int(time_match.group(2))

    if "послезавтра" in text:
        base = now + timedelta(days=2)
    elif "завтра" in text:
        base = now + timedelta(days=1)
    else:
        date_match = re.search(r'(\d{1,2})[./](\d{1,2})', text)
        if date_match:
            day, month = int(date_match.group(1)), int(date_match.group(2))
            try:
                base = datetime(now.year, month, day)
            except ValueError:
                base = now
        else:
            base = now

    try:
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return None


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m %H:%M"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            if fmt in ("%d.%m %H:%M",):
                dt = dt.replace(year=datetime.now().year)
            return dt
        except ValueError:
            continue
    return None


async def process_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user = update.effective_user

    # Кнопки меню — обрабатываем без AI
    if user_text == "📅 Сегодня":
        from bot.handlers.task_handler import show_today
        return await show_today(update, context)
    if user_text == "📆 Неделя":
        from bot.handlers.task_handler import show_week
        return await show_week(update, context)
    if user_text == "📋 Все задачи":
        from bot.handlers.task_handler import show_pending
        return await show_pending(update, context)
    if user_text == "📊 Аналитика":
        return await handle_analytics(update, context)
    if user_text == "➕ Добавить задачу":
        await update.message.reply_text(
            "Опиши задачу — например:\n"
            "_«Помыть посуду сегодня в 18:00»_\n"
            "_«Встреча с клиентом завтра в 10:00 высокий приоритет»_\n"
            "_«Тренировка в пятницу в 7:00, напомни за 30 минут»_",
            parse_mode="Markdown",
        )
        return
    if user_text == "📓 Заметки":
        return await show_notes_menu(update, context)
    if user_text == "🤖 Спросить ИИ":
        await update.message.reply_text(
            "🤖 Задай мне любой вопрос о твоём расписании или попроси совета!\n\n"
            "Например:\n"
            "_«Как оптимизировать мой день?»_\n"
            "_«Найди свободное время для тренировки»_\n"
            "_«Проанализируй мою неделю»_",
            parse_mode="Markdown",
        )
        return

    # Получаем историю диалога из context
    if "history" not in context.user_data:
        context.user_data["history"] = []

    # Проверяем режим ввода заметки
    if await handle_note_input(update, context):
        return

    # Проверяем режим переноса задачи
    if "reschedule_task_id" in context.user_data:
        task_id = context.user_data.pop("reschedule_task_id")
        from bot.services.task_service import reschedule_task
        new_time = _parse_datetime_natural(user_text)
        if new_time:
            success = await reschedule_task(task_id, user.id, new_time)
            if success:
                await update.message.reply_text(
                    f"🔄 Задача #{task_id} перенесена на *{new_time.strftime('%d.%m %H:%M')}*",
                    parse_mode="Markdown", reply_markup=main_menu_keyboard()
                )
            else:
                await update.message.reply_text("❌ Задача не найдена.")
        else:
            await update.message.reply_text(
                "❌ Не понял время. Напиши например: _«завтра в 15:00»_ или _«12.06 в 10:30»_",
                parse_mode="Markdown"
            )
        return

    await update.message.chat.send_action("typing")

    try:
        result = await process_message(user_text, context.user_data["history"])
    except Exception as e:
        print(f"[ОШИБКА AI]: {e}")
        await update.message.reply_text(f"⚠️ Ошибка: {e}")
        return

    # Обновляем историю (храним последние 10 сообщений)
    context.user_data["history"].append({"role": "user", "content": user_text})
    if result.get("message"):
        context.user_data["history"].append({"role": "assistant", "content": result.get("message", "")})
    if len(context.user_data["history"]) > 20:
        context.user_data["history"] = context.user_data["history"][-20:]

    action = result.get("action", "chat")

    if action == "create_task":
        task_data = result.get("task", {})
        task = await create_task(
            user_id=user.id,
            title=task_data.get("title", user_text),
            category=task_data.get("category", "личные"),
            scheduled_at=_parse_datetime(task_data.get("scheduled_at")),
            deadline_at=_parse_datetime(task_data.get("deadline_at")),
            priority=task_data.get("priority", "medium"),
            description=task_data.get("description"),
            reminder_minutes=task_data.get("reminder_minutes"),
        )
        reply = result.get("message", f"✅ Задача создана!")
        reply += f"\n\n{format_task(task)}"
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=task_action_keyboard(task.id),
        )

    elif action == "show_today":
        from bot.handlers.task_handler import show_today
        await show_today(update, context)

    elif action == "show_week":
        from bot.handlers.task_handler import show_week
        await show_week(update, context)

    elif action == "show_pending":
        from bot.handlers.task_handler import show_pending
        await show_pending(update, context)

    elif action == "complete_task":
        task_id = result.get("task_id")
        if task_id:
            success = await complete_task(int(task_id), user.id)
            msg = result.get("message", f"✅ Задача #{task_id} выполнена!" if success else "❌ Задача не найдена.")
        else:
            msg = result.get("message", "Укажи номер задачи. Например: «Выполни задачу #5»")
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif action == "delete_task":
        task_id = result.get("task_id")
        if task_id:
            success = await delete_task(int(task_id), user.id)
            msg = result.get("message", f"🗑 Задача #{task_id} удалена." if success else "❌ Задача не найдена.")
        else:
            msg = result.get("message", "Укажи номер задачи.")
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif action == "reschedule_task":
        task_id = result.get("task_id")
        new_time = _parse_datetime(result.get("new_time"))
        if task_id and new_time:
            success = await reschedule_task(int(task_id), user.id, new_time)
            msg = result.get("message", f"🔄 Задача #{task_id} перенесена на {new_time.strftime('%d.%m %H:%M')}." if success else "❌ Задача не найдена.")
        else:
            msg = result.get("message", "Укажи номер задачи и новое время.")
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif action == "analyze":
        tasks_today = await get_tasks_today(user.id)
        tasks_week = await get_tasks_week(user.id)
        analysis = await analyze_schedule(tasks_today, tasks_week)
        await update.message.reply_text(f"🤖 *Анализ расписания:*\n\n{analysis}", parse_mode="Markdown")

    else:
        msg = result.get("message", "Понял! Чем ещё помочь?")
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        print(f"[LOG] Сообщение от {user.id}: {update.message.text}")
        await get_or_create_user(user.id, user.full_name)
    except Exception as e:
        print(f"[ОШИБКА init]: {e}")
        await update.message.reply_text(f"⚠️ Ошибка инициализации: {e}")
        return
    await process_user_text(update, context, update.message.text)


async def handle_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.chat.send_action("typing")

    from bot.services.task_service import get_stats, get_pending_tasks, CATEGORY_EMOJI
    from bot.services.task_service import get_tasks_today, get_tasks_week

    stats = await get_stats(user_id)
    tasks_today = await get_tasks_today(user_id)
    tasks_week = await get_tasks_week(user_id)
    pending = await get_pending_tasks(user_id)

    total = stats["total"]
    done = stats["done"]
    p = stats["pending"]
    pct = round(done / total * 100) if total > 0 else 0
    bar = "🟩" * (pct // 10) + "⬜" * (10 - pct // 10)

    # Статистика по категориям
    cat_count = {}
    for task in pending:
        cat_count[task.category] = cat_count.get(task.category, 0) + 1

    lines = [
        "📊 *Аналитика твоего планировщика*\n",
        f"📌 Всего задач: {total}",
        f"✅ Выполнено: {done}",
        f"⏳ Осталось: {p}",
        f"📈 Прогресс: {pct}%",
        f"{bar}\n",
    ]

    if tasks_today:
        done_today = sum(1 for t in tasks_today if t.status == "done")
        lines.append(f"📅 *Сегодня:* {len(tasks_today)} задач, выполнено {done_today}\n")

    if tasks_week:
        lines.append(f"📆 *На неделю:* {len(tasks_week)} задач\n")

    if cat_count:
        lines.append("📂 *По категориям (невыполненные):*")
        for cat, cnt in sorted(cat_count.items(), key=lambda x: -x[1]):
            emoji = CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"  {emoji} {cat.capitalize()}: {cnt}")
        lines.append("")

    # Советы
    if p == 0:
        lines.append("🎉 Все задачи выполнены! Отличная работа!")
    elif p > 10:
        lines.append("⚠️ *Совет:* Много невыполненных задач. Попробуй расставить приоритеты!")
    elif pct >= 70:
        lines.append("💪 *Отлично!* Ты выполняешь большинство задач. Так держать!")
    else:
        lines.append("📝 *Совет:* Добавь задачи на неделю чтобы лучше планировать время.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
