
import pytest

from sqlalchemy import create_engine, inspect, select, event


from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import sessionmaker

from app.database import Base

from app.models import ProcurementNotice, SourceDocument, User, ResearchQuery


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





def test_notice_can_be_retrieved_and_updated(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-CRUD-001",
        title="Original title",
        notice_type="RFP",
    )
    db_session.add(notice)
    db_session.commit()

    notice_id = notice.id

    retrieved = db_session.get(ProcurementNotice, notice_id)
    assert retrieved is not None
    assert retrieved.sam_notice_id == "SAM-CRUD-001"
    assert retrieved.title == "Original title"

    retrieved.title = "Updated title"
    db_session.commit()
    db_session.refresh(retrieved)

    assert retrieved.title == "Updated title"


def test_user_creation_timestamp_is_populated(db_session):
    user = User(
        username="timestamp_test",
        hashed_password="test-hash",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.created_at is not None
    assert isinstance(user.created_at, datetime)


def test_notice_last_fetched_timestamp_is_populated(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-FETCH-001",
        title="Timestamp test",
        notice_type="RFI",
    )
    db_session.add(notice)
    db_session.commit()
    db_session.refresh(notice)

    assert notice.last_fetched_at is not None
    assert isinstance(notice.last_fetched_at, datetime)

def test_username_is_normalized_before_persisting(db_session):
    user = User(
        username="  Researcher  ",
        hashed_password="test-hash",
    )
    db_session.add(user)
    db_session.commit()

    db_session.refresh(user)

    assert user.username == "researcher"


def test_username_case_insensitive_uniqueness(db_session):
    db_session.add(
        User(username="Researcher", hashed_password="hash-one")
    )
    db_session.commit()

    db_session.add(
        User(username="researcher", hashed_password="hash-two")
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_username_normalization_applies_on_update(db_session):
    user = User(
        username="researcher",
        hashed_password="test-hash",
    )
    db_session.add(user)
    db_session.commit()

    user.username = "  NEWRESEARCHER  "
    db_session.commit()

    assert user.username == "newresearcher"



def test_user_creation_timestamp_is_utc(db_session):
    user = User(
        username="utc_user",
        hashed_password="test-hash",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.created_at is not None
    assert user.created_at.tzinfo is timezone.utc
    assert user.created_at.utcoffset().total_seconds() == 0


def test_research_query_creation_timestamp_is_utc(db_session):
    user = User(
        username="utc_researcher",
        hashed_password="test-hash",
    )
    db_session.add(user)
    db_session.flush()

    query = ResearchQuery(
        user_id=user.id,
        question="Test UTC timestamp",
        answer="Test answer",
        sources_json="[]",
        sufficient_evidence=False,
    )
    db_session.add(query)
    db_session.commit()
    db_session.refresh(query)

    assert query.created_at is not None
    assert query.created_at.tzinfo is timezone.utc
    assert query.created_at.utcoffset().total_seconds() == 0


def test_utc_datetime_rejects_naive_values(db_session):
    user = User(
        username="naive_timestamp",
        hashed_password="test-hash",
        created_at=datetime(2026, 1, 1),
    )
    db_session.add(user)

    with pytest.raises(StatementError):
        db_session.commit()

    db_session.rollback()


def test_procurement_notice_insert_and_retrieve(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-TEST-001",
        title="Test procurement opportunity",
        notice_type="Solicitation",
        department="Department of Defense",
        description="Test description",
    )
    db_session.add(notice)
    db_session.commit()

    retrieved = db_session.scalar(
        select(ProcurementNotice).where(
            ProcurementNotice.sam_notice_id == "SAM-TEST-001"
        )
    )

    assert retrieved is not None
    assert retrieved.title == "Test procurement opportunity"
    assert retrieved.department == "Department of Defense"


def test_procurement_notice_update(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-TEST-002",
        title="Original title",
        notice_type="Solicitation",
    )
    db_session.add(notice)
    db_session.commit()

    notice.title = "Updated title"
    db_session.commit()
    db_session.refresh(notice)

    assert notice.title == "Updated title"


def test_procurement_notice_rejects_duplicate_sam_notice_id(db_session):
    db_session.add(
        ProcurementNotice(
            sam_notice_id="SAM-DUPLICATE-001",
            title="First notice",
            notice_type="Solicitation",
        )
    )
    db_session.commit()

    db_session.add(
        ProcurementNotice(
            sam_notice_id="SAM-DUPLICATE-001",
            title="Duplicate notice",
            notice_type="Solicitation",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_procurement_notice_allows_nullable_optional_fields(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-TEST-OPTIONAL-001",
        title="Minimal notice",
        notice_type="Solicitation",
    )
    db_session.add(notice)
    db_session.commit()
    db_session.refresh(notice)

    assert notice.department is None
    assert notice.posted_date is None
    assert notice.response_deadline is None
    assert notice.source_url is None
    assert notice.description is None




def test_source_document_links_to_procurement_notice(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-SOURCE-001",
        title="Notice with source",
        notice_type="Solicitation",
    )
    db_session.add(notice)
    db_session.flush()

    document = SourceDocument(
        procurement_notice_id=notice.id,
        title="Solicitation attachment",
        source_type="attachment",
        source_url="https://example.com/solicitation.pdf",
        content_hash="abc123",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    assert document.procurement_notice_id == notice.id
    assert document.procurement_notice is not None
    assert document.procurement_notice.sam_notice_id == "SAM-SOURCE-001"
    assert document in notice.source_documents


def test_source_document_can_exist_without_notice(db_session):
    document = SourceDocument(
        procurement_notice_id=None,
        title="Federal Acquisition Regulation reference",
        source_type="regulation",
        source_url="https://example.com/far",
        content_hash="far-hash-001",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    assert document.id is not None
    assert document.procurement_notice_id is None
    assert document.procurement_notice is None


def test_source_document_rejects_invalid_notice_foreign_key(db_session):
    document = SourceDocument(
        procurement_notice_id=999999,
        title="Orphaned attachment",
        source_type="attachment",
    )
    db_session.add(document)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_deleting_notice_deletes_associated_source_documents(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-CASCADE-001",
        title="Notice to delete",
        notice_type="Solicitation",
    )
    db_session.add(notice)
    db_session.flush()

    document = SourceDocument(
        procurement_notice_id=notice.id,
        title="Associated attachment",
        source_type="attachment",
    )
    db_session.add(document)
    db_session.commit()

    document_id = document.id

    db_session.delete(notice)
    db_session.commit()

    assert db_session.get(SourceDocument, document_id) is None

def test_research_queries_are_associated_with_their_owners(db_session):
    user_one = User(
        username="owner_one",
        hashed_password="hashed-password-one",
    )
    user_two = User(
        username="owner_two",
        hashed_password="hashed-password-two",
    )

    query_one = ResearchQuery(
        user=user_one,
        question="Find cybersecurity contracts",
        answer="Results for user one",
        sources_json="[]",
        sufficient_evidence=True,
    )
    query_two = ResearchQuery(
        user=user_two,
        question="Find medical supply contracts",
        answer="Results for user two",
        sources_json="[]",
        sufficient_evidence=False,
    )

    db_session.add_all([user_one, user_two])
    db_session.commit()

    db_session.refresh(user_one)
    db_session.refresh(user_two)

    assert query_one.user_id == user_one.id
    assert query_two.user_id == user_two.id

    assert query_one in user_one.research_queries
    assert query_two in user_two.research_queries

    assert query_two not in user_one.research_queries
    assert query_one not in user_two.research_queries


def test_research_query_rejects_nonexistent_user_id(db_session):
    query = ResearchQuery(
        user_id=999999,
        question="Test invalid user reference",
        answer="Test answer",
        sources_json="[]",
        sufficient_evidence=False,
    )
    db_session.add(query)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

def test_research_query_persists_required_fields(db_session):
    user = User(
        username="query_fields_test",
        hashed_password="test-hash",
    )
    db_session.add(user)
    db_session.flush()

    query = ResearchQuery(
        user_id=user.id,
        question="Find open cybersecurity contracts",
        answer="Two matching opportunities found.",
        sources_json='[{"sam_notice_id": "SAM-123"}]',
        sufficient_evidence=True,
    )
    db_session.add(query)
    db_session.commit()

    query_id = query.id
    user_id = user.id
    db_session.expire_all()

    saved_query = db_session.get(ResearchQuery, query_id)

    assert saved_query is not None
    assert saved_query.user_id == user_id
    assert saved_query.question == "Find open cybersecurity contracts"
    assert saved_query.answer == "Two matching opportunities found."
    assert saved_query.sources_json == (
        '[{"sam_notice_id": "SAM-123"}]'
    )
    assert saved_query.sufficient_evidence is True
    assert saved_query.created_at is not None
    assert saved_query.created_at.tzinfo is timezone.utc
def test_models_have_expected_primary_and_foreign_keys():
    expected = {
        User: {"primary_key": ["id"], "foreign_keys": {}},
        ProcurementNotice: {"primary_key": ["id"], "foreign_keys": {}},
        SourceDocument: {
            "primary_key": ["id"],
            "foreign_keys": {
                "procurement_notice_id": "procurement_notices.id",
            },
        },
        ResearchQuery: {
            "primary_key": ["id"],
            "foreign_keys": {
                "user_id": "users.id",
            },
        },
    }

    for model, constraints in expected.items():
        table = model.__table__

        assert [column.name for column in table.primary_key] == (
            constraints["primary_key"]
        )

        actual_foreign_keys = {
            foreign_key.parent.name: foreign_key.target_fullname
            for foreign_key in table.foreign_keys
        }

        assert actual_foreign_keys == constraints["foreign_keys"]
