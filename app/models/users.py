from datetime import datetime
from sqlalchemy import TIMESTAMP, Integer, String, func
from typing import TYPE_CHECKING


from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.room import Room


class User(Base):
    """Модель пользователя"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    nickname: Mapped[str] = mapped_column(String(255), unique=True)

    password_hash: Mapped[str] = mapped_column(
        String(255),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
