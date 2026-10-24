"""Request and response schemas for source-document ingestion."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class SourceDocumentCreate(BaseModel):
    """Validated extracted text and provenance for a source document."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=100)
    source_url: HttpUrl | None = None
    content: str = Field(min_length=1, max_length=5_000_000)

    @field_validator("title", "source_type", "content")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    def normalized_content(self) -> str:
        return self.content


class SourceDocumentResponse(BaseModel):
    """Public source metadata without returning potentially large source text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    procurement_notice_id: int | None
    title: str
    source_type: str
    source_url: str | None
    content_hash: str | None
    indexed_at: datetime | None


class SourceDocumentIndexResponse(BaseModel):
    """Summary of one source document indexing attempt."""

    source_document: SourceDocumentResponse
    chunks_indexed: int = Field(ge=0)
    skipped: bool
