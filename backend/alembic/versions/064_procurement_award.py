"""Identify the awarded firm in each procurement discipline."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "064_procurement_award"
down_revision = "063_prompt_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("procurement_strategy_rows", sa.Column("awarded_candidate_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_strategy_awarded_candidate", "procurement_strategy_rows", "procurement_strategy_candidates", ["awarded_candidate_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_strategy_awarded_candidate", "procurement_strategy_rows", type_="foreignkey")
    op.drop_column("procurement_strategy_rows", "awarded_candidate_id")
