from pydantic import BaseModel
from datetime import datetime


class RoomCreate(BaseModel):
    name: str
    host_id: int


class RoomResponse(BaseModel):
    id: int
    room_id: str
    name: str
    host_id: int
    is_active: bool
    created_at: datetime
    


class RoomJoin(BaseModel):
    room_id: str
