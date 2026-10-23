from sqlalchemy import create_engine

from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

from sqlalchemy import event

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
@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign-key enforcement on every SQLite connection."""
    if engine.dialect.name != "sqlite":
        return

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()

class Base(DeclarativeBase):
    """Base class for Scout's SQLAlchemy models."""

def get_db():
    """Provide a database session and close it after use."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
