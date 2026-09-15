from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=7)


class TagCreate(TagBase):
    pass


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
    is_active: bool = True


class NoteCreate(NoteBase):
    tag_ids: list[int] = Field(default_factory=list)
    reminders: list[ReminderCreate] = Field(default_factory=list)


class NoteUpdate(BaseModel):
    version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    text: str | None = None
    target_datetime: datetime | None = None
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