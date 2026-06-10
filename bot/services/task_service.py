from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
from bot.models.database import Task, User, SessionLocal
import pytz


CATEGORIES = ["учёба", "работа", "питание", "спорт", "отдых", "личные", "бытовые"]
CATEGORY_EMOJI = {
    "учёба": "📚",
    "работа": "💼",
    "питание": "🍽",
    "спорт": "🏋️",
    "отдых": "😴",
    "личные": "👤",
    "бытовые": "🏠",
}
PRIORITY_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴"}
PRIORITY_LABEL = {"low": "Низкий", "medium": "Средний", "high": "Высокий"}
STATUS_EMOJI = {"pending": "⏳", "done": "✅", "cancelled": "❌"}


async def get_or_create_user(telegram_id: int, name: str) -> User:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, name=name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def create_task(
    user_id: int,
    title: str,
    category: str = "личные",
    scheduled_at: datetime = None,
    deadline_at: datetime = None,
    priority: str = "medium",
    description: str = None,
    reminder_minutes: int = None,
) -> Task:
    async with SessionLocal() as session:
        task = Task(
            user_id=user_id,
            title=title,
            category=category,
            scheduled_at=scheduled_at,
            deadline_at=deadline_at,
            priority=priority,
            description=description,
            reminder_minutes=reminder_minutes,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def get_tasks_today(user_id: int) -> list[Task]:
    async with SessionLocal() as session:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        result = await session.execute(
            select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.status != "cancelled",
                    Task.scheduled_at >= today_start,
                    Task.scheduled_at < today_end,
                )
            ).order_by(Task.scheduled_at)
        )
        return result.scalars().all()


async def get_tasks_week(user_id: int) -> list[Task]:
    async with SessionLocal() as session:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today_start + timedelta(days=7)
        result = await session.execute(
            select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.status != "cancelled",
                    Task.scheduled_at >= today_start,
                    Task.scheduled_at < week_end,
                )
            ).order_by(Task.scheduled_at)
        )
        return result.scalars().all()


async def get_pending_tasks(user_id: int) -> list[Task]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Task).where(
                and_(Task.user_id == user_id, Task.status == "pending")
            ).order_by(Task.scheduled_at.nulls_last(), Task.created_at)
        )
        return result.scalars().all()


async def get_task_by_id(task_id: int, user_id: int) -> Task | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        return result.scalar_one_or_none()


async def complete_task(task_id: int, user_id: int) -> bool:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "done"
            task.updated_at = datetime.utcnow()
            await session.commit()
            return True
        return False


async def delete_task(task_id: int, user_id: int) -> bool:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "cancelled"
            task.updated_at = datetime.utcnow()
            await session.commit()
            return True
        return False


async def reschedule_task(task_id: int, user_id: int, new_time: datetime) -> bool:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        task = result.scalar_one_or_none()
        if task:
            task.scheduled_at = new_time
            task.updated_at = datetime.utcnow()
            await session.commit()
            return True
        return False


async def get_tasks_pending_reminders() -> list[Task]:
    async with SessionLocal() as session:
        now = datetime.utcnow()
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
        tasks = result.scalars().all()
        due = []
        for task in tasks:
            remind_at = task.scheduled_at - timedelta(minutes=task.reminder_minutes)
            if remind_at <= now:
                due.append(task)
        return due


async def mark_reminder_sent(task_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.reminder_sent = True
            await session.commit()


async def get_stats(user_id: int) -> dict:
    async with SessionLocal() as session:
        total = await session.execute(
            select(func.count()).where(Task.user_id == user_id)
        )
        done = await session.execute(
            select(func.count()).where(and_(Task.user_id == user_id, Task.status == "done"))
        )
        pending = await session.execute(
            select(func.count()).where(and_(Task.user_id == user_id, Task.status == "pending"))
        )
        return {
            "total": total.scalar(),
            "done": done.scalar(),
            "pending": pending.scalar(),
        }


def format_task(task: Task, show_id: bool = True) -> str:
    cat_emoji = CATEGORY_EMOJI.get(task.category, "📌")
    pri_emoji = PRIORITY_EMOJI.get(task.priority, "🟡")
    status_emoji = STATUS_EMOJI.get(task.status, "⏳")

    lines = []
    if show_id:
        lines.append(f"{status_emoji} *#{task.id}* {cat_emoji} {task.title}")
    else:
        lines.append(f"{status_emoji} {cat_emoji} {task.title}")

    if task.scheduled_at:
        lines.append(f"   🕐 {task.scheduled_at.strftime('%d.%m %H:%M')}")
    if task.deadline_at:
        lines.append(f"   ⚠️ Дедлайн: {task.deadline_at.strftime('%d.%m %H:%M')}")
    if task.description:
        lines.append(f"   📝 {task.description}")
    lines.append(f"   {pri_emoji} Приоритет: {PRIORITY_LABEL.get(task.priority, task.priority)}")

    return "\n".join(lines)
