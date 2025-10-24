from pydantic import BaseModel, Field
from datetime import datetime


class RoomCreate(BaseModel):
    """Схема создания комнаты"""

    schedule: datetime | None = Field(
        None, description="На какую дату запланирована встреча в комнате"
    )


class RoomResponse(BaseModel):
    """Схема ответа с информацией о комнате"""

    id: int
    code: str = Field(..., description="Уникальный код комнаты")
    user_id: int = Field(..., description="ID создателя комнаты")
    is_active: bool = Field(..., description="Активна ли комната")
    schedule: datetime | None = Field(None, description="Дата запланированной встречи")
    created_at: datetime = Field(..., description="Дата создания комнаты")


class RoomUser(BaseModel):
    """Схема пользователя в комнате"""

    user_nickname: str = Field(..., description="Никнейм пользователя")


class RoomWithUsersResponse(BaseModel):
    """Схема ответа с информацией о комнате и пользователями"""

    id: int
    code: str = Field(..., description="Уникальный код комнаты")
    user_id: int = Field(..., description="ID создателя комнаты")
    is_active: bool = Field(..., description="Активна ли комната")
    schedule: datetime | None = Field(None, description="Дата запланированной встречи")
    created_at: datetime = Field(..., description="Дата создания комнаты")

    room_users: list[RoomUser] = Field(
        ..., description="Пользователи подключенные к комнате"
    )


class RoomJoin(BaseModel):
    """Схема для присоединения к комнате"""

    code: str = Field(..., description="Код комнаты для присоединения")
    nickname: str | None = Field(None, description="Имя пользователя в комнате")


class RoomUpdate(BaseModel):
    """Схема для обновления комнаты"""

    is_active: bool | None = Field(None, description="Изменить статус активности")
    schedule: datetime | None = Field(None, description="Изменить дату встречи")
