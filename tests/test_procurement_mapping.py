
from datetime import datetime, timezone

import pytest

from app.schemas.sam_gov import SamOpportunity
from app.services.procurement_mapping import map_sam_opportunity


def test_maps_sam_notice_fields_and_dates():
    opportunity = SamOpportunity.model_validate(
        {
            "noticeId": "NOTICE-123",
            "title": "Equipment procurement",
            "type": "Solicitation",
            "fullParentPathName": "Department of Example",
            "postedDate": "10/22/2026",
            "responseDeadLine": "2026-11-22T15:30:00-05:00",
            "uiLink": "https://sam.gov/notice/NOTICE-123",
            "description": "Example procurement notice",
        }
    )

    result = map_sam_opportunity(opportunity)

    assert result["sam_notice_id"] == "NOTICE-123"
    assert result["title"] == "Equipment procurement"
    assert result["notice_type"] == "Solicitation"
    assert result["department"] == "Department of Example"
    assert result["posted_date"] == datetime(
        2026, 10, 22, tzinfo=timezone.utc
    )
    assert result["response_deadline"] == datetime(
        2026, 11, 22, 20, 30, tzinfo=timezone.utc
    )
    assert result["source_url"] == "https://sam.gov/notice/NOTICE-123"
    assert result["description"] == "Example procurement notice"


def test_missing_optional_fields_map_to_none():
    opportunity = SamOpportunity.model_validate(
        {
            "noticeId": "NOTICE-456",
            "title": "Example notice",
            "type": "Sources Sought",
        }
    )

    result = map_sam_opportunity(opportunity)

    assert result["department"] is None
    assert result["posted_date"] is None
    assert result["response_deadline"] is None
    assert result["source_url"] is None
    assert result["description"] is None


def test_invalid_date_is_rejected():
    opportunity = SamOpportunity.model_validate(
        {
            "noticeId": "NOTICE-789",
            "title": "Example notice",
            "type": "Solicitation",
            "postedDate": "not-a-date",
        }
    )

    with pytest.raises(ValueError, match="unsupported date format"):
        map_sam_opportunity(opportunity)
