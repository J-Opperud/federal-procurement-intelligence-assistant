"""Focused tests for source-document API persistence and validation."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ProcurementNotice, SourceDocument
from app.routers.source_documents import create_notice_source
from app.schemas.source_documents import SourceDocumentCreate
from app.services.source_ingestion import IndexingResult, content_sha256
from app.utils.exceptions import AppException


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'source-api.db').as_posix()}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        yield session
    engine.dispose()


def create_notice(db_session):
    notice = ProcurementNotice(
        sam_notice_id="SAM-SOURCE-API-001",
        title="Cloud migration support",
        notice_type="Solicitation",
    )
    db_session.add(notice)
    db_session.commit()
    return notice


def test_source_request_strips_text_and_rejects_blank_values():
    payload = SourceDocumentCreate(
        title="  Attachment  ",
        source_type="  PDF  ",
        source_url="https://example.gov/source.pdf",
        content="  Required text  ",
    )
    assert payload.title == "Attachment"
    assert payload.source_type == "PDF"
    assert payload.normalized_content() == "Required text"

    with pytest.raises(ValueError, match="blank"):
        SourceDocumentCreate(
            title="   ", source_type="PDF", content="text"
        )
    with pytest.raises(ValueError, match="blank"):
        SourceDocumentCreate(
            title="Attachment", source_type="PDF", content="  "
        )


def test_source_is_persisted_when_vector_indexing_fails(db_session, monkeypatch):
    from app.routers import source_documents

    notice = create_notice(db_session)
    payload = SourceDocumentCreate(
        title="Requirements", source_type="attachment", content="Secure hosting required."
    )

    def fail_indexing(*args, **kwargs):
        raise RuntimeError("vector store unavailable")

    monkeypatch.setattr(source_documents, "index_source_document", fail_indexing)

    with pytest.raises(AppException) as error:
        create_notice_source(
            notice.sam_notice_id, payload, current_user=None, db=db_session
        )

    assert error.value.status_code == 503
    assert "Retry POST" in error.value.detail
    saved = db_session.scalar(
        select(SourceDocument).where(SourceDocument.procurement_notice_id == notice.id)
    )
    assert saved is not None
    assert saved.extracted_text == "Secure hosting required."
    assert saved.indexed_at is None
    assert saved.content_hash is None


def test_source_creation_returns_indexing_result(db_session, monkeypatch):
    from app.routers import source_documents

    notice = create_notice(db_session)

    def fake_index(db, source, content):
        source.content_hash = content_sha256(content)
        source.indexed_at = datetime.now(timezone.utc)
        db.flush()
        return IndexingResult(chunks_indexed=3, skipped=False, content_hash=source.content_hash)

    monkeypatch.setattr(source_documents, "index_source_document", fake_index)
    response = create_notice_source(
        notice.sam_notice_id,
        SourceDocumentCreate(
            title="Requirements", source_type="attachment", content="Secure hosting required."
        ),
        current_user=None,
        db=db_session,
    )

    assert response.chunks_indexed == 3
    assert response.skipped is False
    assert response.source_document.id > 0
    assert response.source_document.indexed_at is not None
    assert response.source_document.content_hash == content_sha256("Secure hosting required.")
