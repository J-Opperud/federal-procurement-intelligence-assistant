"""Authenticated RAG question answering for procurement intelligence."""
import logging
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ResearchQuery
from app.routers.auth import CurrentUser
from app.schemas.ask import AskRequest, AskResponse, SourceReference
from app.services.evidence_assessment import assess_evidence
from app.services.ollama_client import OllamaError, generate_answer
from app.services.source_ingestion import retrieve_evidence





logger = logging.getLogger(__name__)








router = APIRouter(tags=["Research"])
DbSession = Annotated[Session, Depends(get_db)]

INSUFFICIENT_EVIDENCE_ANSWER = (
    "The retrieved sources do not establish an answer to this question. "
    "Scout cannot verify the requested fact or relationship from the indexed evidence. "
    "Add or index relevant official procurement documents and try again."
)


def _source_references(evidence: list[dict[str, Any]]) -> list[SourceReference]:
    """Convert retrieved chunks to response-safe provenance records."""
    references = []
    seen: set[tuple[int, int]] = set()
    for item in evidence:
        try:
            source_id = int(item["source_document_id"])
            chunk_index = int(item["chunk_index"])
            excerpt = str(item["text"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if not excerpt or (source_id, chunk_index) in seen:
            continue
        seen.add((source_id, chunk_index))
        references.append(
            SourceReference(
                source_document_id=source_id,
                title=str(item.get("title") or "Untitled source"),
                source_url=item.get("source_url"),
                excerpt=excerpt,
                chunk_index=chunk_index,
                content_hash=item.get("content_hash"),
            )
        )
    return references


@router.post("/ask", response_model=AskResponse)
def ask_question(
    payload: AskRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AskResponse:
    """Retrieve, assess, answer, and persist an authenticated user's question."""
    try:
        evidence = retrieve_evidence(
            payload.question,
            n_results=settings.retrieval_n_results,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence retrieval is unavailable. Please try again later.",
        ) from exc

    sufficient = assess_evidence(evidence)
    sources = _source_references(
        evidence) if sufficient else []
    # Never call the LLM when retrieval did not meet the configured threshold.
    if sufficient:
        try:
            answer = generate_answer(payload.question, evidence)
        except OllamaError as exc:
            logger.exception("Scout answer generation failed")

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The local answer-generation service is unavailable.",
            ) from exc
    else:
        answer = INSUFFICIENT_EVIDENCE_ANSWER

    research_query = ResearchQuery(
        user_id=current_user.id,
        question=payload.question,
        answer=answer,
        sources_json=json.dumps([source.model_dump() for source in sources]),
        sufficient_evidence=sufficient,
    )
    db.add(research_query)
    try:
        db.commit()
        db.refresh(research_query)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The research result could not be saved.",
        ) from None

    return AskResponse(
        answer=answer,
        sufficient_evidence=sufficient,
        sources=sources,
        research_query_id=research_query.id,
    )
