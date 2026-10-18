from sqlalchemy import create_engine

from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


DATABASE_URL = settings.get_database_url()


# SQLite needs this setting when connections may be used across threads,
# such as when FastAPI handles requests.


connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
    )
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    )
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    )

class Base(DeclarativeBase):
    """Base class for Scout's SQLAlchemy models."""

def get_db():
    """Provide a database session and close it after use."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
