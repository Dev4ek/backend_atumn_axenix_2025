from datetime import datetime
from sqlalchemy import TIMESTAMP, Integer, String, func
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

class User(Base):
    """Модель пользователя"""

    __tablename__ = "users"
    

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    nickname: Mapped[str] = mapped_column(
        String(255),
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    
    # # Отношения
    # hosted_rooms = relationship(
    #     "Room", back_populates="host", foreign_keys="Room.host_id"
    # )
    # participations = relationship(
    #     "Participant", back_populates="user", cascade="all, delete-orphan"
    # )
    # messages = relationship(
    #     "Message", back_populates="user", cascade="all, delete-orphan"
    # )
