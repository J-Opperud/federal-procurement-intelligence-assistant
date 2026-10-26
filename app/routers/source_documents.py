"""Authenticated source-document persistence and semantic indexing endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProcurementNotice, SourceDocument
from app.routers.auth import CurrentUser
from app.schemas.source_documents import (
    SourceDocumentCreate,
    SourceDocumentIndexResponse,
    SourceDocumentResponse,
)
from app.services.chroma_evidence_service import index_source_document
from app.utils.exceptions import AppException, NotFoundException

router = APIRouter(prefix="/documents", tags=["Source documents"])
DbSession = Annotated[Session, Depends(get_db)]


def _indexing_failure(source_document_id: int) -> AppException:
    return AppException(
        detail=(
            f"Source document {source_document_id} was saved, but indexing failed. "
            f"Retry POST /documents/source-documents/{source_document_id}/index "
            "after checking the vector database and embedding model."
        ),
        status_code=503,
        code="SOURCE_INDEXING_FAILED",
    )


@router.get(
    "/{sam_notice_id}/sources",
    response_model=list[SourceDocumentResponse],
)
def list_notice_sources(
    sam_notice_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[SourceDocumentResponse]:
    """List source metadata for a locally stored procurement notice."""
    notice = db.scalar(
        select(ProcurementNotice).where(
            ProcurementNotice.sam_notice_id == sam_notice_id
        )
    )
    if notice is None:
        raise NotFoundException("Procurement notice", sam_notice_id)

    sources = db.scalars(
        select(SourceDocument)
        .where(SourceDocument.procurement_notice_id == notice.id)
        .order_by(SourceDocument.id.desc())
    ).all()
    return [SourceDocumentResponse.model_validate(source) for source in sources]


@router.post(
    "/{sam_notice_id}/sources",
    response_model=SourceDocumentIndexResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_notice_source(
    sam_notice_id: str,
    payload: SourceDocumentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> SourceDocumentIndexResponse:
    """Persist extracted source text and attempt semantic indexing immediately."""
    notice = db.scalar(
        select(ProcurementNotice).where(
            ProcurementNotice.sam_notice_id == sam_notice_id
        )
    )
    if notice is None:
        raise NotFoundException("Procurement notice", sam_notice_id)

    content = payload.normalized_content()
    source = SourceDocument(
        procurement_notice_id=notice.id,
        title=payload.title.strip(),
        source_type=payload.source_type.strip(),
        source_url=str(payload.source_url) if payload.source_url else None,
        extracted_text=content,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    try:
        result = index_source_document(db, source, content)
        db.commit()
        db.refresh(source)
    except Exception as exc:
        # The source record remains saved with indexed_at=None so a later retry
        # can recover without losing the ingested source content.
        db.rollback()
        raise _indexing_failure(source.id) from exc

    return SourceDocumentIndexResponse(
        source_document=SourceDocumentResponse.model_validate(source),
        chunks_indexed=result.chunks_indexed,
        skipped=result.skipped,
    )


@router.post(
    "/source-documents/{source_document_id}/index",
    response_model=SourceDocumentIndexResponse,
)
def reindex_source_document(
    source_document_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SourceDocumentIndexResponse:
    """Retry indexing a saved source document or refresh its current vectors."""
    source = db.get(SourceDocument, source_document_id)
    if source is None:
        raise NotFoundException("Source document", source_document_id)
    if not source.extracted_text:
        raise AppException(
            detail="Source document has no extracted text to index.",
            status_code=422,
            code="SOURCE_TEXT_MISSING",
        )

    try:
        result = index_source_document(db, source, source.extracted_text)
        db.commit()
        db.refresh(source)
    except Exception as exc:
        db.rollback()
        raise _indexing_failure(source.id) from exc

    return SourceDocumentIndexResponse(
        source_document=SourceDocumentResponse.model_validate(source),
        chunks_indexed=result.chunks_indexed,
        skipped=result.skipped,
    )
