from pydantic import BaseModel, Field
from datetime import datetime


class UserResponse(BaseModel):
    id: int = Field(..., description="Уникальный ID пользователя")
    nickname: str = Field(..., description="Имя пользователя")
    avatar: str = Field(..., description="Ссылка на аватар пользователя")
    created_at: datetime = Field(..., description="Дата и время создания аккаунта")


class UserCreate(BaseModel):
    nickname: str
    password: str
