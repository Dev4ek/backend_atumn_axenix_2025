import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.dependencies import CurrentUser, get_db, CurrentUserOptional
from app.models.room import Room
from app.models.room_users import RoomUsers
from app.schemas.room import RoomCreate, RoomJoinResponse, RoomResponse, RoomJoin, RoomWithUsersResponse
import shortuuid
from app.config import settings

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get(
    "", response_model=list[RoomResponse], description="Получение списка моих комнат"
)
async def get_rooms(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Room).where(Room.user_id == current_user.id, Room.is_active)
    )
    return result.scalars().all()


@router.post(
    "", response_model=RoomResponse, description="Создание комнаты с уникальной ссылкой"
)
async def create_room(
    data: RoomCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    room_code = shortuuid.uuid()[:12]
    room_code = f"{room_code[:3]}-{room_code[3:6]}-{room_code[6:9]}".lower()

    room = Room(code=room_code, user_id=current_user.id, schedule=data.schedule)

    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.get(
    "/{room_code}",
    response_model=RoomWithUsersResponse,
    description="Получение комнаты по уникальному room_code",
)
async def get_room_by_code(
    room_code: str, request: Request, db: AsyncSession = Depends(get_db)
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
        raise HTTPException(status_code=403, detail="You not login in a room")

    result = await db.execute(
        select(Room)
        .where(Room.code == room_code)
        .options(selectinload(Room.room_users))
    )
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return room


@router.post(
    "/join",
    response_model=RoomJoinResponse,
    description="Присоединение к комнате по ссылке",
)
async def join_room(
    response: Response,
    request: Request,
    data: RoomJoin,
    current_user: CurrentUserOptional,
    db: AsyncSession = Depends(get_db),
):
    # Проверяем что пользователь уже в комнате
    result = await db.execute(
        select(RoomUsers)
        .join(Room, Room.id == RoomUsers.room_id)
        .where(
            RoomUsers.token == request.cookies.get("token_room"),
            Room.code == data.code
        )
    )
    room_user_exists = result.scalar_one_or_none()

    if room_user_exists:
        await db.delete(room_user_exists)

    if current_user:
        nickname = current_user.nickname
    elif data.nickname:
        nickname = data.nickname
    else:
        raise HTTPException(status_code=400, detail="Nickname is required")

    result = await db.execute(select(Room).where(Room.code == data.code))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not room.is_active:
        raise HTTPException(status_code=403, detail="Room is closed")

    # Генерируем токен для пользователя
    token_room = secrets.token_urlsafe(8)

    room_user = RoomUsers(user_nickname=nickname, room_id=room.id, token=token_room)

    db.add(room_user)
    await db.commit()
    
    
    response.set_cookie(
        key="token_room",
        value=token_room,
        httponly=False,
        secure=settings.auth.cookie_secure,
        samesite=settings.auth.cookie_samesite,
        domain=settings.auth.cookie_domain,
    )


    return RoomJoinResponse(
        id=room.id,
        code=room.code,
        token=token_room
    )


@router.delete("/leave", description="Покинуть комнату")
async def leave_room(request: Request, db: AsyncSession = Depends(get_db)):
    token_room = request.cookies.get("token_room")

    if not token_room:
        raise HTTPException(status_code=400, detail="Not room login")

    result = await db.execute(select(RoomUsers).where(RoomUsers.token == token_room))
    room_user = result.scalar_one_or_none()

    if not room_user:
        raise HTTPException(status_code=404, detail="Room user not found")

    await db.delete(room_user)
    await db.commit()
    return {"ok": True}

@router.delete("/{room_id}", description="Удаление комнаты (только создатель)")
async def delete_room(
    room_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this room"
        )

    await db.delete(room)
    await db.commit()
    return {"ok": True}
