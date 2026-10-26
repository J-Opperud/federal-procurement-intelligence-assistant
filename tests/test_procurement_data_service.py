"""Tests for turning structured procurement rows into searchable source text."""

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ProcurementNotice, SourceDocument
from app.services.procurement_data_service import (
    procurement_notice_search_text,
    upsert_notice_source_document,
)


def test_procurement_notice_search_text_includes_available_fields():
    notice = ProcurementNotice(
        sam_notice_id="SAM-123",
        title="Secure network support",
        notice_type="Sources Sought",
        department="Department of Defense",
        posted_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
        response_deadline=None,
        source_url="https://sam.gov/notice/SAM-123",
        description="Provide secure network maintenance.",
    )

    text = procurement_notice_search_text(notice)

    assert "SAM.gov notice ID: SAM-123" in text
    assert "Title: Secure network support" in text
    assert "Notice type: Sources Sought" in text
    assert "Department: Department of Defense" in text
    assert "Description: Provide secure network maintenance." in text
    assert "Response deadline:" not in text


def test_upsert_notice_source_document_creates_then_updates_source():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    try:
        with Session(engine) as db:
            notice = ProcurementNotice(
                sam_notice_id="SAM-123",
                title="First title",
                notice_type="Solicitation",
                description="Original description",
            )
            db.add(notice)
            db.flush()

            first = upsert_notice_source_document(db, notice)
            first_id = first.id
            assert "Original description" in first.extracted_text
            assert first.source_type == "sam_notice"

            notice.description = "Updated description"
            notice.title = "Updated title"
            second = upsert_notice_source_document(db, notice)

            assert second.id == first_id
            assert "Updated description" in second.extracted_text
            assert second.title == "SAM.gov notice: Updated title"
            sources = db.scalars(
                select(SourceDocument).where(
                    SourceDocument.procurement_notice_id == notice.id,
                    SourceDocument.source_type == "sam_notice",
                )
            ).all()
            assert len(sources) == 1
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
