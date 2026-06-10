from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL на Supabase/Railway
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Добавляем SSL для Supabase
    if "supabase" in DATABASE_URL and "ssl=" not in DATABASE_URL:
        sep = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL = DATABASE_URL + sep + "ssl=require"
    engine = create_async_engine(DATABASE_URL, echo=False)
else:
    # Локальная SQLite
    os.makedirs("data", exist_ok=True)
    engine = create_async_engine("sqlite+aiosqlite:///data/planner.db", echo=False)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default="личные")
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(String(10), nullable=False, default="medium")
    scheduled_at = Column(DateTime, nullable=True)
    deadline_at = Column(DateTime, nullable=True)
    reminder_minutes = Column(Integer, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    deadline_notified = Column(Boolean, default=False)
    task_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(String(10), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    timezone = Column(String(50), default="Asia/Yekaterinburg")
    created_at = Column(DateTime, default=datetime.now)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite migrations (только для локальной БД)
        if not DATABASE_URL:
            for sql in [
                "ALTER TABLE tasks ADD COLUMN task_number INTEGER",
                "ALTER TABLE tasks ADD COLUMN deadline_notified INTEGER DEFAULT 0",
            ]:
                try:
                    await conn.execute(__import__("sqlalchemy").text(sql))
                except Exception:
                    pass
