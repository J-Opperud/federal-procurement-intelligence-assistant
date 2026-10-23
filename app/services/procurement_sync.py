"""Database synchronization for procurement notices."""


from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProcurementNotice


def upsert_procurement_notice(
    db: Session,
    notice_data: dict,
) -> tuple[ProcurementNotice, bool]:
    """Insert or update a notice by SAM.gov ID.

    Returns:
        A tuple of (notice, created), where created is True
        when a new database record was added.
    """
    sam_notice_id = notice_data.get("sam_notice_id")

    if not isinstance(sam_notice_id, str) or not sam_notice_id.strip():
        raise ValueError("sam_notice_id must be a non-empty string.")

    values = {
        **notice_data,
        "sam_notice_id": sam_notice_id.strip(),
        "last_fetched_at": datetime.now(timezone.utc),
    }

    notice = db.scalar(
        select(ProcurementNotice).where(
            ProcurementNotice.sam_notice_id == values["sam_notice_id"]
        )
    )

    if notice is None:
        notice = ProcurementNotice(**values)
        db.add(notice)
        db.flush()
        return notice, True

    for field, value in values.items():
        if field != "sam_notice_id":
            setattr(notice, field, value)

    db.flush()
    return notice, False
