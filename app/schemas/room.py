from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class RoomCreate(BaseModel):
    """Схема создания комнаты"""

    schedule: datetime | None = Field(
        None, description="На какую дату запланирована встреча в комнате"
    )
    banned_words: list[str]| None = Field(
        None, description="список запрещеныйх слов"
    )

class RoomJoinResponse(BaseModel):
    """Схема ответа на присоединение в комнату"""
    
    id: int = Field(..., description="ID созданной комнаты")
    code: str = Field(..., description="Уникальный код комнаты")
    token: str = Field(..., description="Уникальный токен для пользователя в комнате")
    

class RoomResponse(BaseModel):
    """Схема ответа с информацией о комнате"""

    id: int = Field(..., description="Уникальный идентификатор комнаты")
    code: str = Field(..., description="Уникальный код комнаты для присоединения")
    user_id: int = Field(..., description="ID пользователя создавшего комнату")
    is_active: bool = Field(..., description="Активна ли комната для присоединения")
    schedule: datetime | None = Field(None, description="Дата запланированной встречи")
    created_at: datetime = Field(..., description="Дата и время создания комнаты")


class RoomUser(BaseModel):
    """Схема пользователя в комнате"""

    user_nickname: str = Field(..., description="Никнейм пользователя в комнате")


class RoomWithUsersResponse(BaseModel):
    """Схема ответа с информацией о комнате и пользователями"""

    id: int = Field(..., description="Уникальный идентификатор комнаты")
    code: str = Field(..., description="Уникальный код комнаты для присоединения")
    user_id: int = Field(..., description="ID пользователя создавшего комнату")
    is_active: bool = Field(..., description="Активна ли комната для присоединения")
    schedule: datetime | None = Field(None, description="Дата запланированной встречи")
    created_at: datetime = Field(..., description="Дата и время создания комнаты")

    room_users: list[RoomUser] = Field(
        ..., description="Список пользователей подключенных к комнате"
    )


class RoomJoin(BaseModel):
    """Схема для присоединения к комнате"""

    code: str = Field(..., description="Код комнаты для присоединения")
    nickname: str | None = Field(None, description="Имя пользователя в комнате (если пользователь не авторизован)")


class RoomUpdate(BaseModel):
    """Схема для обновления настроек комнаты"""

    is_active: bool | None = Field(None, description="Изменить статус активности комнаты")
    schedule: datetime | None = Field(None, description="Изменить дату и время запланированной встречи")


class RoomMessageBase(BaseModel):
    """Базовая схема сообщения в комнате"""
    
    text: str = Field(..., min_length=1, max_length=2000, description="Текст сообщения")
    message_type: str = Field(default="text", description="Тип сообщения: text, system, notification")


class RoomMessageCreate(RoomMessageBase):
    """Схема для создания нового сообщения в комнате"""
    
    pass


class RoomMessageResponse(RoomMessageBase):
    """Схема ответа с информацией о сообщении"""
    
    id: int = Field(..., description="Уникальный идентификатор сообщения")
    user_nickname: str = Field(..., description="Никнейм пользователя отправившего сообщение")
    room_id: int = Field(..., description="ID комнаты в которой отправлено сообщение")
    message_type: str = Field(..., description="Тип сообщения")
    is_filtered: bool = Field(..., description="Было ли сообщение отфильтровано модерацией")
    filtered_reason: Optional[str] = Field(None, description="Причина фильтрации сообщения")
    send_at: datetime = Field(..., description="Дата и время отправки сообщения")


class PollingResponse(BaseModel):
    """Схема ответа для long-polling запроса новых сообщений"""
    
    messages: List[RoomMessageResponse] = Field(
        default_factory=list, 
        description="Список новых сообщений с момента последнего запроса"
    )
    notifications: List[dict] = Field(
        default_factory=list,
        description="Список уведомлений (вход/выход пользователей, модерация)"
    )
    user_count: int = Field(
        default=0,
        description="Текущее количество пользователей в комнате"
    )
    last_message_id: Optional[int] = Field(
        None,
        description="ID последнего сообщения в ответе (для следующего запроса)"
    )
    has_more: bool = Field(
        default=False,
        description="Есть ли еще сообщения для загрузки"
    )


class RoomWithBannedWordsResponse(BaseModel):
    """Схема ответа с информацией о комнате и списком запрещенных слов"""
    
    id: int = Field(..., description="Уникальный идентификатор комнаты")
    code: str = Field(..., description="Уникальный код комнаты")
    is_active: bool = Field(..., description="Активна ли комната")
    banned_words: List[str] = Field(
        ...,
        description="Список запрещенных слов для фильтрации сообщений в комнате"
    )
    created_at: datetime = Field(..., description="Дата и время создания комнаты")


class RoomSettingsUpdate(BaseModel):
    """Схема для обновления настроек комнаты (модерация)"""
    
    banned_words: Optional[List[str]] = Field(
        None,
        description="Список запрещенных слов для фильтрации сообщений"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Статус активности комнаты"
    )


class NotificationMessage(BaseModel):
    """Схема уведомления в реальном времени"""
    
    type: str = Field(
        ...,
        description="Тип уведомления: user_joined, user_left, message_filtered, room_updated"
    )
    user_nickname: Optional[str] = Field(
        None,
        description="Никнейм пользователя связанного с уведомлением"
    )
    message: str = Field(..., description="Текст уведомления")
    timestamp: datetime = Field(..., description="Время создания уведомления")
    reason: Optional[str] = Field(
        None,
        description="Причина уведомления (например, причина фильтрации сообщения)"
    )


class RoomUsersResponse(BaseModel):
    """Схема ответа со списком пользователей в комнате"""
    
    users: List[str] = Field(..., description="Список никнеймов пользователей в комнате")
    user_count: int = Field(..., description="Общее количество пользователей в комнате")