import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchQueryCreate(BaseModel):
    """Validate a completed research query submitted for persistence."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=10000)
    answer: str = Field(min_length=1, max_length=100000)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    sufficient_evidence: bool

    @field_validator("question", "answer")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field must not be blank.")
        return value.strip()


class ResearchQueryResponse(BaseModel):
    """Expose a saved research query without internal ORM fields."""

    id: int
    user_id: int
    question: str
    answer: str
    sources: list[dict[str, Any]]
    sufficient_evidence: bool
    created_at: datetime
