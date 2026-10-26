"""Authenticated procurement document search and synchronization endpoints."""

import logging

from datetime import datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from sqlalchemy.orm import Session
from app.services.chroma_evidence_service import index_procurement_notice

from app.database import get_db
from app.models import ProcurementNotice

from app.routers.auth import CurrentUser
from app.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    DocumentSearchParams,
    DocumentSyncRequest,
    DocumentSyncResponse,
)
from app.schemas.sam_gov import SamOpportunity
from app.services.procurement_mapping import map_sam_opportunity
from app.services.procurement_sync import upsert_procurement_notice

from app.services.chroma_evidence_service import index_procurement_notice

from app.services.sam_gov import SamGovClient

router = APIRouter(prefix="/documents", tags=["Documents"])
DbSession = Annotated[Session, Depends(get_db)]


logger = logging.getLogger(__name__)

def _utc_day_start(value) -> datetime:
    """Convert a calendar date to the start of that day in UTC."""
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


@router.get("", response_model=DocumentListResponse)
def search_documents(
    current_user: CurrentUser,
    db: DbSession,
    params: Annotated[DocumentSearchParams, Query()],
) -> DocumentListResponse:
    """Search locally stored notices without calling SAM.gov."""
    conditions = []

    if params.keyword:
        pattern = f"%{params.keyword}%"
        conditions.append(
            or_(
                ProcurementNotice.title.ilike(pattern),
                ProcurementNotice.description.ilike(pattern),
                ProcurementNotice.department.ilike(pattern),
                ProcurementNotice.sam_notice_id.ilike(pattern),
            )
        )

    if params.notice_type:
        conditions.append(ProcurementNotice.notice_type.ilike(params.notice_type))

    if params.posted_from:
        conditions.append(
            ProcurementNotice.posted_date >= _utc_day_start(params.posted_from)
        )

    if params.posted_to:
        # Exclusive upper bound includes every timestamp on posted_to.
        next_day = params.posted_to + timedelta(days=1)
        conditions.append(
            ProcurementNotice.posted_date < _utc_day_start(next_day)
        )

    filtered = select(ProcurementNotice).where(*conditions)
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0

    statement = (
        filtered
        .order_by(
            ProcurementNotice.posted_date.desc().nulls_last(),
            ProcurementNotice.id.desc(),
        )
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    )
    notices = db.scalars(statement).all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(notice) for notice in notices],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{sam_notice_id}", response_model=DocumentResponse)
def get_document(
    sam_notice_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentResponse:
    """Retrieve a notice already stored in the local database."""
    notice = db.scalar(
        select(ProcurementNotice).where(
            ProcurementNotice.sam_notice_id == sam_notice_id
        )
    )
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement notice not found locally.",
        )
    return DocumentResponse.model_validate(notice)


@router.post("/sync", response_model=DocumentSyncResponse)
def sync_documents(
    payload: DocumentSyncRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentSyncResponse:
    """Fetch notices into SQL, then index their searchable text in ChromaDB."""
    client = SamGovClient()
    result = client.search_opportunities(
        posted_from=payload.posted_from.strftime("%m/%d/%Y"),
        posted_to=payload.posted_to.strftime("%m/%d/%Y"),
        limit=payload.limit,
    )
    opportunities = result["opportunities"]
    inserted_count = 0
    updated_count = 0
    indexed_count = 0
    failed_count = 0
    notices_to_index = []

    for item in opportunities:
        try:
            opportunity = SamOpportunity.model_validate(item)
            if (
                payload.notice_type
                and opportunity.notice_type.casefold() != payload.notice_type.casefold()
            ):
                continue

            # Keep each malformed notice isolated from the remaining batch.
            with db.begin_nested():
                notice, created = upsert_procurement_notice(
                    db, map_sam_opportunity(opportunity)
                )

            notices_to_index.append(notice)
            if created:
                inserted_count += 1
            else:
                updated_count += 1
        except (ValueError, SQLAlchemyError):
            db.rollback()
            failed_count += 1

    stored_notices = db.scalars(
        select(ProcurementNotice)).all()

    for notice in stored_notices:
        index_procurement_notice(db, notice)

    # Commit structured SAM.gov records before attempting vector indexing.
    # If embeddings or Chroma fail, the SQL notice remains available for retry.
    db.commit()

    for notice in notices_to_index:
        try:
            result = index_procurement_notice(db, notice)
            indexed_count += 1
        except Exception:
            logger.exception(
                "Failed to index procurement notice %s",
                notice.sam_notice_id,
            )
            failed_count += 1
            # Do not discard valid SQL records because semantic indexing failed.
            

    return DocumentSyncResponse(
        fetched_count=len(opportunities),
        inserted_count=inserted_count,
        updated_count=updated_count,
        indexed_count=indexed_count,
        failed_count=failed_count,
    )
