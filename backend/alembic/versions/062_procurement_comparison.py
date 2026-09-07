"""Link many canonical files to a firm and retain row recommendation pointers."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "062_procurement_comparison"
down_revision = "061_programme_dependencies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procurement_candidate_files",
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_strategy_candidates.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "workspace_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace_files.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_procurement_candidate_files_file",
        "procurement_candidate_files",
        ["workspace_file_id"],
    )
    op.add_column(
        "procurement_strategy_rows",
        sa.Column(
            "submission_revision", sa.Integer(), nullable=False, server_default="1"
        ),
    )
    op.add_column(
        "procurement_strategy_rows",
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True)),
    )
    op.add_column(
        "procurement_strategy_rows",
        sa.Column(
            "recommendation_draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("draft_artifacts.id", ondelete="SET NULL"),
        ),
    )
    op.add_column(
        "procurement_strategy_rows",
        sa.Column(
            "recommendation_stale",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tender_documents",
        sa.Column(
            "review_data",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute("ALTER TABLE procurement_candidate_files ENABLE ROW LEVEL SECURITY")
    op.execute("""CREATE FUNCTION mark_procurement_submission_changed() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        IF TG_OP = 'DELETE' OR NEW.content_hash IS DISTINCT FROM OLD.content_hash THEN
            UPDATE procurement_strategy_rows SET submission_revision = submission_revision + 1,
                recommendation_stale = (recommendation_draft_id IS NOT NULL)
            WHERE id IN (SELECT c.strategy_row_id FROM procurement_strategy_candidates c
                JOIN procurement_candidate_files f ON f.candidate_id = c.id
                WHERE f.workspace_file_id = OLD.id);
        END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        RETURN NEW;
        END $$""")
    op.execute("""CREATE TRIGGER procurement_submission_content_changed
        BEFORE UPDATE OF content_hash OR DELETE ON workspace_files
        FOR EACH ROW EXECUTE FUNCTION mark_procurement_submission_changed()""")
    ownership = """EXISTS (SELECT 1 FROM procurement_strategy_candidates c
        JOIN procurement_strategy_rows r ON r.id = c.strategy_row_id
        JOIN procurement_strategies s ON s.id = r.strategy_id
        JOIN projects p ON p.id = s.project_id
        JOIN workspace_files f ON f.project_id = p.id
        WHERE c.id = candidate_id AND f.id = workspace_file_id AND p.owner_user_id = auth.uid())"""
    op.execute(
        f"CREATE POLICY procurement_candidate_files_owner_policy ON procurement_candidate_files USING ({ownership}) WITH CHECK ({ownership})"
    )
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON procurement_candidate_files TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON procurement_candidate_files TO service_role;
        END IF;
    END $$""")


def downgrade() -> None:
    op.execute("DROP TRIGGER procurement_submission_content_changed ON workspace_files")
    op.execute("DROP FUNCTION mark_procurement_submission_changed()")
    op.drop_column("tender_documents", "review_data")
    for name in (
        "recommendation_stale",
        "recommendation_draft_id",
        "comparison_id",
        "submission_revision",
    ):
        op.drop_column("procurement_strategy_rows", name)
    op.drop_table("procurement_candidate_files")
