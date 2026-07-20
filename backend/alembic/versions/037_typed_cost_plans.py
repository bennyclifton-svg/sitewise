"""Add canonical typed Cost Plan versions and items.

Revision ID: 037_typed_cost_plans
Revises: 036_tender_mapping_trade_target
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "037_typed_cost_plans"
down_revision = "036_tender_mapping_trade_target"
branch_labels = None
depends_on = None


def _owner_policy(table: str, project_expression: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""CREATE POLICY {table}_owner_policy ON {table}
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = {project_expression} AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = {project_expression} AND p.owner_user_id = auth.uid()
        ))"""
    )


def upgrade() -> None:
    op.create_table(
        "cost_plan_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artefact_revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("draft_artifacts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), server_default="proposed", nullable=False),
        sa.Column(
            "contingency_percent", sa.Numeric(9, 4), server_default="0", nullable=False
        ),
        sa.Column(
            "escalation_percent", sa.Numeric(9, 4), server_default="0", nullable=False
        ),
        sa.Column(
            "gst_treatment", sa.String(24), server_default="exclusive", nullable=False
        ),
        sa.Column(
            "assumptions",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "narrative",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("dependency_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("deterministic_totals", postgresql.JSONB(), nullable=False),
        sa.Column(
            "source_draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("draft_artifacts.id", ondelete="RESTRICT"),
        ),
        sa.Column("external_idempotency_key", sa.String(255)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('proposed','accepted','superseded')",
            name="ck_cost_plan_versions_status",
        ),
        sa.CheckConstraint(
            "gst_treatment IN ('exclusive','inclusive','not_applicable')",
            name="ck_cost_plan_versions_gst_treatment",
        ),
        sa.CheckConstraint(
            "contingency_percent >= 0 AND escalation_percent >= 0",
            name="ck_cost_plan_versions_nonnegative_percentages",
        ),
        sa.UniqueConstraint(
            "project_id", "version", name="uq_cost_plan_versions_project_version"
        ),
        sa.UniqueConstraint(
            "project_id",
            "artefact_revision_id",
            name="uq_cost_plan_versions_project_artefact",
        ),
        sa.UniqueConstraint(
            "project_id",
            "source_draft_id",
            name="uq_cost_plan_versions_project_source_draft",
        ),
        sa.UniqueConstraint(
            "project_id",
            "external_idempotency_key",
            name="uq_cost_plan_versions_project_external_key",
        ),
    )
    op.create_index(
        "ix_cost_plan_versions_project_status",
        "cost_plan_versions",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_cost_plan_versions_created_by", "cost_plan_versions", ["created_by_user_id"]
    )

    op.create_table(
        "cost_plan_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cost_plan_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cost_plan_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_key", sa.String(255), nullable=False),
        sa.Column("cost_code", sa.String(128), nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("item", sa.String(512), nullable=False),
        sa.Column("budget", sa.Numeric(18, 2), nullable=False),
        sa.Column("committed", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("forecast", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("paid", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column(
            "allowance_type", sa.String(16), server_default="none", nullable=False
        ),
        sa.Column("quantity", sa.Numeric(18, 4)),
        sa.Column("unit", sa.String(64)),
        sa.Column("rate", sa.Numeric(18, 4)),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column(
            "source_refs",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("status", sa.String(24), server_default="proposed", nullable=False),
        sa.Column("locked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "allowance_type IN ('none','pc','ps','contingency')",
            name="ck_cost_plan_items_allowance_type",
        ),
        sa.CheckConstraint(
            "status IN ('proposed','confirmed','manual')",
            name="ck_cost_plan_items_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_cost_plan_items_confidence",
        ),
        sa.CheckConstraint(
            "(quantity IS NULL AND rate IS NULL AND unit IS NULL) OR (quantity IS NOT NULL AND rate IS NOT NULL AND unit IS NOT NULL)",
            name="ck_cost_plan_items_complete_unit_rate",
        ),
        sa.UniqueConstraint(
            "cost_plan_version_id", "item_key", name="uq_cost_plan_items_version_key"
        ),
        sa.UniqueConstraint(
            "cost_plan_version_id", "cost_code", name="uq_cost_plan_items_version_code"
        ),
    )
    op.create_index(
        "ix_cost_plan_items_version", "cost_plan_items", ["cost_plan_version_id"]
    )

    _owner_policy("cost_plan_versions", "cost_plan_versions.project_id")
    _owner_policy(
        "cost_plan_items",
        "(SELECT cpv.project_id FROM cost_plan_versions cpv WHERE cpv.id = cost_plan_items.cost_plan_version_id)",
    )
    op.execute(
        """CREATE FUNCTION protect_cost_plan_version_content() RETURNS trigger AS $$
        BEGIN
            IF ROW(
                NEW.project_id, NEW.artefact_revision_id, NEW.version,
                NEW.created_by_user_id, NEW.contingency_percent,
                NEW.escalation_percent, NEW.gst_treatment, NEW.assumptions,
                NEW.narrative, NEW.dependency_snapshot, NEW.deterministic_totals,
                NEW.source_draft_id, NEW.external_idempotency_key
            ) IS DISTINCT FROM ROW(
                OLD.project_id, OLD.artefact_revision_id, OLD.version,
                OLD.created_by_user_id, OLD.contingency_percent,
                OLD.escalation_percent, OLD.gst_treatment, OLD.assumptions,
                OLD.narrative, OLD.dependency_snapshot, OLD.deterministic_totals,
                OLD.source_draft_id, OLD.external_idempotency_key
            ) THEN
                RAISE EXCEPTION 'Cost Plan version content is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql"""
    )
    op.execute(
        """CREATE TRIGGER cost_plan_versions_immutable_content
        BEFORE UPDATE ON cost_plan_versions
        FOR EACH ROW EXECUTE FUNCTION protect_cost_plan_version_content()"""
    )
    op.execute(
        """CREATE FUNCTION protect_cost_plan_item_content() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Cost Plan items are immutable; create a new version';
        END;
        $$ LANGUAGE plpgsql"""
    )
    op.execute(
        """CREATE TRIGGER cost_plan_items_immutable_content
        BEFORE UPDATE ON cost_plan_items
        FOR EACH ROW EXECUTE FUNCTION protect_cost_plan_item_content()"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT ON cost_plan_versions, cost_plan_items TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE ON cost_plan_versions, cost_plan_items TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS cost_plan_items_immutable_content ON cost_plan_items"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_cost_plan_item_content()")
    op.execute(
        "DROP TRIGGER IF EXISTS cost_plan_versions_immutable_content ON cost_plan_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_cost_plan_version_content()")
    op.execute("DROP POLICY IF EXISTS cost_plan_items_owner_policy ON cost_plan_items")
    op.execute(
        "DROP POLICY IF EXISTS cost_plan_versions_owner_policy ON cost_plan_versions"
    )
    op.drop_index("ix_cost_plan_items_version", table_name="cost_plan_items")
    op.drop_table("cost_plan_items")
    op.drop_index("ix_cost_plan_versions_created_by", table_name="cost_plan_versions")
    op.drop_index(
        "ix_cost_plan_versions_project_status", table_name="cost_plan_versions"
    )
    op.drop_table("cost_plan_versions")
