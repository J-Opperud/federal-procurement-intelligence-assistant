from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    event,
    func,
    UniqueConstraint,
    CheckConstraint,
    Numeric,
    Integer,
)
from datetime import datetime, timezone

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
        nullable=False,
    )

    source_documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="procurement_notice",
        cascade="all, delete-orphan",
    )

    contracting_office_code: Mapped[str | None] = mapped_column(
        ForeignKey(
            "contracting_offices.office_code",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    naics_code: Mapped[str | None] = mapped_column(
        ForeignKey("naics_codes.code", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    psc_code: Mapped[str | None] = mapped_column(
        ForeignKey("psc_codes.code", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    contracting_office: Mapped["ContractingOffice | None"] = relationship()

    naics_classification: Mapped["NAICSCode | None"] = relationship()

    psc_classification: Mapped["PSCCode | None"] = relationship()

    awards: Mapped[list["Award"]] = relationship(
        back_populates="procurement_notice",
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
        String(64),
        nullable=True,
        index=True,
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    indexed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

    procurement_notice: Mapped["ProcurementNotice | None"] = relationship(
        back_populates="source_documents",
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="source_document",
        cascade="all, delete-orphan",
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

class Department(Base):
    """A federal department (e.g., Department of Defense)."""

    __tablename__ = "departments"

    department_code: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    department_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
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

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    agencies: Mapped[list["Agency"]] = relationship(
        back_populates="department",
    )

class Agency(Base):
    """An agency or sub-tier organization within a federal department."""

    __tablename__ = "agencies"

    agency_code: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    department_code: Mapped[str] = mapped_column(
        ForeignKey("departments.department_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    agency_name: Mapped[str] = mapped_column(
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

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    department: Mapped["Department"] = relationship(
        back_populates="agencies",
    )

    contracting_offices: Mapped[list["ContractingOffice"]] = relationship(
        back_populates="agency",
    )

class ContractingOffice(Base):
    """A specific contracting office responsible for issuing solicitations and awards."""

    __tablename__ = "contracting_offices"

    office_code: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    agency_code: Mapped[str] = mapped_column(
        ForeignKey("agencies.agency_code", ondelete="RESTRICT" ),
        nullable=False,
        index=True,
    )

    office_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    agency: Mapped["Agency"] = relationship(
        back_populates="contracting_offices",
    )

    awards: Mapped[list["Award"]] = relationship(
    back_populates="contracting_office",
    )

class Company(Base):
    """A registered corporate contractor entity identified by SAM.gov UEI and CAGE code."""

    __tablename__ = "companies"

    uei: Mapped[str] = mapped_column(
        String(12),
        primary_key=True,
    )

    cage_code: Mapped[str | None] = mapped_column(
        String(5),
        index=True,
        nullable=True,
    )

    legal_business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    dba_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    awards: Mapped[list["Award"]] = relationship(
    back_populates="recipient",
)

class NAICSCode(Base):
    """North American Industry Classification System (NAICS) code."""

    __tablename__ = "naics_codes"

    code: Mapped[str] = mapped_column(
        String(6),
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

class PSCCode(Base):
    """Product and Service Code (PSC) classification."""

    __tablename__ = "psc_codes"

    code: Mapped[str] = mapped_column(
        String(4),
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    category_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

class Contract(Base):
    """A federal contract or contract vehicle identified by PIID."""

    __tablename__ = "contracts"

    piid: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    awards: Mapped[list["Award"]] = relationship(
        back_populates="contract",
    )

class Award(Base):

    """A federal award record associated with a contract and recipient."""

    __tablename__ = "awards"

    award_id: Mapped[str] = mapped_column(
        String(150),
        primary_key=True,
    )

    contract_piid: Mapped[str | None] = mapped_column(
        ForeignKey("contracts.piid", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    recipient_uei: Mapped[str | None] = mapped_column(
        ForeignKey("companies.uei", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    contracting_office_code: Mapped[str | None] = mapped_column(
        ForeignKey("contracting_offices.office_code", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    notice_id: Mapped[int | None] = mapped_column(
        ForeignKey("procurement_notices.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    award_amount: Mapped[Numeric | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    award_date: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

    contract: Mapped["Contract | None"] = relationship(
        back_populates="awards",
    )

    recipient: Mapped["Company | None"] = relationship(
        back_populates="awards",
    )

    contracting_office: Mapped["ContractingOffice | None"] = relationship(
        back_populates="awards",
    )

    procurement_notice: Mapped["ProcurementNotice | None"] = relationship(
        back_populates="awards",
    )

    transactions: Mapped[list["AwardTransaction"]] = relationship(
        back_populates="award",
    )

class AwardTransaction(Base):
    """A financial transaction, obligation, or modification record tied to a contract award."""

    __tablename__ = "award_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    award_id: Mapped[str] = mapped_column(
        ForeignKey(
            "awards.award_id", ondelete="RESTRICT"
        ),
        nullable=False,
        index=True,
    )

    modification_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    action_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    obligation_amount: Mapped[Numeric | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )

    action_date: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    award: Mapped["Award"] = relationship(
        back_populates="transactions",
    )

class DocumentChunk(Base):
    """A text chunk derived from a source document for RAG retrieval."""

    __tablename__ = "document_chunks"

    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "chunk_index",
            name="uq_document_chunk_position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    vector_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    source_document: Mapped["SourceDocument"] = relationship(
        back_populates="chunks",
    )

class IngestionRecord(Base):
    """Tracks ingestion jobs, processing outcomes, and failures."""

    __tablename__ = "ingestion_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    job_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )

    records_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    records_inserted: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    records_updated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    records_failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

class AgencyRelationship(Base):
    """Tracks hierarchical or operational relationships between federal agencies."""

    __tablename__ = "agency_relationships"

    __table_args__ = (
        UniqueConstraint(
            "parent_agency_code",
            "child_agency_code",
            "relationship_type",
            name="uq_agency_relationship",
        ),
        CheckConstraint(
            "parent_agency_code != child_agency_code",
            name="ck_agency_relationship_no_self_reference",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    parent_agency_code: Mapped[str] = mapped_column(
        ForeignKey("agencies.agency_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    child_agency_code: Mapped[str] = mapped_column(
        ForeignKey("agencies.agency_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="SUB_TIER",
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )