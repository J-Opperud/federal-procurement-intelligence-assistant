"""Create the complete initial Scout schema."""

from alembic import op
import sqlalchemy as sa

revision = "79a525ed2bc3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_users_username", "users", ["username"], unique=True
    )
    op.create_index(
        "uq_users_username_lower",
        "users",
        [sa.text("lower(username)")],
        unique=True,
    )

    op.create_table(
        "procurement_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sam_notice_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("notice_type", sa.String(100), nullable=False),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("posted_date", sa.DateTime(), nullable=True),
        sa.Column("response_deadline", sa.DateTime(), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_procurement_notices_sam_notice_id",
        "procurement_notices",
        ["sam_notice_id"],
        unique=True,
    )

    op.create_table(
        "source_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "procurement_notice_id",
            sa.Integer(),
            sa.ForeignKey("procurement_notices.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_source_documents_procurement_notice_id",
        "source_documents",
        ["procurement_notice_id"],
    )
    op.create_index(
        "ix_source_documents_content_hash",
        "source_documents",
        ["content_hash"],
    )

    op.create_table(
        "research_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("sources_json", sa.Text(), nullable=True),
        sa.Column("sufficient_evidence", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_research_queries_user_id",
        "research_queries",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("research_queries")
    op.drop_table("source_documents")
    op.drop_table("procurement_notices")
    op.drop_table("users")