from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from app.models.room import Room


class RoomChats(Base):
    """Сообщения в комнате"""

    __tablename__ = "room_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_nickname: Mapped[str] = mapped_column(String(255), comment="Имя пользователя")
    
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id"),
        comment="Айди комнаты",
    )
    text: Mapped[str] = mapped_column(String(1000), comment="Текст сообщения")
    send_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        comment="Время отправки сообщения"
    )

    room: Mapped["Room"] = relationship(
        "Room", back_populates="room_chats", lazy="selectin"
    )