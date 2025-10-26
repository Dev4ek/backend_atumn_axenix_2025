from fastapi import APIRouter
from .users import router as users_router
from .rooms import router as rooms_router
from .auth import router as auth_routers
from .websocket import router as websocket_router
from .crypto import router as crypto_router

router = APIRouter(prefix="")

router.include_router(auth_routers)
router.include_router(users_router)
router.include_router(rooms_router)
router.include_router(websocket_router)
router.include_router(crypto_router)
