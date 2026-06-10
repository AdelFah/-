from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from bot.models.database import Task, SessionLocal
from bot.services.task_service import CATEGORY_EMOJI
import pytz

TZ = pytz.timezone("Asia/Yekaterinburg")


def _task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Выполнено", callback_data=f"done_{task_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{task_id}"),
        ],
        [
            InlineKeyboardButton("🔄 Перенести", callback_data=f"move_{task_id}"),
            InlineKeyboardButton("✏️ Переименовать", callback_data=f"rename_{task_id}"),
        ],
    ])


def now_local() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


async def check_reminders(bot: Bot):
    now = now_local()

    async with SessionLocal() as session:
        # 1. Напоминание за X минут до scheduled_at
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
        for task in result.scalars().all():
            remind_at = task.scheduled_at - timedelta(minutes=task.reminder_minutes)
            if remind_at <= now:
                cat_emoji = CATEGORY_EMOJI.get(task.category, "📌")
                text = (
                    f"🔔 *Напоминание!*\n\n"
                    f"{cat_emoji} *{task.title}*\n"
                    f"🕐 Начало в {task.scheduled_at.strftime('%H:%M')}\n"
                    f"⏰ Через {task.reminder_minutes} мин."
                )
                try:
                    await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown", reply_markup=_task_keyboard(task.id))
                    task.reminder_sent = True
                except Exception as e:
                    print(f"[ОШИБКА напоминания] задача {task.id}: {e}")

        # 2. Уведомление в момент scheduled_at (если reminder_minutes не задан)
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
        for task in result2.scalars().all():
            cat_emoji = CATEGORY_EMOJI.get(task.category, "📌")
            text = (
                f"⏰ *Пора!*\n\n"
                f"{cat_emoji} *{task.title}*\n"
                f"🕐 Запланировано на {task.scheduled_at.strftime('%H:%M')}"
            )
            try:
                await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown", reply_markup=_task_keyboard(task.id))
                task.reminder_sent = True
            except Exception as e:
                print(f"[ОШИБКА уведомления] задача {task.id}: {e}")

        # 3. Уведомление в момент дедлайна
        result3 = await session.execute(
            select(Task).where(
                and_(
                    Task.status == "pending",
                    Task.deadline_notified == False,
                    Task.deadline_at.isnot(None),
                    Task.deadline_at <= now,
                )
            )
        )
        for task in result3.scalars().all():
            cat_emoji = CATEGORY_EMOJI.get(task.category, "📌")
            text = (
                f"🚨 *Дедлайн!*\n\n"
                f"{cat_emoji} *{task.title}*\n"
                f"⚠️ Срок сдачи истёк в {task.deadline_at.strftime('%d.%m %H:%M')}\n"
                f"Задача ещё не выполнена!"
            )
            try:
                await bot.send_message(chat_id=task.user_id, text=text, parse_mode="Markdown", reply_markup=_task_keyboard(task.id))
                task.deadline_notified = True
            except Exception as e:
                print(f"[ОШИБКА дедлайна] задача {task.id}: {e}")

        await session.commit()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, "interval", minutes=1, args=[bot])
    return scheduler
