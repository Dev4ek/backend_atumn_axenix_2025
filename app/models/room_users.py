from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from app.models.room import Room


class RoomUsers(Base):
    """Участники подключенные к комнате"""

    __tablename__ = "room_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_nickname: Mapped[str] = mapped_column(String(255), comment="Имя пользователя")
    token: Mapped[str] = mapped_column(
        String(255), comment="Уникальный токен пользователя"
    )
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id"),
        comment="Айди комнаты к которой подключен пользователь",
    )

    room: Mapped["Room"] = relationship(
        "Room", back_populates="room_users", lazy="selectin"
    )
