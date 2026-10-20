

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Describe a request-validation problem without exposing input values."""

    location: list[str | int]
    message: str
    type: str


class ErrorDetail(BaseModel):
    """Describe a single API error."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: list[ValidationIssue] | None = None


class ErrorResponse(BaseModel):
    """Standard envelope for API error responses."""

    error: ErrorDetail
