import asyncio
import json
import re
from contextlib import asynccontextmanager
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from email_emulator import send_email_notification
import models
from schemas import (
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    TagCreate,
    TagResponse,
    TagUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
    normalize_email,
)


Base.metadata.create_all(bind=engine)
from database import add_missing_user_email_columns

add_missing_user_email_columns()


def ensure_default_user_settings() -> None:
    with SessionLocal() as db:
        if db.scalar(select(models.User).where(models.User.email == "user@example.com")) is None:
            db.add(models.User(email="user@example.com", user_email="user@example.com", timezone="UTC"))
            db.commit()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, email: str) -> None:
        await websocket.accept()
        self.active_connections[websocket] = email

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.pop(websocket, None)

    async def broadcast(
        self, event: str, payload: dict[str, Any], target_email: str | None = None
    ) -> None:
        message = {"event": event, **payload}
        disconnected = []
        for websocket, email in self.active_connections.items():
            if target_email is not None and email != target_email:
                continue
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)


manager = ConnectionManager()


def note_payload(note: models.Note) -> dict[str, Any]:
    return NoteResponse.model_validate(note).model_dump(mode="json")


VIRTUAL_NOTE_ID = re.compile(r"^(?P<master_id>\d+)_virtual_(?P<date>.+)$")


def parse_note_id(note_id: str) -> tuple[int, datetime | None]:
    match = VIRTUAL_NOTE_ID.fullmatch(note_id)
    if match is None:
        try:
            return int(note_id), None
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid note id") from None
    try:
        original_date = datetime.fromisoformat(match.group("date").replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid virtual occurrence date") from None
    return int(match.group("master_id")), original_date


def next_occurrence(value: datetime, repeat: str) -> datetime:
    if repeat == "daily":
        return value + timedelta(days=1)
    if repeat == "weekly":
        return value + timedelta(weeks=1)
    if repeat == "monthly":
        year = value.year + (value.month == 12)
        month = 1 if value.month == 12 else value.month + 1
        day = min(value.day, monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)
    raise ValueError(f"Unsupported repeat interval: {repeat}")


def expand_note_occurrences(
    note: models.Note,
    target_from: datetime | None = None,
    target_to: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return calendar occurrences while keeping the stored note as the series master."""
    if (
        note.target_datetime is None
        or note.repeat == "none"
        or note.repeat_until is None
    ):
        occurrence = note_payload(note)
        occurrence["series_id"] = None
        return [occurrence]

    exceptions = {
        exception.original_date.isoformat(): exception for exception in note.exceptions
    }
    current = note.target_datetime
    repeat_until = note.repeat_until
    occurrences: list[dict[str, Any]] = []
    occurrence_index = 0
    while current <= repeat_until:
        after_start = target_from is None or current >= target_from
        before_end = target_to is None or current <= target_to
        exception = exceptions.get(current.isoformat())
        if exception is None and current.tzinfo is not None:
            exception = exceptions.get(current.replace(microsecond=0).isoformat())
        event_datetime = exception.new_event_date if exception and exception.new_event_date else current
        if exception and exception.is_deleted:
            current = next_occurrence(current, note.repeat)
            occurrence_index += 1
            continue
        if after_start and before_end:
            occurrence = note_payload(note)
            occurrence["id"] = f"{note.id}_virtual_{current.isoformat()}"
            occurrence["target_datetime"] = event_datetime.isoformat()
            occurrence["series_id"] = note.id
            if exception:
                if exception.new_title is not None:
                    occurrence["title"] = exception.new_title
                if exception.new_text is not None:
                    occurrence["text"] = exception.new_text
                if exception.new_is_active is not None:
                    occurrence["is_active"] = exception.new_is_active
            occurrences.append(occurrence)
        current = next_occurrence(current, note.repeat)
        occurrence_index += 1
    return occurrences


def purge_deleted_notes() -> list[int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    with SessionLocal() as db:
        notes = list(db.scalars(select(models.Note).where(models.Note.deleted_at < cutoff)).all())
        note_ids = [note.id for note in notes]
        for note in notes:
            db.delete(note)
        db.commit()
        return note_ids


async def cleanup_loop() -> None:
    while True:
        for note_id in purge_deleted_notes():
            await manager.broadcast("note_deleted", {"note_id": note_id})
        await asyncio.sleep(24 * 60 * 60)


def generate_recurring_reminders(db: Session, now: datetime) -> None:
    notes = list(
        db.scalars(
            select(models.Note)
            .where(
                models.Note.repeat != "none",
                models.Note.target_datetime.is_not(None),
                models.Note.repeat_until.is_not(None),
                models.Note.is_active.is_(True),
                models.Note.deleted_at.is_(None),
            )
        ).all()
    )
    for note in notes:
        exceptions = {exception.original_date.isoformat(): exception for exception in note.exceptions}
        current = note.target_datetime
        while current <= note.repeat_until:
            exception = exceptions.get(current.isoformat())
            if (
                not exception
                or (
                    not exception.is_deleted
                    and exception.new_is_active is not False
                )
            ):
                event_datetime = exception.new_event_date if exception and exception.new_event_date else current
                for reminder in note.reminders:
                    remind_at = event_datetime - timedelta(minutes=reminder.offset_minutes)
                    delivery = db.scalar(
                        select(models.ReminderDelivery).where(
                            models.ReminderDelivery.reminder_id == reminder.id,
                            models.ReminderDelivery.occurrence_date == current,
                        )
                    )
                    if delivery is None:
                        db.add(
                            models.ReminderDelivery(
                                reminder_id=reminder.id,
                                occurrence_date=current,
                                remind_at=remind_at,
                            )
                        )
            current = next_occurrence(current, note.repeat)
    db.commit()


def process_due_reminders() -> int:
    now = datetime.now(timezone.utc)
    sent_count = 0
    with SessionLocal() as db:
        generate_recurring_reminders(db, now)
        deliveries = list(
            db.scalars(
                select(models.ReminderDelivery)
                .join(models.ReminderDelivery.reminder)
                .join(models.Reminder.note)
                .where(
                    models.ReminderDelivery.is_sent.is_(False),
                    models.ReminderDelivery.remind_at <= now,
                    models.Note.is_active.is_(True),
                    models.Note.deleted_at.is_(None),
                )
            ).all()
        )
        for delivery in deliveries:
            note = delivery.reminder.note
            exception = db.scalar(
                select(models.NoteException).where(
                    models.NoteException.master_note_id == note.id,
                    models.NoteException.original_date == delivery.occurrence_date,
                )
            )
            title = exception.new_title if exception and exception.new_title else note.title
            send_email_notification(note.user_email, title, delivery.remind_at)
            delivery.is_sent = True
            db.commit()
            sent_count += 1
        reminders = list(
            db.scalars(
                select(models.Reminder)
                .join(models.Reminder.note)
                .where(
                    models.Reminder.is_sent.is_(False),
                    models.Reminder.remind_at <= now,
                    models.Note.repeat == "none",
                    models.Note.is_active.is_(True),
                    models.Note.deleted_at.is_(None),
                )
            ).all()
        )
        for reminder in reminders:
            send_email_notification(
                reminder.note.user_email,
                reminder.note.title,
                reminder.remind_at,
            )
            reminder.is_sent = True
            db.commit()
            sent_count += 1
    return sent_count


async def reminder_scheduler_loop() -> None:
    while True:
        process_due_reminders()
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_default_user_settings()
    cleanup_task = asyncio.create_task(cleanup_loop())
    reminder_task = asyncio.create_task(reminder_scheduler_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        reminder_task.cancel()
        await asyncio.gather(cleanup_task, reminder_task, return_exceptions=True)


app = FastAPI(title="Notetaker API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    if any("email" in error.get("loc", ()) for error in exc.errors()):
        return JSONResponse(status_code=400, content={"detail": "Некорректный формат email"})
    return await request_validation_exception_handler(request, exc)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}


def get_current_email(x_user_email: str | None = Header(default=None)) -> str:
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Некорректный формат email")
    try:
        return normalize_email(x_user_email)
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректный формат email") from None


def get_user_settings(db: Session, current_email: str) -> models.User:
    user = db.scalar(select(models.User).where(models.User.email == current_email))
    if user is None:
        user = models.User(email=current_email, user_email=current_email, timezone="UTC")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@app.get("/api/user/settings", response_model=UserSettingsResponse)
def read_user_settings(
    current_email: str = Depends(get_current_email), db: Session = Depends(get_db)
) -> models.User:
    return get_user_settings(db, current_email)


@app.put("/api/user/settings", response_model=UserSettingsResponse)
def update_user_settings(
    settings_data: UserSettingsUpdate,
    current_email: str = Depends(get_current_email),
    db: Session = Depends(get_db),
) -> models.User:
    user = get_user_settings(db, current_email)
    user.email = settings_data.email
    user.user_email = settings_data.email
    user.timezone = settings_data.timezone
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists") from None
    db.refresh(user)
    return user


def get_note_or_404(note_id: int, current_email: str, db: Session) -> models.Note:
    note = db.scalar(
        select(models.Note).where(models.Note.id == note_id, models.Note.user_email == current_email)
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def resolve_tags(tag_ids: list[int], current_email: str, db: Session) -> list[models.Tag]:
    if not tag_ids:
        return []
    tags = list(
        db.scalars(
            select(models.Tag).where(
                models.Tag.id.in_(tag_ids), models.Tag.user_email == current_email
            )
        ).all()
    )
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=404, detail="One or more tags not found")
    return tags


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    try:
        email = normalize_email(websocket.query_params.get("email", ""))
    except ValueError:
        await websocket.close(code=1008, reason="Authentication required")
        return
    await manager.connect(websocket, email)
    try:
        while True:
            message = json.loads(await websocket.receive_text())
            if message.get("event") == "reminder_dismissed" and message.get("reminder_key"):
                await manager.broadcast(
                    "reminder_dismissed",
                    {"reminder_key": message["reminder_key"]},
                    email,
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/notes", response_model=list[NoteResponse])
def list_notes(
    tag_id: int | None = None,
    tag_ids: list[int] | None = Query(default=None),
    is_active: bool | None = None,
    search: str | None = Query(default=None, max_length=255),
    target_from: datetime | None = Query(default=None),
    target_to: datetime | None = Query(default=None),
    sort_by: str = Query(default="updated_at_desc", pattern=r"^(event_date_asc|event_date_desc|updated_at_desc)$"),
    expand_recurrences: bool = Query(default=False),
    current_email: str = Depends(get_current_email),
    db: Session = Depends(get_db),
) -> list[models.Note] | list[dict[str, Any]]:
    query = select(models.Note).where(
        models.Note.deleted_at.is_(None), models.Note.user_email == current_email
    )
    selected_tag_ids = tag_ids or ([] if tag_id is None else [tag_id])
    if selected_tag_ids:
        query = query.join(models.Note.tags).where(models.Tag.id.in_(selected_tag_ids))
    if is_active is not None:
        query = query.where(models.Note.is_active == is_active)
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                models.Note.title.ilike(search_pattern),
                models.Note.text.ilike(search_pattern),
            )
        )
    if target_from is not None and not expand_recurrences:
        query = query.where(models.Note.target_datetime >= target_from)
    if target_to is not None and not expand_recurrences:
        query = query.where(models.Note.target_datetime <= target_to)
    sort_column = models.Note.updated_at
    sort_direction = desc
    if sort_by == "event_date_asc":
        sort_column = models.Note.target_datetime
        sort_direction = asc
    elif sort_by == "event_date_desc":
        sort_column = models.Note.target_datetime
    notes = list(
        db.scalars(query.order_by(sort_direction(sort_column).nullslast(), models.Note.id)).unique().all()
    )
    if not expand_recurrences:
        return notes
    expanded = []
    for note in notes:
        expanded.extend(expand_note_occurrences(note, target_from, target_to))
    return expanded


@app.get("/api/notes/trash", response_model=list[NoteResponse])
def list_deleted_notes(
    current_email: str = Depends(get_current_email), db: Session = Depends(get_db)
) -> list[models.Note]:
    query = select(models.Note).where(
        models.Note.deleted_at.is_not(None), models.Note.user_email == current_email
    )
    return list(db.scalars(query.order_by(models.Note.updated_at.desc())).unique().all())


@app.post("/api/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    current_email: str = Depends(get_current_email),
    db: Session = Depends(get_db),
) -> models.Note:
    note = models.Note(
        user_email=current_email,
        title=note_data.title,
        text=note_data.text,
        target_datetime=note_data.target_datetime,
        repeat=note_data.repeat,
        repeat_until=note_data.repeat_until,
        is_active=note_data.is_active,
        tags=resolve_tags(note_data.tag_ids, current_email, db),
    )
    note.reminders = [models.Reminder(**reminder.model_dump()) for reminder in note_data.reminders]
    db.add(note)
    db.commit()
    db.refresh(note)
    await manager.broadcast("note_created", {"note": note_payload(note)}, current_email)
    return note


@app.put("/api/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    current_email: str = Depends(get_current_email),
    db: Session = Depends(get_db),
) -> models.Note:
    master_id, original_date = parse_note_id(note_id)
    note = get_note_or_404(master_id, current_email, db)
    if note.version != note_data.version:
        raise HTTPException(status_code=409, detail="Note version conflict")
    if original_date is not None:
        exception = db.scalar(
            select(models.NoteException).where(
                models.NoteException.master_note_id == master_id,
                models.NoteException.original_date == original_date,
            )
        )
        if exception is None:
            exception = models.NoteException(
                master_note_id=master_id, original_date=original_date
            )
            db.add(exception)
        if "title" in note_data.model_fields_set:
            exception.new_title = note_data.title
        if "text" in note_data.model_fields_set:
            exception.new_text = note_data.text
        if "target_datetime" in note_data.model_fields_set:
            exception.new_event_date = note_data.target_datetime
        if "is_active" in note_data.model_fields_set:
            exception.new_is_active = note_data.is_active
        db.commit()
        db.refresh(note)
        occurrence = next(
            (
                item
                for item in expand_note_occurrences(note)
                if item["id"] == note_id
            ),
            None,
        )
        if occurrence is None:
            raise HTTPException(status_code=404, detail="Occurrence not found")
        await manager.broadcast("note_updated", {"note": occurrence}, current_email)
        return occurrence
    updates = note_data.model_dump(
        exclude_unset=True,
        exclude={"version", "tag_ids", "reminders", "repeat", "repeat_until"},
    )
    for field, value in updates.items():
        setattr(note, field, value)
    if "repeat" in note_data.model_fields_set:
        note.repeat = note_data.repeat if note_data.repeat is not None else "none"
    if "repeat_until" in note_data.model_fields_set:
        note.repeat_until = note_data.repeat_until
    if note_data.tag_ids is not None:
        note.tags = resolve_tags(note_data.tag_ids, current_email, db)
    if note_data.reminders is not None:
        note.reminders.clear()
        note.reminders.extend(
            models.Reminder(**reminder.model_dump()) for reminder in note_data.reminders
        )
    note.version += 1
    db.commit()
    db.refresh(note)
    await manager.broadcast("note_updated", {"note": note_payload(note)}, current_email)
    return note


@app.delete("/api/notes/{note_id}", response_model=NoteResponse)
async def delete_note(
    note_id: str, current_email: str = Depends(get_current_email), db: Session = Depends(get_db)
) -> models.Note:
    master_id, original_date = parse_note_id(note_id)
    note = get_note_or_404(master_id, current_email, db)
    if original_date is not None:
        exception = db.scalar(
            select(models.NoteException).where(
                models.NoteException.master_note_id == master_id,
                models.NoteException.original_date == original_date,
            )
        )
        if exception is None:
            exception = models.NoteException(
                master_note_id=master_id, original_date=original_date
            )
            db.add(exception)
        exception.is_deleted = True
        db.commit()
        occurrence = note_payload(note)
        occurrence["id"] = note_id
        occurrence["series_id"] = master_id
        await manager.broadcast("note_deleted", {"note": occurrence}, current_email)
        return occurrence
    note.deleted_at = datetime.now().astimezone()
    note.is_active = False
    note.version += 1
    db.commit()
    db.refresh(note)
    await manager.broadcast("note_deleted", {"note": note_payload(note)}, current_email)
    return note


@app.post("/api/notes/{note_id}/restore", response_model=NoteResponse)
async def restore_note(
    note_id: str, current_email: str = Depends(get_current_email), db: Session = Depends(get_db)
) -> models.Note:
    master_id, original_date = parse_note_id(note_id)
    note = get_note_or_404(master_id, current_email, db)
    if original_date is not None:
        exception = db.scalar(
            select(models.NoteException).where(
                models.NoteException.master_note_id == master_id,
                models.NoteException.original_date == original_date,
            )
        )
        if exception is None:
            raise HTTPException(status_code=404, detail="Occurrence not found")
        exception.is_deleted = False
        db.commit()
        occurrence = next(
            item for item in expand_note_occurrences(note) if item["id"] == note_id
        )
        await manager.broadcast("note_updated", {"note": occurrence}, current_email)
        return occurrence
    note.deleted_at = None
    note.is_active = True
    note.version += 1
    db.commit()
    db.refresh(note)
    await manager.broadcast("note_updated", {"note": note_payload(note)}, current_email)
    return note


@app.delete("/api/notes/{note_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanently_delete_note(
    note_id: str, current_email: str = Depends(get_current_email), db: Session = Depends(get_db)
) -> None:
    master_id, original_date = parse_note_id(note_id)
    note = get_note_or_404(master_id, current_email, db)
    if original_date is not None:
        exception = db.scalar(
            select(models.NoteException).where(
                models.NoteException.master_note_id == master_id,
                models.NoteException.original_date == original_date,
            )
        )
        if exception is not None:
            db.delete(exception)
            db.commit()
        await manager.broadcast("note_updated", {"note": note_payload(note)}, current_email)
        return
    db.delete(note)
    db.commit()
    await manager.broadcast("note_deleted", {"note_id": master_id}, current_email)


@app.get("/api/tags", response_model=list[TagResponse])
def list_tags(
    current_email: str = Depends(get_current_email), db: Session = Depends(get_db)
) -> list[models.Tag]:
    return list(
        db.scalars(
            select(models.Tag)
            .where(models.Tag.user_email == current_email)
            .order_by(models.Tag.name)
        ).all()
    )


@app.post("/api/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag_data: TagCreate,
    current_email: str = Depends(get_current_email),
    db: Session = Depends(get_db),
) -> models.Tag:
    tag = models.Tag(user_email=current_email, **tag_data.model_dump())
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tag already exists") from None
    db.refresh(tag)
    return tag


@app.put("/api/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    current_email: str = Depends(get_current_email),
    db: Session = Depends(get_db),
) -> models.Tag:
    tag = db.scalar(
        select(models.Tag).where(models.Tag.id == tag_id, models.Tag.user_email == current_email)
    )
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    for field, value in tag_data.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tag already exists") from None
    db.refresh(tag)
    return tag


@app.delete("/api/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int, current_email: str = Depends(get_current_email), db: Session = Depends(get_db)
) -> None:
    tag = db.scalar(
        select(models.Tag).where(models.Tag.id == tag_id, models.Tag.user_email == current_email)
    )
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    tag.notes.clear()
    db.delete(tag)
    db.commit()