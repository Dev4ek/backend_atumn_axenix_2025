from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import html
import re
from app.utils.auth import rs


class RoomMessageBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    message_type: str = Field(default="text")


class RoomMessageCreate(BaseModel):
    public_key_user: str
    text: str = Field(..., min_length=1, max_length=2000)
    message_type: str = Field(default="text")
    
    @validator('text')
    def encrypt_text(cls, v, values):
        if 'public_key_user' in values:

            encrypted_text = rs.sync_decode(public_key_user=values['public_key_user'], encrypted_message=v)
            return encrypted_text
        return v

class RoomMessageResponse(BaseModel):
    id: int
    public_key_user: str
    text: str
    @validator('text')
    def encrypt_text(cls, v, values):
        print(values)
        if 'public_key_user' in values:
            text = rs.sync_encode(public_key_user=values['public_key_user'], message=v)
            return text
        return v

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




class RoomMessageGetNew(BaseModel):
    last_message_id: int 
    timeout: int = Field(30, ge=5, le=60, description="Таймаут ожидания (секунды)"),
    public_key_user: str = Field(..., description="Публичный ключ пользователя для шифрования")

class RoomMessageGetAll(BaseModel):
    limit: int = Field(100, ge=1, le=1000),
    offset: int = Field(0, ge=0),
    public_key_user: str = Field(..., description="Публичный ключ пользователя для шифрования"),