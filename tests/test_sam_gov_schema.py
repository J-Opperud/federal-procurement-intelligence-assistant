import pytest
from pydantic import ValidationError

from app.schemas.sam_gov import (
    SamOpportunity,
    SamOpportunitySearchResponse,
)


def test_sam_response_maps_notice_fields():
    response = SamOpportunitySearchResponse.model_validate(
        {
            "totalRecords": 1,
            "opportunitiesData": [
                {
                    "noticeId": "SAM-123",
                    "title": "  Software Support  ",
                    "type": "Solicitation",
                    "fullParentPathName": "Department of Defense",
                    "postedDate": "10/20/2026",
                    "responseDeadLine": "11/20/2026",
                    "uiLink": "https://sam.gov/opp/example/view",
                    "unexpectedField": "ignored",
                }
            ],
        }
    )

    notice = response.opportunities[0]
    assert notice.notice_id == "SAM-123"
    assert notice.title == "Software Support"
    assert notice.notice_type == "Solicitation"
    assert notice.department == "Department of Defense"
    assert notice.source_url == "https://sam.gov/opp/example/view"


def test_sam_notice_accepts_missing_optional_fields():
    notice = SamOpportunity.model_validate(
        {
            "noticeId": "SAM-456",
            "title": "Maintenance",
            "type": "Combined Synopsis/Solicitation",
        }
    )

    assert notice.department is None
    assert notice.posted_date is None
    assert notice.response_deadline is None
    assert notice.source_url is None


def test_sam_notice_rejects_blank_required_fields():
    with pytest.raises(ValidationError):
        SamOpportunity.model_validate(
            {
                "noticeId": " ",
                "title": "Maintenance",
                "type": "Solicitation",
            }
        )


def test_sam_response_defaults_to_empty_opportunity_list():
    response = SamOpportunitySearchResponse.model_validate(
        {"totalRecords": 0}
    )

    assert response.opportunities == []

def test_rejects_missing_total_records():
    with pytest.raises(ValidationError):
        SamOpportunitySearchResponse.model_validate(
            {"opportunitiesData": []}
        )


def test_rejects_negative_total_records():
    with pytest.raises(ValidationError):
        SamOpportunitySearchResponse.model_validate(
            {"totalRecords": -1, "opportunitiesData": []}
        )


def test_rejects_invalid_opportunity_record():
    with pytest.raises(ValidationError):
        SamOpportunity.model_validate(
            {
                "noticeId": "",
                "title": "Example notice",
                "type": "Solicitation",
            }
        )


def test_rejects_non_list_opportunities():
    with pytest.raises(ValidationError):
        SamOpportunitySearchResponse.model_validate(
            {"totalRecords": 1, "opportunitiesData": "invalid"}
        )
