
"""Typed schemas for SAM.gov Opportunities API responses."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator



class SamOpportunity(BaseModel):
    """Validate one opportunity returned by SAM.gov."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    notice_id: str = Field(
        validation_alias=AliasChoices("noticeId", "notice_id"),
        min_length=1,
        max_length=100,
    )
    title: str = Field(min_length=1, max_length=500)
    notice_type: str = Field(
        validation_alias=AliasChoices("type", "notice_type"),
        min_length=1,
        max_length=100,
    )

    department: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "fullParentPathName",
            "department",
        ),
        max_length=255,
    )
    posted_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("postedDate", "posted_date"),
    )
    response_deadline: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "responseDeadLine",
            "response_deadline",
        ),
    )
    source_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("uiLink", "source_url"),
        max_length=2048,
    )
    description: str | None = None

    @field_validator("notice_id", "title", "notice_type")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field must not be blank.")
        return value.strip()

    @field_validator(
        "department",
        "posted_date",
        "response_deadline",
        "source_url",
        "description",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class SamOpportunitySearchResponse(BaseModel):
    """Validate the envelope returned by the SAM.gov search API."""

    model_config = ConfigDict(extra="ignore")

    total_records: int = Field(
        validation_alias=AliasChoices("totalRecords", "total_records"),
        ge=0,
    )
    opportunities: list[SamOpportunity] = Field(
        validation_alias=AliasChoices(
            "opportunitiesData",
            "opportunities",
        ),
        default_factory=list,
    )
