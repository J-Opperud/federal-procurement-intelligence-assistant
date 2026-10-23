
import pytest
from sqlalchemy import create_engine, select, event

from datetime import datetime, timezone



from app.models import ProcurementNotice

from app.services.procurement_sync import upsert_procurement_notice

from datetime import datetime, timezone


from sqlalchemy.orm import sessionmaker

from app.database import Base

from app.models import ProcurementNotice




@pytest.fixture
def db_session(tmp_path):
    """Create an isolated SQLite database for each test."""
    database_path = tmp_path / "test_scout.db"
    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
    )

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    Base.metadata.create_all(bind=test_engine)

    TestSession = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )



    with TestSession() as session:
        yield session

    test_engine.dispose()




def make_notice(**overrides):
    """Build a valid notice payload for synchronization tests."""
    notice = {
        "sam_notice_id": "SAM-TEST-001",
        "title": "Initial procurement notice",
        "notice_type": "Solicitation",
        "department": "Department of Defense",
        "posted_date": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "response_deadline": datetime(2026, 11, 1, tzinfo=timezone.utc),
        "source_url": "https://sam.gov/notice/SAM-TEST-001",
        "description": "Initial description",
    }
    notice.update(overrides)
    return notice


def test_upsert_inserts_new_notice(db_session):
    notice, created = upsert_procurement_notice(
        db_session,
        make_notice(),
    )

    assert created is True
    assert notice.id is not None
    assert notice.sam_notice_id == "SAM-TEST-001"
    assert notice.title == "Initial procurement notice"

    db_session.commit()

    saved_notice = db_session.scalar(
        select(ProcurementNotice).where(
            ProcurementNotice.sam_notice_id == "SAM-TEST-001"
        )
    )
    assert saved_notice is not None


def test_upsert_updates_existing_notice(db_session):
    original, created = upsert_procurement_notice(
        db_session,
        make_notice(),
    )
    assert created is True

    original_id = original.id

    updated, created = upsert_procurement_notice(
        db_session,
        make_notice(
            title="Updated procurement notice",
            description="Updated description",
        ),
    )

    assert created is False
    assert updated.id == original_id
    assert updated.title == "Updated procurement notice"
    assert updated.description == "Updated description"


def test_repeated_upsert_does_not_create_duplicates(db_session):
    upsert_procurement_notice(db_session, make_notice())
    upsert_procurement_notice(
        db_session,
        make_notice(title="Revised title"),
    )

    db_session.flush()

    notices = db_session.scalars(
        select(ProcurementNotice).where(
            ProcurementNotice.sam_notice_id == "SAM-TEST-001"
        )
    ).all()

    assert len(notices) == 1
    assert notices[0].title == "Revised title"


def test_upsert_rejects_missing_sam_notice_id(db_session):
    import pytest

    with pytest.raises(ValueError, match="sam_notice_id"):
        upsert_procurement_notice(
            db_session,
            make_notice(sam_notice_id=""),
        )
