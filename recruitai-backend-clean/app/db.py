import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")  # Set in Render from Neon
engine = create_async_engine(DATABASE_URL, echo=True) if DATABASE_URL else None
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False) if engine else None

Base = declarative_base()

async def get_db():
    if not async_session:
        raise ValueError("Database not configured")
    async with async_session() as session:
        yield session
