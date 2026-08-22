"""Add project Procurement Strategy register.

Revision ID: 058_procurement_strategy
Revises: 057_procurement_submissions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "058_procurement_strategy"
down_revision = "057_procurement_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procurement_strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "tenderer_column_count", sa.Integer(), server_default="3", nullable=False
        ),
        sa.Column(
            "source_fingerprint", sa.String(length=64), server_default="", nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("revision >= 1", name="ck_procurement_strategies_revision"),
        sa.CheckConstraint(
            "tenderer_column_count IN (3, 4)",
            name="ck_procurement_strategies_column_count",
        ),
    )
    op.create_index(
        "ix_procurement_strategies_project", "procurement_strategies", ["project_id"]
    )
    op.create_table(
        "procurement_strategy_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "strategy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("discipline_code", sa.String(length=128)),
        sa.Column("discipline_label", sa.String(length=512), nullable=False),
        sa.Column("participant_type", sa.String(length=24), nullable=False),
        sa.Column("request_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="not_started", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=24), nullable=False),
        sa.Column("locked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "participant_type IN ('consultant','trade','supplier')",
            name="ck_procurement_strategy_rows_participant_type",
        ),
        sa.CheckConstraint(
            "request_kind IN ('consultant_rfp','contractor_eoi','trade_rft','trade_rfq')",
            name="ck_procurement_strategy_rows_request_kind",
        ),
        sa.CheckConstraint(
            "status IN ('not_started','researching','shortlisting','request_drafted',"
            "'issued','responses_received','evaluating','awarded','cancelled')",
            name="ck_procurement_strategy_rows_status",
        ),
        sa.CheckConstraint(
            "origin IN ('derived','existing_request','manual')",
            name="ck_procurement_strategy_rows_origin",
        ),
    )
    op.create_index(
        "uq_procurement_strategy_rows_discipline",
        "procurement_strategy_rows",
        ["strategy_id", "discipline_code"],
        unique=True,
        postgresql_where=sa.text("discipline_code IS NOT NULL"),
    )
    op.create_index(
        "ix_procurement_strategy_rows_order",
        "procurement_strategy_rows",
        ["strategy_id", "display_order"],
    )
    op.create_index(
        "ix_procurement_strategy_rows_code",
        "procurement_strategy_rows",
        ["discipline_code"],
    )
    op.create_table(
        "procurement_strategy_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "strategy_row_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_strategy_rows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=512), nullable=False),
        sa.Column("website_url", sa.String(length=2048)),
        sa.Column("location_text", sa.String(length=512)),
        sa.Column("source_url", sa.String(length=2048)),
        sa.Column("source_title", sa.String(length=512)),
        sa.Column("researched_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("slot BETWEEN 1 AND 4", name="ck_strategy_candidates_slot"),
        sa.UniqueConstraint(
            "strategy_row_id", "slot", name="uq_strategy_candidates_row_slot"
        ),
    )
    op.create_index(
        "ix_strategy_candidates_row",
        "procurement_strategy_candidates",
        ["strategy_row_id"],
    )
    op.add_column(
        "procurement_requests", sa.Column("discipline_code", sa.String(length=128))
    )
    op.add_column(
        "procurement_requests",
        sa.Column(
            "strategy_row_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_strategy_rows.id", ondelete="SET NULL"),
        ),
    )
    op.create_index(
        "ix_procurement_requests_strategy_row",
        "procurement_requests",
        ["strategy_row_id"],
    )
    op.create_index(
        "ix_procurement_requests_discipline",
        "procurement_requests",
        ["discipline_code"],
    )
    op.execute(
        """UPDATE procurement_requests SET discipline_code = CASE
        WHEN lower(target_name) IN ('architect','architecture','architectural') THEN 'consultant.architect'
        WHEN lower(target_name) IN ('structural','structural engineer','structural engineering') THEN 'consultant.structural'
        WHEN lower(target_name) IN ('civil','civil engineer','civil engineering') THEN 'consultant.civil'
        WHEN lower(target_name) IN ('town planner','town planning') THEN 'consultant.town_planner'
        WHEN lower(target_name) IN ('main works','main contractor','head contractor','builder') THEN 'trade.main_works'
        WHEN lower(target_name) IN ('structural steel','structural steelwork') THEN 'trade.structural_steel'
        WHEN lower(target_name) IN ('windows and glazing','windows','glazing') THEN 'supplier.windows_glazing'
        ELSE discipline_code END
        WHERE discipline_code IS NULL"""
    )

    for table in (
        "procurement_strategies",
        "procurement_strategy_rows",
        "procurement_strategy_candidates",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY procurement_strategies_owner_policy ON procurement_strategies
        USING (EXISTS (SELECT 1 FROM projects p WHERE p.id = project_id AND p.owner_user_id = auth.uid()))
        WITH CHECK (EXISTS (SELECT 1 FROM projects p WHERE p.id = project_id AND p.owner_user_id = auth.uid()))"""
    )
    op.execute(
        """CREATE POLICY procurement_strategy_rows_owner_policy ON procurement_strategy_rows
        USING (EXISTS (SELECT 1 FROM procurement_strategies s JOIN projects p ON p.id = s.project_id
          WHERE s.id = strategy_id AND p.owner_user_id = auth.uid()))
        WITH CHECK (EXISTS (SELECT 1 FROM procurement_strategies s JOIN projects p ON p.id = s.project_id
          WHERE s.id = strategy_id AND p.owner_user_id = auth.uid()))"""
    )
    op.execute(
        """CREATE POLICY procurement_strategy_candidates_owner_policy ON procurement_strategy_candidates
        USING (EXISTS (SELECT 1 FROM procurement_strategy_rows r JOIN procurement_strategies s ON s.id = r.strategy_id
          JOIN projects p ON p.id = s.project_id WHERE r.id = strategy_row_id AND p.owner_user_id = auth.uid()))
        WITH CHECK (EXISTS (SELECT 1 FROM procurement_strategy_rows r JOIN procurement_strategies s ON s.id = r.strategy_id
          JOIN projects p ON p.id = s.project_id WHERE r.id = strategy_row_id AND p.owner_user_id = auth.uid()))"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
          GRANT SELECT, INSERT, UPDATE, DELETE ON procurement_strategies, procurement_strategy_rows, procurement_strategy_candidates TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
          GRANT SELECT, INSERT, UPDATE, DELETE ON procurement_strategies, procurement_strategy_rows, procurement_strategy_candidates TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.drop_index("ix_procurement_requests_discipline", table_name="procurement_requests")
    op.drop_index("ix_procurement_requests_strategy_row", table_name="procurement_requests")
    op.drop_column("procurement_requests", "strategy_row_id")
    op.drop_column("procurement_requests", "discipline_code")
    op.drop_table("procurement_strategy_candidates")
    op.drop_table("procurement_strategy_rows")
    op.drop_table("procurement_strategies")
