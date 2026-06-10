from sqlalchemy import select, and_
from datetime import datetime, date
from bot.models.database import Note, SessionLocal


async def get_note_today(user_id: int) -> Note | None:
    today = date.today().strftime("%Y-%m-%d")
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).where(and_(Note.user_id == user_id, Note.date == today))
        )
        return result.scalar_one_or_none()


async def get_note_by_date(user_id: int, date_str: str) -> Note | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).where(and_(Note.user_id == user_id, Note.date == date_str))
        )
        return result.scalar_one_or_none()


async def save_note(user_id: int, text: str) -> Note:
    today = date.today().strftime("%Y-%m-%d")
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).where(and_(Note.user_id == user_id, Note.date == today))
        )
        note = result.scalar_one_or_none()
        if note:
            note.text = text
            note.updated_at = datetime.now()
        else:
            note = Note(user_id=user_id, date=today, text=text)
            session.add(note)
        await session.commit()
        await session.refresh(note)
        return note


async def append_note(user_id: int, text: str) -> Note:
    today = date.today().strftime("%Y-%m-%d")
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).where(and_(Note.user_id == user_id, Note.date == today))
        )
        note = result.scalar_one_or_none()
        if note:
            note.text = note.text + "\n\n" + text
            note.updated_at = datetime.now()
        else:
            note = Note(user_id=user_id, date=today, text=text)
            session.add(note)
        await session.commit()
        await session.refresh(note)
        return note


async def delete_note(user_id: int) -> bool:
    today = date.today().strftime("%Y-%m-%d")
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).where(and_(Note.user_id == user_id, Note.date == today))
        )
        note = result.scalar_one_or_none()
        if note:
            await session.delete(note)
            await session.commit()
            return True
        return False


async def get_recent_notes(user_id: int, limit: int = 7) -> list[Note]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).where(Note.user_id == user_id)
            .order_by(Note.date.desc())
            .limit(limit)
        )
        return result.scalars().all()
