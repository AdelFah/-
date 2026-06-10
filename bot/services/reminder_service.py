from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from bot.services.task_service import (
    get_tasks_pending_reminders, mark_reminder_sent,
    CATEGORY_EMOJI, PRIORITY_EMOJI,
)
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from bot.models.database import Task, User, SessionLocal


async def check_reminders(bot: Bot):
    tasks = await get_tasks_pending_reminders()
    for task in tasks:
        # Получаем telegram_id пользователя
        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == task.user_id)
            )
            # user_id в Task — это telegram_id
            user = result.scalar_one_or_none()

        cat_emoji = CATEGORY_EMOJI.get(task.category, "📌")
        time_str = task.scheduled_at.strftime("%H:%M") if task.scheduled_at else ""

        text = (
            f"🔔 *Напоминание!*\n\n"
            f"{cat_emoji} *{task.title}*\n"
            f"🕐 Начало в {time_str}\n"
            f"⏰ Через {task.reminder_minutes} мин."
        )

        try:
            await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown")
            await mark_reminder_sent(task.id)
        except Exception as e:
            print(f"Ошибка отправки напоминания для задачи {task.id}: {e}")


async def check_deadlines(bot: Bot):
    async with SessionLocal() as session:
        now = datetime.utcnow()
        soon = now + timedelta(hours=1)
        result = await session.execute(
            select(Task).where(
                and_(
                    Task.status == "pending",
                    Task.deadline_at.isnot(None),
                    Task.deadline_at >= now,
                    Task.deadline_at <= soon,
                )
            )
        )
        tasks = result.scalars().all()

    for task in tasks:
        minutes_left = int((task.deadline_at - datetime.utcnow()).total_seconds() / 60)
        text = (
            f"⚠️ *Дедлайн приближается!*\n\n"
            f"📌 *{task.title}*\n"
            f"🕐 Дедлайн: {task.deadline_at.strftime('%d.%m %H:%M')}\n"
            f"⏳ Осталось: {minutes_left} мин."
        )
        try:
            await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка уведомления о дедлайне {task.id}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, "interval", minutes=1, args=[bot])
    scheduler.add_job(check_deadlines, "interval", minutes=5, args=[bot])
    return scheduler
