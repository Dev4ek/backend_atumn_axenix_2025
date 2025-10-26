import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import router
from contextlib import asynccontextmanager

from app.routers.websocket import cleanup_stale_connections

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cleanup_task = asyncio.create_task(cleanup_stale_connections())
    yield
    # Shutdown
    cleanup_task.cancel()

# Создание приложения
app = FastAPI(
    title="УткиУУУ - Онлайн Конференции",
    description="API для веб-приложения онлайн-конференций",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://axenix.site",
        "https://api.idenmarket.com",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Подключение роутеров
app.include_router(router)

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
