from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import CurrentUser, get_db
from app.models.rooms import Room
from app.schemas.room import RoomCreate, RoomResponse, RoomJoin
import shortuuid

router = APIRouter(prefix="/rooms", tags=["rooms"])



@router.get("", response_model=list[RoomResponse], description="Получение списка комнат")
async def get_rooms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room))
    return result.scalars().all()

@router.post("", response_model=RoomResponse, description="Создание комнаты с уникальной ссылкой")
async def create_room(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    room_id = shortuuid.uuid()[:12]  # Генерация короткого ID
    
    room = Room(
        room_id=room_id,
    )
    
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room



@router.get("/{room_id}", response_model=RoomResponse, description="Получение комнаты по уникальному room_id")
async def get_room(room_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.room_id == room_id))
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return room


# JOIN (гостевой доступ)
@router.post("/join", response_model=RoomResponse, description="Присоединение к комнате по ссылке")
async def join_room(data: RoomJoin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.room_id == data.room_id))
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if not room.is_active:
        raise HTTPException(status_code=403, detail="Room is closed")
    
    return room


@router.delete("/{room_id}", description="Удаление комнаты")
async def delete_room(room_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.room_id == room_id))
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    await db.delete(room)
    await db.commit()
    return {"ok": True}
