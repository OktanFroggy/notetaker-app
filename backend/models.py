from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Table, Text, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True, default="user@example.com")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True, default="user@example.com")
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")
    notes: Mapped[list["Note"]] = relationship(secondary=note_tags, back_populates="tags")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True, default="user@example.com")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    repeat: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    repeat_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", onupdate="now()"
    )
    tags: Mapped[list[Tag]] = relationship(secondary=note_tags, back_populates="notes")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="note")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[Note] = relationship(back_populates="reminders")