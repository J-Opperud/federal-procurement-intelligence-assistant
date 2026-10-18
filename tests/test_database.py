
from sqlalchemy import text

from app.database import Base, SessionLocal, engine, get_db

from unittest.mock import MagicMock, patch

def test_engine_uses_configured_database_url():
    assert str(engine.url).startswith("sqlite:")


def test_database_session_can_execute_query():
    with SessionLocal() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_base_is_sqlalchemy_declarative_base():
    assert hasattr(Base, "metadata")




from unittest.mock import MagicMock, patch


def test_get_db_closes_session():
    mock_session = MagicMock()

    with patch("app.database.SessionLocal", return_value=mock_session):
        db_generator = get_db()
        next(db_generator)
        db_generator.close()

    mock_session.close.assert_called_once()
