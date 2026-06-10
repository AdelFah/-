from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from bot.models.database import Task, SessionLocal
from bot.services.task_service import CATEGORY_EMOJI
import pytz

TZ = pytz.timezone("Asia/Yekaterinburg")


def now_local() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


async def check_reminders(bot: Bot):
    now = now_local()

    async with SessionLocal() as session:
        # Уведомления за X минут до задачи
        result = await session.execute(
            select(Task).where(
                and_(
                    Task.status == "pending",
                    Task.reminder_minutes.isnot(None),
                    Task.reminder_sent == False,
                    Task.scheduled_at.isnot(None),
                )
            )
        )
        tasks_with_reminder = result.scalars().all()

        for task in tasks_with_reminder:
            remind_at = task.scheduled_at - timedelta(minutes=task.reminder_minutes)
            if remind_at <= now:
                cat_emoji = CATEGORY_EMOJI.get(task.category, "📌")
                time_str = task.scheduled_at.strftime("%H:%M")
                text = (
                    f"🔔 *Напоминание!*\n\n"
                    f"{cat_emoji} *{task.title}*\n"
                    f"🕐 Начало в {time_str}\n"
                    f"⏰ Через {task.reminder_minutes} мин."
                )
                try:
                    await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown")
                    task.reminder_sent = True
                except Exception as e:
                    print(f"[ОШИБКА напоминания] задача {task.id}: {e}")

        # Уведомление в момент задачи (если reminder_minutes не задан)
        result2 = await session.execute(
            select(Task).where(
                and_(
                    Task.status == "pending",
                    Task.reminder_minutes.is_(None),
                    Task.reminder_sent == False,
                    Task.scheduled_at.isnot(None),
                    Task.scheduled_at <= now,
                )
            )
        )
        tasks_at_time = result2.scalars().all()

        for task in tasks_at_time:
            cat_emoji = CATEGORY_EMOJI.get(task.category, "📌")
            time_str = task.scheduled_at.strftime("%H:%M")
            text = (
                f"⏰ *Пора!*\n\n"
                f"{cat_emoji} *{task.title}*\n"
                f"🕐 Запланировано на {time_str}"
            )
            try:
                await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown")
                task.reminder_sent = True
            except Exception as e:
                print(f"[ОШИБКА уведомления] задача {task.id}: {e}")

        await session.commit()


async def check_deadlines(bot: Bot):
    async with SessionLocal() as session:
        now = now_local()
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
        minutes_left = int((task.deadline_at - datetime.now()).total_seconds() / 60)
        text = (
            f"⚠️ *Дедлайн приближается!*\n\n"
            f"📌 *{task.title}*\n"
            f"🕐 Дедлайн: {task.deadline_at.strftime('%d.%m %H:%M')}\n"
            f"⏳ Осталось: {minutes_left} мин."
        )
        try:
            await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown")
        except Exception as e:
            print(f"[ОШИБКА дедлайна] задача {task.id}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, "interval", minutes=1, args=[bot])
    scheduler.add_job(check_deadlines, "interval", minutes=5, args=[bot])
    return scheduler
