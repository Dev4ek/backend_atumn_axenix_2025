import secrets
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.dependencies import CurrentUser, get_db, CurrentUserOptional
from app.models.room import Room
from app.models.room_users import RoomUsers
from app.models.room_messages import RoomMessages
from app.schemas.room import RoomCreate, RoomJoinResponse, RoomResponse, RoomJoin, RoomWithUsersResponse, RoomUpdate, RoomWithBannedWordsResponse
from app.schemas.room_messages import RoomMessageCreate, RoomMessageResponse, PollingResponse, RoomMessageGetNew, RoomMessageGetAll 
from app.services.message_filter import message_filter
from app.services.notification_service import notification_service
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

    room = Room(
        name=data.name,
        code=room_code, 
        user_id=current_user.id, 
        schedule=data.schedule,
        banned_words=data.banned_words  # Пустой список запрещенных слов по умолчанию
    )

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
    
    # Отправляем уведомление о присоединении
    notification_service.add_notification(room.id, {
        "type": "user_joined",
        "user_nickname": nickname,
        "message": f"{nickname} присоединился к чату",
        "timestamp": datetime.utcnow().isoformat()
    })
    
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

    result = await db.execute(
        select(RoomUsers)
        .where(RoomUsers.token == token_room)
        .options(selectinload(RoomUsers.room))
    )
    room_user = result.scalar_one_or_none()

    if not room_user:
        raise HTTPException(status_code=404, detail="Room user not found")

    # Отправляем уведомление о выходе
    notification_service.add_notification(room_user.room_id, {
        "type": "user_left", 
        "user_nickname": room_user.user_nickname,
        "message": f"{room_user.user_nickname} покинул чат",
        "timestamp": datetime.utcnow().isoformat()
    })

    # Отписываем от уведомлений
    notification_service.unsubscribe_user(room_user.room_id, token_room)

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


# ===== НОВЫЕ ЭНДПОИНТЫ ДЛЯ СООБЩЕНИЙ =====

@router.post(
    "/{room_code}/poll",
    response_model=PollingResponse,
    description="Long-polling для получения новых сообщений и уведомлений"
)
async def poll_messages(
    room_code: str,
    request: Request,
    roommessage: RoomMessageGetNew,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем доступ к комнате
    token_room = request.cookies.get("token_room")
    result = await db.execute(
        select(RoomUsers)
        .join(Room, Room.id == RoomUsers.room_id)
        .where(
            RoomUsers.token == token_room,
            Room.code == room_code
        )
    )
    room_user = result.scalar_one_or_none()

    if not room_user:
        raise HTTPException(status_code=403, detail="You are not in this room")

    room_id = room_user.room_id
    start_time = datetime.utcnow()
    
    # Подписываем пользователя на уведомления
    notification_service.subscribe_user(room_id, token_room)

    # Проверяем наличие новых данных с интервалами
    while (datetime.utcnow() - start_time).seconds < roommessage.timeout:
        # Получаем новые сообщения
        result = await db.execute(
            select(RoomMessages)
            .where(
                RoomMessages.room_id == room_id,
                RoomMessages.id > roommessage.last_message_id
            )
            .order_by(RoomMessages.id.asc())
        )
        new_messages = result.scalars().all()

        # Получаем уведомления с момента последней проверки
        notifications = notification_service.get_pending_notifications(
            room_id, start_time - timedelta(seconds=5)
        )

        # Если есть новые данные - возвращаем сразу
        if new_messages or notifications:
            # Получаем количество пользователей в комнате
            user_count_result = await db.execute(
                select(func.count(RoomUsers.id))
                .where(RoomUsers.room_id == room_id)
            )
            user_count = user_count_result.scalar() or 0
            for msg in new_messages:
                msg.public_key_user = roommessage.public_key_user
                MessageResponse=[RoomMessageResponse.from_orm(msg) ]
            return PollingResponse(
                messages=MessageResponse,
                notifications=notifications,
                user_count=user_count,
                last_message_id=new_messages[-1].id if new_messages else roommessage.last_message_id,
                has_more=False
            )

        # Ждем 1 секунду перед следующей проверкой
        await asyncio.sleep(1)

    # Таймаут - возвращаем пустой ответ
    return PollingResponse(
        messages=[],
        notifications=[],
        user_count=0,
        last_message_id=roommessage.last_message_id,
        has_more=False
    )


@router.post(
    "/{room_code}/messages/send",
    response_model=RoomMessageResponse,
    description="Отправка сообщения в комнату"
)
async def create_message(
    room_code: str,
    message_data: RoomMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем доступ к комнате
    token_room = request.cookies.get("token_room")
    result = await db.execute(
        select(RoomUsers)
        .join(Room, Room.id == RoomUsers.room_id)
        .where(
            RoomUsers.token == token_room,
            Room.code == room_code
        )
        .options(selectinload(RoomUsers.room))
    )
    room_user = result.scalar_one_or_none()

    if not room_user:
        raise HTTPException(status_code=403, detail="You are not in this room")

    room = room_user.room
    
    if not room.is_active:
        raise HTTPException(status_code=403, detail="Room is closed")

    # Получаем запрещенные слова комнаты
    # banned_words = []
    # if room.banned_words:
    #     try:
    #         banned_words = json.loads(room.banned_words)
    #     except:
    #         banned_words = []

    # Фильтруем сообщение
    filter_result = message_filter.filter_message(
        message_data.text, 
        room.banned_words
    )

    # Создаем сообщение
    message = RoomMessages(
        user_nickname=room_user.user_nickname,
        room_id=room.id,
        text=filter_result["filtered_text"],
        original_text=filter_result["original_text"],
        message_type=message_data.message_type,
        is_filtered=not filter_result["is_clean"],
        filtered_reason=filter_result["filtered_reason"]
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    # Обновляем последний ID сообщения для уведомлений
    notification_service.update_last_message_id(room.id, message.id)

    # Если сообщение было отфильтровано - отправляем уведомление
    if message.is_filtered:
        notification_service.add_notification(room.id, {
            "type": "message_filtered",
            "user_nickname": room_user.user_nickname,
            "message": f"Сообщение от {room_user.user_nickname} было отфильтровано",
            "reason": filter_result["filtered_reason"],
            "timestamp": datetime.utcnow().isoformat()
        })
    message.public_key_user = message_data.public_key_user
    return RoomMessageResponse.from_orm(message)


@router.post(
    "/{room_code}/messages",
    response_model=list[RoomMessageResponse],
    description="Получение истории сообщений комнаты"
)
async def get_room_messages(
    room_code: str,
    request: Request,
    RoomMessage:RoomMessageGetAll,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем доступ к комнате
    token_room = request.cookies.get("token_room")
    result = await db.execute(
        select(RoomUsers)
        .join(Room, Room.id == RoomUsers.room_id)
        .where(
            RoomUsers.token == token_room,
            Room.code == room_code
        )
    )
    room_user = result.scalar_one_or_none()

    if not room_user:
        raise HTTPException(status_code=403, detail="You are not in this room")

    # Получаем сообщения
    result = await db.execute(
        select(RoomMessages)
        .where(RoomMessages.room_id == room_user.room_id)
        .order_by(desc(RoomMessages.send_at))

    )
    
    messages = result.scalars().all()
    msgg = []
    for msg in messages:
        msg.public_key_user = RoomMessage.public_key_user
        msgg.append(RoomMessageResponse.from_orm(msg))
    return msgg


@router.put(
    "/{room_code}/settings",
    response_model=RoomWithBannedWordsResponse,
    description="Обновление настроек комнаты (только создатель)"
)
async def update_room_settings(
    room_code: str,
    settings: RoomUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    # Получаем комнату
    result = await db.execute(
        select(Room).where(
            Room.code == room_code,
            Room.user_id == current_user.id
        )
    )
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found or access denied")

    # Обновляем запрещенные слова
    if settings.banned_words is not None:
        room.banned_words = json.dumps(settings.banned_words)

    # Обновляем активность
    if settings.is_active is not None:
        room.is_active = settings.is_active

    await db.commit()
    await db.refresh(room)

    # Парсим banned_words для ответа
    banned_words_list = []
    if room.banned_words:
        try:
            banned_words_list = json.loads(room.banned_words)
        except:
            banned_words_list = []

    return RoomWithBannedWordsResponse(
        id=room.id,
        code=room.code,
        is_active=room.is_active,
        banned_words=banned_words_list,
        created_at=room.created_at
    )


@router.get(
    "/{room_code}/settings",
    response_model=RoomWithBannedWordsResponse,
    description="Получение настроек комнаты"
)
async def get_room_settings(
    room_code: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Room).where(Room.code == room_code)
    )
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Парсим banned_words для ответа
    banned_words_list = []
    if room.banned_words:
        try:
            banned_words_list = json.loads(room.banned_words)
        except:
            banned_words_list = []

    return RoomWithBannedWordsResponse(
        id=room.id,
        code=room.code,
        is_active=room.is_active,
        banned_words=banned_words_list,
        created_at=room.created_at
    )


@router.get("/{room_code}/users", description="Получение списка пользователей в комнате")
async def get_room_users(
    room_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем доступ к комнате
    token_room = request.cookies.get("token_room")
    result = await db.execute(
        select(RoomUsers)
        .join(Room, Room.id == RoomUsers.room_id)
        .where(
            RoomUsers.token == token_room,
            Room.code == room_code
        )
    )
    room_user = result.scalar_one_or_none()

    if not room_user:
        raise HTTPException(status_code=403, detail="You are not in this room")

    # Получаем всех пользователей комнаты
    result = await db.execute(
        select(RoomUsers.user_nickname)
        .where(RoomUsers.room_id == room_user.room_id)
    )
    users = result.scalars().all()

    return {"users": list(users), "user_count": len(users)}
