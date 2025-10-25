from fastapi import APIRouter, Depends, HTTPException, Query,Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.dependencies import get_db, CurrentUserOptional
from app.models.room import Room
from app.models.room_users import RoomUsers
from app.models.room_messages import RoomMessages
from app.schemas.room_messages import RoomMessageResponse, RoomMessageCreate
from datetime import datetime
from app.routers.rooms import router
# Добавляем в существующий router или создаем новый
# router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.get(
    "/{room_code}/messages",
    response_model=list[RoomMessageResponse],
    description="Получение всех сообщений в комнате"
)
async def get_room_messages(
    room_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Лимит сообщений"),
    offset: int = Query(0, ge=0, description="Смещение")
):
    # Проверяем что пользователь уже в комнате
    result = await db.execute(
        select(RoomUsers)
        .join(Room, Room.id == RoomUsers.room_id)
        .where(
            RoomUsers.token == request.cookies.get("token_room"),
            Room.code == room_code
        )
    )
    room_user_exists = result.scalar_one_or_none()

    if not room_user_exists:
        raise HTTPException(status_code=403, detail="You are not in this room")

    # Получаем комнату
    result = await db.execute(
        select(Room).where(Room.code == room_code)
    )
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Получаем сообщения с пагинацией
    result = await db.execute(
        select(RoomMessages)
        .where(RoomMessages.room_id == room.id)
        .order_by(desc(RoomMessages.send_at))
        .limit(limit)
        .offset(offset)
        .options(selectinload(RoomMessages.room))
    )
    
    messages = result.scalars().all()
    return messages


@router.post(
    "/{room_code}/messages",
    response_model=RoomMessageResponse,
    description="Отправка сообщения в комнату"
)
async def create_room_message(
    room_code: str,
    data: RoomMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем что пользователь уже в комнате
    result = await db.execute(
        select(RoomUsers)
        .join(Room, Room.id == RoomUsers.room_id)
        .where(
            RoomUsers.token == request.cookies.get("token_room"),
            Room.code == room_code
        )
    )
    room_user = result.scalar_one_or_none()

    if not room_user:
        raise HTTPException(status_code=403, detail="You are not in this room")

    # Получаем комнату
    result = await db.execute(
        select(Room).where(Room.code == room_code)
    )
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not room.is_active:
        raise HTTPException(status_code=403, detail="Room is closed")

    # Создаем сообщение
    message = RoomMessages(
        user_nickname=room_user.user_nickname,
        room_id=room.id,
        text=data.text,
        send_at=datetime.utcnow()
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    return message


@router.delete(
    "/messages/{message_id}",
    description="Удаление сообщения (только свое или создатель комнаты)"
)
async def delete_message(
    message_id: int,
    request: Request,
    current_user: CurrentUserOptional,
    db: AsyncSession = Depends(get_db)
):
    # Получаем сообщение
    result = await db.execute(
        select(RoomMessages)
        .options(selectinload(RoomMessages.room))
        .where(RoomMessages.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Проверяем права на удаление
    token_room = request.cookies.get("token_room")
    
    # Проверяем является ли пользователь автором сообщения
    result = await db.execute(
        select(RoomUsers)
        .where(
            RoomUsers.token == token_room,
            RoomUsers.user_nickname == message.user_nickname
        )
    )
    is_author = result.scalar_one_or_none()

    # Проверяем является ли пользователь создателем комнаты
    is_owner = False
    if current_user and current_user.id:
        result = await db.execute(
            select(Room).where(
                Room.id == message.room_id,
                Room.user_id == current_user.id
            )
        )
        is_owner = result.scalar_one_or_none() is not None

    if not is_author and not is_owner:
        raise HTTPException(
            status_code=403, 
            detail="You can only delete your own messages or be room owner"
        )

    await db.delete(message)
    await db.commit()
    
    return {"ok": True}