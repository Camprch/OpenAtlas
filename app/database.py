# app/database.py
from contextlib import contextmanager
from pathlib import Path
import os


from sqlmodel import SQLModel, create_engine, Session

# Resolve the database URL (prefer DB_URL, fallback to local SQLite)
DB_PATH = Path("data/osint.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
db_url = os.getenv("DB_URL")
if db_url:
    DATABASE_URL = db_url
    is_sqlite = DATABASE_URL.startswith("sqlite")
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    is_sqlite = True

# Create the SQLModel engine (SQLite needs check_same_thread disabled)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    # check_same_thread uniquement pour SQLite
    connect_args={"check_same_thread": False} if is_sqlite else {},
)


def init_db() -> None:
    # Import models so SQLModel registers table metadata
    from app.models.message import Message  # noqa: F401
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Session:
    # Context-managed session helper for non-FastAPI use
    with Session(engine) as session:
        yield session


# Dépendance FastAPI
def get_db():
    # FastAPI dependency that yields a DB session
    with Session(engine) as session:
        yield session
