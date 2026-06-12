"""tender taxonomy and knowledge tables

Revision ID: 008_tender_knowledge
Revises: 007_tender_core
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_tender_knowledge"
down_revision: Union[str, Sequence[str], None] = "007_tender_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "taxonomy_cells",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("parent_code", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("grp", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applicability", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bundling_parents", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("region_tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("build_type_tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("benchmark_key", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_taxonomy_cells_code"),
        sa.CheckConstraint(
            "stage IN ('prelim', 'base', 'lockup', 'fixing', 'completion', "
            "'external', 'statutory')",
            name="ck_taxonomy_cells_stage",
        ),
    )

    op.create_table(
        "taxonomy_synonyms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cell_code", sa.String(length=32), nullable=False),
        sa.Column("phrase", sa.Text(), nullable=False),
        sa.Column("phrase_norm", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="seed"),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        # FK to tender_corrections.id is added in 009 once that table exists.
        sa.Column("correction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cell_code"], ["taxonomy_cells.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cell_code", "phrase_norm", name="uq_taxonomy_synonyms_cell_code_phrase_norm"
        ),
        sa.CheckConstraint(
            "source IN ('seed', 'correction', 'auto')",
            name="ck_taxonomy_synonyms_source",
        ),
    )
    op.execute(
        """
        CREATE INDEX ix_taxonomy_synonyms_phrase_norm_trgm
        ON taxonomy_synonyms
        USING gin (phrase_norm gin_trgm_ops)
        """
    )

    op.create_table(
        "expectation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("cell_code", sa.String(length=32), nullable=False),
        sa.Column("predicate", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("region_tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("build_type_tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["cell_code"], ["taxonomy_cells.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_code", name="uq_expectation_rules_rule_code"),
        sa.CheckConstraint(
            "severity IN ('must', 'should', 'conditional')",
            name="ck_expectation_rules_severity",
        ),
    )

    op.create_table(
        "benchmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_key", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False),
        sa.Column("build_type", sa.String(length=32), nullable=False),
        sa.Column("spec_level", sa.String(length=32), nullable=False),
        sa.Column("metric", sa.String(length=32), nullable=False),
        sa.Column("p25", sa.Numeric(), nullable=True),
        sa.Column("p50", sa.Numeric(), nullable=True),
        sa.Column("p75", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("provenance", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["superseded_by"], ["benchmarks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "metric IN ('absolute', 'per_m2', 'pct_of_build', 'ratio')",
            name="ck_benchmarks_metric",
        ),
        sa.CheckConstraint(
            "source IN ('model_seed', 'published', 'observed')",
            name="ck_benchmarks_source",
        ),
        sa.CheckConstraint(
            "confidence IN ('low', 'medium', 'high')",
            name="ck_benchmarks_confidence",
        ),
    )
    op.create_index("ix_benchmarks_benchmark_key", "benchmarks", ["benchmark_key"], unique=False)


def downgrade() -> None:
    # pg_trgm is a shared extension — deliberately not dropped here.
    op.drop_index("ix_benchmarks_benchmark_key", table_name="benchmarks")
    op.drop_table("benchmarks")

    op.drop_table("expectation_rules")

    op.execute("DROP INDEX IF EXISTS ix_taxonomy_synonyms_phrase_norm_trgm")
    op.drop_table("taxonomy_synonyms")

    op.drop_table("taxonomy_cells")
