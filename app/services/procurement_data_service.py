"""Prepare structured SQL procurement notices as searchable source documents."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProcurementNotice, SourceDocument


def procurement_notice_search_text(notice: ProcurementNotice) -> str:
    """Convert a stored SAM.gov notice into readable, searchable text.

    The SQL notice remains authoritative; this text is a searchable projection
    for semantic retrieval, not a replacement for the structured record.
    """
    fields = [
        ("SAM.gov notice ID", notice.sam_notice_id),
        ("Title", notice.title),
        ("Notice type", notice.notice_type),
        ("Department", notice.department),
        ("Posted date", notice.posted_date.isoformat() if notice.posted_date else None),
        ("Response deadline", notice.response_deadline.isoformat() if notice.response_deadline else None),
        ("Source URL", notice.source_url),
        ("Description", notice.description),
    ]
    return "\n".join(f"{label}: {value.strip()}" for label, value in fields
                     if isinstance(value, str) and value.strip())



def upsert_notice_source_document(
    db: Session, notice: ProcurementNotice,
) -> SourceDocument:
    """Create or refresh the SQL source-document record for a SAM.gov notice.

    Callers own the transaction and must commit after any subsequent indexing
    succeeds or choose to persist the source record separately for retry.
    """
    if notice.id is None:
        db.flush()
    if notice.id is None:
        raise ValueError("Procurement notice must be persisted before indexing.")

    searchable_text = procurement_notice_search_text(notice)
    if not searchable_text.strip():
        raise ValueError("Procurement notice has no searchable text.")

    source_document = db.scalar(
        select(SourceDocument).where(
            SourceDocument.procurement_notice_id == notice.id,
            SourceDocument.source_type == "sam_notice",
        ).order_by(SourceDocument.id.asc())
    )
    source_title = f"SAM.gov notice: {notice.title}"[:500]
    if source_document is None:
        source_document = SourceDocument(
            procurement_notice_id=notice.id,
            title=source_title,
            source_type="sam_notice",
            source_url=notice.source_url,
            extracted_text=searchable_text,
        )
        db.add(source_document)
    else:
        # Updating the text causes the indexer's content hash check to re-index it.
        source_document.title = source_title
        source_document.source_url = notice.source_url
        source_document.extracted_text = searchable_text

    db.flush()
    return source_document
