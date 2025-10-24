from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import TIMESTAMP, Integer, String, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.room_users import RoomUsers
from .base import Base

if TYPE_CHECKING:
    from app.models.users import User


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(255), comment="Уникальный код комнаты")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), comment="Айди пользователя кто создал комнату"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Является ли комната активной"
    )
    schedule: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="На какую дату запланирована встреча в комнате",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Когда комната была создана",
    )

    user: Mapped["User"] = relationship("User", back_populates="rooms", lazy="selectin")
    room_users: Mapped[list["RoomUsers"]] = relationship(
        "RoomUsers",
        back_populates="room",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
