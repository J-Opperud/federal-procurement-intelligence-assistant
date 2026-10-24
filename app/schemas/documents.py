"""Request and response schemas for procurement document endpoints."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentSearchParams(BaseModel):
    """Validate local procurement notice search parameters."""

    model_config = ConfigDict(extra="forbid")

    keyword: str | None = Field(default=None, min_length=1, max_length=200)
    notice_type: str | None = Field(default=None, min_length=1, max_length=100)
    posted_from: date | None = None
    posted_to: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("keyword", "notice_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @model_validator(mode="after")
    def validate_date_range(self):
        if (
            self.posted_from is not None
            and self.posted_to is not None
            and self.posted_from > self.posted_to
        ):
            raise ValueError("posted_from must be on or before posted_to.")
        return self


class DocumentResponse(BaseModel):
    """Public representation of a stored procurement notice."""

    model_config = ConfigDict(from_attributes=True)

    sam_notice_id: str
    title: str
    notice_type: str
    department: str | None
    posted_date: datetime | None
    response_deadline: datetime | None
    source_url: str | None
    description: str | None


class DocumentListResponse(BaseModel):
    """Paginated procurement notice search results."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentSyncRequest(BaseModel):
    """Validate a bounded SAM.gov synchronization request."""

    model_config = ConfigDict(extra="forbid")

    posted_from: date
    posted_to: date
    notice_type: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=100, ge=1, le=1000)

    @field_validator("notice_type")
    @classmethod
    def normalize_notice_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("notice_type must not be blank.")
        return value

    @model_validator(mode="after")
    def validate_sync_window(self):
        if self.posted_from > self.posted_to:
            raise ValueError("posted_from must be on or before posted_to.")
        if (self.posted_to - self.posted_from).days > 365:
            raise ValueError("The date window must not exceed 365 days.")
        return self


class DocumentSyncResponse(BaseModel):
    """Summary of a procurement notice synchronization run."""

    fetched_count: int = Field(ge=0)
    inserted_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    indexed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
