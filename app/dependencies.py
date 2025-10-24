from typing import Annotated, AsyncIterable
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings
from app.models.users import User
from jose import jwt


engine = create_async_engine(settings.postgres.build_dsn())
session_maker = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncIterable[AsyncSession]:
    async with session_maker() as session:
        yield session


async def get_current_user_from_token(
    access_token: str | None = Cookie(None, include_in_schema=False),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            access_token,
            settings.auth.secret_key.get_secret_value(),
            algorithms=[settings.auth.algorithm],
        )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException("Invalid token")

        # 3. Получение пользователя из БД
        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException("Invalid token")

        return user

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user_optional(
    access_token: str | None = Cookie(None, include_in_schema=False),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    try:
        return await get_current_user_from_token(access_token=access_token, db=db)
    except Exception:
        return None


# Type Alias для аннотаций
CurrentUser = Annotated[User, Depends(get_current_user_from_token)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
