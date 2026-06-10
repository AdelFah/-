from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
import os
import socket

DATABASE_URL = os.getenv("DATABASE_URL")


def _force_ipv4_url(url: str) -> tuple[str, dict]:
    """Резолвит hostname в IPv4 и возвращает url + connect_args."""
    import re
    match = re.search(r'@([^:/]+):', url)
    if not match:
        return url, {}
    hostname = match.group(1)
    try:
        ipv4 = socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]
        connect_args = {"hostaddr": ipv4}
        return url, connect_args
    except Exception:
        return url, {}


if DATABASE_URL:
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    url, connect_args = _force_ipv4_url(url)
    engine = create_async_engine(url, echo=False, connect_args=connect_args)
    IS_POSTGRES = True
else:
    os.makedirs("data", exist_ok=True)
    engine = create_async_engine("sqlite+aiosqlite:///data/planner.db", echo=False)
    IS_POSTGRES = False

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


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False)   # user | assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


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
        if not IS_POSTGRES:
            for sql in [
                "ALTER TABLE tasks ADD COLUMN task_number INTEGER",
                "ALTER TABLE tasks ADD COLUMN deadline_notified INTEGER DEFAULT 0",
            ]:
                try:
                    await conn.execute(__import__("sqlalchemy").text(sql))
                except Exception:
                    pass
