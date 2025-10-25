from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import html
import re


class RoomMessageBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    message_type: str = Field(default="text")


class RoomMessageCreate(RoomMessageBase):
    @validator('text')
    def validate_text(cls, v):
        # Базовая очистка от HTML
        v = html.escape(v)
        
        # Проверка на повторяющиеся символы
        if re.match(r'^(.)\1{15,}$', v):
            raise ValueError('Сообщение содержит подозрительные паттерны')
            
        return v


class RoomMessageResponse(RoomMessageBase):
    id: int
    user_nickname: str
    room_id: int
    message_type: str
    is_filtered: bool
    filtered_reason: Optional[str]
    send_at: datetime

    class Config:
        from_attributes = True


class PollingResponse(BaseModel):
    messages: List[RoomMessageResponse] = []
    notifications: List[dict] = []
    user_count: int = 0
    last_message_id: Optional[int] = None
    has_more: bool = False