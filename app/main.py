from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import router

# Создание приложения
app = FastAPI(
    title="УткиУУУ - Онлайн Конференции",
    description="API для веб-приложения онлайн-конференций",
    version="1.0.0",
    docs_url="/docs",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(router)
