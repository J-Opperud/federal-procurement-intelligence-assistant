
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """An authenticated Scout user."""

    __tablename__ = "users"


    id: Mapped[int] = mapped_column(
        primary_key=True
        )
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
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        )
    research_queries: Mapped[
        list["ResearchQuery"]] = relationship(
            back_populates="user",
            cascade="all,delete-orphan"
        )

class ProcurementNotice(Base):
    """A structured federal procurement opportunity."""

    __tablename__ = "procurement_notices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        )
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
        )
    posted_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
        )
    response_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
        )
    source_url: Mapped[str | None] = mapped_column(
        String(2048)
        )
    description: Mapped[str | None] = mapped_column(Text)

    last_fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        )
    source_documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="procurement_notice",
        cascade="all, delete-orphan",
        )


class SourceDocument(Base):
    """
    A source document associated with a notice or reference source.
    """
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    procurement_notice_id: Mapped[int | None] = mapped_column(
        ForeignKey("procurement_notices.id"),
        nullable=True,
        index=True,
        )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
        )
    source_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
        )
    source_url: Mapped[str | None] = mapped_column(String(2048))

    content_hash: Mapped[str | None] = mapped_column(String(128))

    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        )
    procurement_notice: Mapped[
        "ProcurementNotice | None"] = relationship(
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
        nullable=False,
    )

    sources_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    sufficient_evidence: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="research_queries",
    )
