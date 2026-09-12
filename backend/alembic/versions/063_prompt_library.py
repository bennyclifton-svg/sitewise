"""Personal prompt libraries shared across projects."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "063_prompt_library"
down_revision = "062_procurement_comparison"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_libraries",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("prompts", postgresql.JSONB(), nullable=False),
    )
    # Access goes through authenticated backend routes; no direct browser writes.
    op.execute("ALTER TABLE prompt_libraries ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("prompt_libraries")
