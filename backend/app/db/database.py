import os
from pathlib import Path
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = BACKEND_DIR / "data" / "climatesense.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH}")

_database_url = make_url(DATABASE_URL)
if _database_url.get_backend_name() == "sqlite" and _database_url.database not in (None, "", ":memory:"):
    Path(_database_url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _database_url.get_backend_name() == "sqlite" else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def initialize_database() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
