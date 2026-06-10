from sqlalchemy import select, delete
from datetime import datetime, timedelta
from bot.models.database import ChatHistory, SessionLocal


async def save_message(user_id: int, role: str, content: str):
    async with SessionLocal() as session:
        msg = ChatHistory(user_id=user_id, role=role, content=content)
        session.add(msg)
        await session.commit()


async def get_history(user_id: int, days: int = 7, limit: int = 30) -> list[dict]:
    since = datetime.now() - timedelta(days=days)
    async with SessionLocal() as session:
        result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id, ChatHistory.created_at >= since)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        # Возвращаем в хронологическом порядке
        return [{"role": r.role, "content": r.content} for r in reversed(rows)]


async def clear_old_history(days: int = 7):
    cutoff = datetime.now() - timedelta(days=days)
    async with SessionLocal() as session:
        await session.execute(
            delete(ChatHistory).where(ChatHistory.created_at < cutoff)
        )
        await session.commit()
