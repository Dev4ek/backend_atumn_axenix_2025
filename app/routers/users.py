from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import CurrentUser, get_db
from app.models.users import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()


@router.get("/me", response_model=UserResponse)
async def get_me_user(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, data: UserCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.nickname:
        user.nickname = data.nickname
    if data.password:
        user.password_hash = data.password

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/avatar", response_model=UserResponse)
async def update_avatar(
    current_user: CurrentUser,
    avatar: UploadFile = File(..., description="Аватар"),
    db: AsyncSession = Depends(get_db),
):
    STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
    AVATARS_DIR = STATIC_DIR / "avatars"
    
    # Создаём папку, если её нет
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    
    file_ext = Path(avatar.filename).suffix.lower()
    
    if file_ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Недопустимый формат файла")
    
    # Генерируем уникальное имя файла
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = AVATARS_DIR / unique_filename
    
    # Удаляем старый аватар, если есть
    if current_user.avatar:
        old_avatar_path = AVATARS_DIR / Path(current_user.avatar).name
        if old_avatar_path.exists():
            old_avatar_path.unlink()
    
    # Сохраняем новый файл
    contents = await avatar.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Обновляем путь в БД
    current_user.avatar = f"/static/avatars/{unique_filename}"
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user
