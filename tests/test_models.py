

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ProcurementNotice, SourceDocument, User


@pytest.fixture
def db_session(tmp_path):
    """Create an isolated SQLite database for each test."""
    database_path = tmp_path / "test_scout.db"
    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
    )
    Base.metadata.create_all(bind=test_engine)

    TestSession = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    with TestSession() as session:
        yield session

    test_engine.dispose()


def test_models_create_expected_tables(db_session):
    tables = inspect(db_session.get_bind()).get_table_names()

    assert "users" in tables
    assert "procurement_notices" in tables
    assert "source_documents" in tables


def test_user_username_must_be_unique(db_session):
    db_session.add(
        User(username="researcher", hashed_password="hash-one")
    )
    db_session.commit()

    db_session.add(
        User(username="researcher", hashed_password="hash-two")
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_sam_notice_id_must_be_unique(db_session):
    notice_data = {
        "sam_notice_id": "SAM-123",
        "title": "Example procurement",
        "notice_type": "RFI",
    }

    db_session.add(ProcurementNotice(**notice_data))
    db_session.commit()

    db_session.add(ProcurementNotice(**notice_data))

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_notice_can_have_source_documents(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-456",
        title="Research equipment",
        notice_type="RFP",
    )
    notice.source_documents.append(
        SourceDocument(
            title="Notice details",
            source_type="sam_notice",
            source_url="https://example.gov/notice/456",
            content_hash="example-hash",
        )
    )

    db_session.add(notice)
    db_session.commit()

    assert len(notice.source_documents) == 1
    assert notice.source_documents[0].title == "Notice details"
    assert notice.source_documents[0].procurement_notice_id == notice.id

def test_research_query_belongs_to_user(db_session):
    from app.models import ResearchQuery

    user = User(
        username="analyst",
        hashed_password="test-hash",
    )
    user.research_queries.append(
        ResearchQuery(
            question="What opportunities are open?",
            answer="Two matching opportunities were found.",
            sources_json='[{"title": "Example notice"}]',
            sufficient_evidence=True,
        )
    )

    db_session.add(user)
    db_session.commit()

    assert len(user.research_queries) == 1
    assert user.research_queries[0].question == (
        "What opportunities are open?"
    )
    assert user.research_queries[0].user_id == user.id


def test_research_query_requires_a_user(db_session):
    from app.models import ResearchQuery

    query = ResearchQuery(
        question="What opportunities are open?",
        answer="No results.",
        sources_json="[]",
        sufficient_evidence=False,
    )
    db_session.add(query)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
