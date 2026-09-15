import os
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:jojo19x@localhost:5432/notetaker_db",
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def add_missing_user_email_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in ("users", "notes", "tags"):
            if not inspector.has_table(table):
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "user_email" not in columns:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN user_email VARCHAR(255)")
                )
                connection.execute(
                    text(f"UPDATE {table} SET user_email = email WHERE user_email IS NULL")
                    if table == "users"
                    else text(
                        f"UPDATE {table} SET user_email = 'user@example.com' WHERE user_email IS NULL"
                    )
                )

        if inspector.has_table("notes"):
            columns = {column["name"] for column in inspector.get_columns("notes")}
            if "repeat" not in columns:
                connection.execute(
                    text("ALTER TABLE notes ADD COLUMN repeat VARCHAR(20) NOT NULL DEFAULT 'none'")
                )
            if "repeat_until" not in columns:
                connection.execute(text("ALTER TABLE notes ADD COLUMN repeat_until TIMESTAMP WITH TIME ZONE"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()