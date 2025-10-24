from fastapi import APIRouter
from .users import router as users_router
from .room import router as rooms_router
from .auth import router as auth_routers

router = APIRouter(prefix="")

router.include_router(auth_routers)
router.include_router(users_router)
router.include_router(rooms_router)
