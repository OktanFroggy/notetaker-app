from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Некорректный формат email")
    return email


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    timezone: str


class UserSettingsUpdate(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ReminderBase(BaseModel):
    remind_at: datetime
    offset_minutes: int = 0
    is_sent: bool = False


class ReminderCreate(ReminderBase):
    pass


class ReminderResponse(ReminderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int


class NoteBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    text: str = ""
    target_datetime: datetime | None = None
    repeat: str = Field(default="none", pattern=r"^(none|daily|weekly|monthly)$")
    repeat_until: datetime | None = None
    is_active: bool = True


class NoteCreate(NoteBase):
    tag_ids: list[int] = Field(default_factory=list)
    reminders: list[ReminderCreate] = Field(default_factory=list)


class NoteUpdate(BaseModel):
    version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    text: str | None = None
    target_datetime: datetime | None = None
    repeat: str | None = Field(default=None, pattern=r"^(none|daily|weekly|monthly)$")
    repeat_until: datetime | None = None
    is_active: bool | None = None
    tag_ids: list[int] | None = None
    reminders: list[ReminderCreate] | None = None


class NoteResponse(NoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deleted_at: datetime | None = None
    version: int
    updated_at: datetime
    tags: list[TagResponse] = Field(default_factory=list)
    reminders: list[ReminderResponse] = Field(default_factory=list)
    series_id: int | None = None