from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey, TIMESTAMP, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from app.models.room import Room


class RoomMessages(Base):
    """Сообщения в комнате"""

    __tablename__ = "room_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_nickname: Mapped[str] = mapped_column(String(255), comment="Имя пользователя")
    
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id"),
        comment="Айди комнаты",
    )
    text: Mapped[str] = mapped_column(String(115), comment="Текст сообщения")
    original_text: Mapped[str] = mapped_column(String(115), comment="Оригинальный текст (до фильтрации)")
    
    message_type: Mapped[str] = mapped_column(
        String(50), default="text", comment="Тип сообщения: text, system, notification"
    )
    
    is_filtered: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Было ли сообщение отфильтровано"
    )
    
    filtered_reason: Mapped[str] = mapped_column(
        String(500), nullable=True, comment="Причина фильтрации"
    )
    
    send_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        comment="Время отправки сообщения"
    )

    room: Mapped["Room"] = relationship(
        "Room", back_populates="room_messages", lazy="selectin"
    )