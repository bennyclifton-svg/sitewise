"""tender mapping support indexes

Revision ID: 012_tender_mapping_support
Revises: 011_tender_report_language
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "012_tender_mapping_support"
down_revision: Union[str, Sequence[str], None] = "011_tender_report_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.add_column(
        "taxonomy_synonyms",
        sa.Column("embedding", Vector(1536), nullable=True),
    )
    op.execute(
        """
        CREATE INDEX ix_taxonomy_synonyms_embedding
        ON taxonomy_synonyms
        USING ivfflat (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_taxonomy_synonyms_embedding")
    op.drop_column("taxonomy_synonyms", "embedding")
