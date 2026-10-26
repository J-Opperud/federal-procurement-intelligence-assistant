
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResearchQuery
from app.routers.auth import CurrentUser
from app.schemas.research import (
    ResearchQueryCreate,
    ResearchQueryResponse,
)

router = APIRouter(
    prefix="/research",
    tags=["Research"],
)

DbSession = Annotated[Session, Depends(get_db)]

@router.get(
    "/queries",
    response_model=list[ResearchQueryResponse],
)
def list_research_queries(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ResearchQueryResponse]:
    """Return only research history belonging to the authenticated user."""
    statement = (
        select(ResearchQuery)
        .where(ResearchQuery.user_id == current_user.id)
        .order_by(ResearchQuery.created_at.desc(), ResearchQuery.id.desc())
        .limit(limit)
        .offset(offset)
    )

    queries = db.scalars(statement).all()

    return [
        ResearchQueryResponse(
            id=query.id,
            user_id=query.user_id,
            question=query.question,
            answer=query.answer,
            sources=json.loads(query.sources_json),
            sufficient_evidence=query.sufficient_evidence,
            created_at=query.created_at,
        )
        for query in queries
    ]
