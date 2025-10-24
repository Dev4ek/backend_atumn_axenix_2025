from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import TIMESTAMP, Integer, String, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.meet_users import MeetUsers
from .base import Base

if TYPE_CHECKING:
    from app.models.users import User


class Meet(Base):
    __tablename__ = "meets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(255), comment="Уникальный код комнаты")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), comment="Айди пользователя кто создал встречу"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Является ли встреча активной"
    )
    schedule: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="На какую дату запланирована встреча",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Когда встреча была создана",
    )

    user: Mapped["User"] = relationship("User", back_populates="meets", lazy="selectin")
    meet_users: Mapped[list["MeetUsers"]] = relationship(
        "MeetUsers",
        back_populates="meet",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
