import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.dependencies import CurrentUser, get_db
from app.models.meet import Meet
from app.models.meet_users import MeetUsers
from app.schemas.meet import MeetCreate, MeetResponse, MeetJoin, MeetWithUsersResponse
import shortuuid
from app.config import settings

router = APIRouter(prefix="/meets", tags=["meets"])


@router.get(
    "", response_model=list[MeetResponse], description="Получение списка моих встреч"
)
async def get_meets(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Meet).where(Meet.user_id == current_user.id, Meet.is_active)
    )
    return result.scalars().all()


@router.post(
    "", response_model=MeetResponse, description="Создание встречи с уникальной ссылкой"
)
async def create_meet(
    data: MeetCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    meet_code = shortuuid.uuid()[:12]
    meet_code = f"{meet_code[:3]}-{meet_code[3:6]}-{meet_code[6:9]}".lower()

    meet = Meet(code=meet_code, user_id=current_user.id, schedule=data.schedule)

    db.add(meet)
    await db.commit()
    await db.refresh(meet)
    return meet


@router.get(
    "/{meet_code}",
    response_model=MeetWithUsersResponse,
    description="Получение встречи по уникальному meet_id",
)
async def get_meet(meet_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Meet).where(Meet.code == meet_code).options(selectinload(Meet.meet_users))
    )
    meet = result.scalar_one_or_none()

    if not meet:
        raise HTTPException(status_code=404, detail="Meet not found")

    return meet


@router.post(
    "/join",
    response_model=MeetResponse,
    description="Присоединение к встрече по ссылке",
)
async def join_meet(response: Response, request: Request, data: MeetJoin, db: AsyncSession = Depends(get_db), ):
    
    #  проверяем что пользовать уже в meet
    result = await db.execute(select(MeetUsers).where(MeetUsers.token == request.cookies.get("token_meet")))
    meet_exists = result.scalar_one_or_none()
    
    if meet_exists:
        raise HTTPException(status_code=409, detail="You already in meet")
        
    
    result = await db.execute(select(Meet).where(Meet.code == data.code))
    meet = result.scalar_one_or_none()

    if not meet:
        raise HTTPException(status_code=404, detail="Meet not found")

    if not meet.is_active:
        raise HTTPException(status_code=403, detail="Meet is closed")

    # Генерируем токен для пользователя
    token_meet = secrets.token_urlsafe(8)
    
    meet_user = MeetUsers(
        user_nickname=data.nickname,
        meet_id=meet.id,
        token=token_meet
    )
    
    response.set_cookie(
        key="token_meet",
        value=token_meet,
        httponly=settings.auth.cookie_httponly,
        secure=settings.auth.cookie_secure,
        samesite=settings.auth.cookie_samesite,
        domain=settings.auth.cookie_domain,
    )
    
    db.add(meet_user)
    await db.commit()
    return meet


@router.delete("/{meet_id}", description="Удаление встречи")
async def delete_meet(meet_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meet).where(Meet.meet_id == meet_id))
    meet = result.scalar_one_or_none()

    if not meet:
        raise HTTPException(status_code=404, detail="Meet not found")

    await db.delete(meet)
    await db.commit()
    return {"ok": True}
