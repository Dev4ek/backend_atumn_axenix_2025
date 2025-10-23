from typing import AsyncIterable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings


engine = create_async_engine(settings.postgres.build_dsn())
session_maker = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncIterable[AsyncSession]:
    async with session_maker() as session:
        yield session
