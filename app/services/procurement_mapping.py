
"""Map validated SAM.gov notices to Scout's internal model fields."""

from datetime import datetime, timezone

from app.schemas.sam_gov import SamOpportunity


def _parse_sam_date(value: str | None) -> datetime | None:
    """Convert a SAM.gov date or timestamp to an aware UTC datetime."""
    if not value:
        return None

    normalized = value.strip()

    # Support ISO timestamps, including timestamps ending in Z.
    try:
        parsed = datetime.fromisoformat(
            normalized.replace("Z", "+00:00")
        )
    except ValueError:
        # SAM.gov may also provide dates in MM/DD/YYYY format.
        try:
            parsed = datetime.strptime(normalized, "%m/%d/%Y")
        except ValueError as exc:
            raise ValueError(
                "SAM.gov returned an unsupported date format."
            ) from exc

    # Treat date-only or otherwise naive values as UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def map_sam_opportunity(
    opportunity: SamOpportunity,
) -> dict[str, str | datetime | None]:
    """Map one validated SAM.gov notice to ProcurementNotice fields."""
    return {
        "sam_notice_id": opportunity.notice_id,
        "title": opportunity.title,
        "notice_type": opportunity.notice_type,
        "department": opportunity.department,
        "posted_date": _parse_sam_date(opportunity.posted_date),
        "response_deadline": _parse_sam_date(
            opportunity.response_deadline
        ),
        "source_url": opportunity.source_url,
        "description": opportunity.description,
    }
