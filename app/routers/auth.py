from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.models.users import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Установка токенов в cookies"""

    # Access token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.auth.cookie_httponly,
        secure=settings.auth.cookie_secure,
        samesite=settings.auth.cookie_samesite,
        max_age=settings.auth.access_token_expire_minutes * 60,
        domain=settings.auth.cookie_domain,
    )

    # Refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.auth.cookie_secure,
        samesite=settings.auth.cookie_samesite,
        max_age=settings.auth.refresh_token_expire_days * 24 * 60 * 60,
        domain=settings.auth.cookie_domain,
    )


@router.post("/login")
async def login(
    data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    """Логин с установкой cookies"""
    result = await db.execute(select(User).where(User.nickname == data.nickname))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    set_auth_cookies(response, access_token, refresh_token)

    return {"message": "Login successful"}


@router.post("/register")
async def register(
    data: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    """Регистрация с установкой cookies"""
    result = await db.execute(select(User).where(User.nickname == data.nickname))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(nickname=data.nickname, password_hash=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    set_auth_cookies(response, access_token, refresh_token)

    return {"message": "User registered successfully"}


@router.post("/logout")
async def logout(response: Response):
    """Выход - удаление cookies"""
    response.delete_cookie(key="access_token",
        httponly=settings.auth.cookie_httponly,
        secure=settings.auth.cookie_secure,
        samesite=settings.auth.cookie_samesite,
        domain=settings.auth.cookie_domain
    )
    response.delete_cookie(key="refresh_token",
        httponly=settings.auth.cookie_httponly,
        secure=settings.auth.cookie_secure,
        samesite=settings.auth.cookie_samesite,
        domain=settings.auth.cookie_domain
    )
    return {"message": "Logout successful"}


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str = Cookie(None, include_in_schema=False),
    db: AsyncSession = Depends(get_db),
):
    """Обновление access токена через refresh токен"""

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = jwt.decode(
            refresh_token,
            settings.auth.secret_key.get_secret_value(),
            algorithms=[settings.auth.algorithm],
        )

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        new_access_token = create_access_token({"sub": str(user.id)})
        new_refresh_token = create_refresh_token({"sub": str(user.id)})

        set_auth_cookies(response, new_access_token, new_refresh_token)

        return {"message": "Token refreshed successfully"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
