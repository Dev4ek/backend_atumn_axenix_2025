from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from app.models.meet import Meet


class MeetUsers(Base):
    "Участники подключенные к встрече"

    __tablename__ = "meet_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_nickname: Mapped[str] = mapped_column(String(255), comment="Имя пользователя")
    token: Mapped[str] = mapped_column(String(255), comment="Уникальный токен пользователя")
    meet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("meets.id"),
        comment="Айди встречи к которой подключен пользователь",
    )

    meet: Mapped["Meet"] = relationship(
        "Meet", back_populates="meet_users", lazy="selectin"
    )
