from pydantic import BaseModel, Field
from datetime import datetime


class MeetCreate(BaseModel):
    schedule: datetime | None = Field(
        None, description="На какую дату запланирована встреча"
    )


class MeetResponse(BaseModel):
    """Схема ответа с информацией о встрече"""

    id: int
    code: str = Field(..., description="Уникальный код встречи")
    user_id: int = Field(..., description="ID создателя встречи")
    is_active: bool = Field(..., description="Активна ли встреча")
    schedule: datetime | None = Field(None, description="Дата запланированной встречи")
    created_at: datetime = Field(..., description="Дата создания встречи")


class MeetUser(BaseModel):
    user_nickname: str = Field(..., description="")


class MeetWithUsersResponse(BaseModel):
    """Схема ответа с информацией о встрече и пользователями"""

    id: int
    code: str = Field(..., description="Уникальный код встречи")
    user_id: int = Field(..., description="ID создателя встречи")
    is_active: bool = Field(..., description="Активна ли встреча")
    schedule: datetime | None = Field(None, description="Дата запланированной встречи")
    created_at: datetime = Field(..., description="Дата создания встречи")

    meet_users: list[MeetUser] = Field(
        ..., description="Пользователи подключенные к встрече"
    )


class MeetJoin(BaseModel):
    """Схема для присоединения к встрече"""

    code: str = Field(..., description="Код встречи для присоединения")
    nickname: str = Field(..., description="Имя пользователя на встрече")


class MeetUpdate(BaseModel):
    """Схема для обновления встречи"""

    is_active: bool | None = Field(None, description="Изменить статус активности")
    schedule: datetime | None = Field(None, description="Изменить дату встречи")
