
"""Request and response schemas for evidence-backed procurement research."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AskRequest(BaseModel):
    """Validate a procurement research question."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=5, max_length=2000)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Question must contain at least 5 non-whitespace characters.")
        return value


class SourceReference(BaseModel):
    """Identify a retrieved passage and its source."""

    model_config = ConfigDict(extra="forbid")

    source_document_id: int
    title: str
    source_url: str | None = None
    excerpt: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    content_hash: str | None = None


class AskResponse(BaseModel):
    """Return an answer alongside its evidence assessment and citations."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    sufficient_evidence: bool
    sources: list[SourceReference] = Field(default_factory=list)
    research_query_id: int
