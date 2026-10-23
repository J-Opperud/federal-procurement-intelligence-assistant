
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Store UTC timestamps and restore UTC awareness on reads."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware.")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class User(Base):
    """An authenticated Scout user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    research_queries: Mapped[list["ResearchQuery"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


Index(
    "uq_users_username_lower",
    func.lower(User.username),
    unique=True,
)


@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def normalize_username(mapper, connection, target: User) -> None:
    """Normalize usernames before persisting them."""
    if target.username is not None:
        target.username = target.username.strip().lower()


class ProcurementNotice(Base):
    """A structured federal procurement opportunity."""

    __tablename__ = "procurement_notices"

    id: Mapped[int] = mapped_column(primary_key=True)

    sam_notice_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    notice_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    department: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    posted_date: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

    response_deadline: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    last_fetched_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=True,
    )

    source_documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="procurement_notice",
        cascade="all, delete-orphan",
    )


class SourceDocument(Base):
    """A source document associated with a notice or reference source."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    procurement_notice_id: Mapped[int | None] = mapped_column(
        ForeignKey("procurement_notices.id"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    indexed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=True,
    )

    procurement_notice: Mapped["ProcurementNotice | None"] = relationship(
        back_populates="source_documents",
    )


class ResearchQuery(Base):
    """A record of a user's procurement research question and answer."""

    __tablename__ = "research_queries"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    sources_json: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        default="[]",
    )

    sufficient_evidence: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="research_queries",
    )
