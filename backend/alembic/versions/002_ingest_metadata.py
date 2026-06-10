"""ingest metadata and unique chunk index

Revision ID: 002_ingest_metadata
Revises: 001_initial_schema
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_ingest_metadata"
down_revision: Union[str, Sequence[str], None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "source_documents",
        sa.Column("document_class", sa.String(length=64), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "source_documents",
        sa.Column("ingest_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "source_documents",
        sa.Column("document_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "source_documents",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )

    op.drop_index("ix_document_chunks_document_id_chunk_index", table_name="document_chunks")
    op.create_index(
        "uq_document_chunks_document_id_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_document_chunks_document_id_chunk_index", table_name="document_chunks")
    op.create_index(
        "ix_document_chunks_document_id_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
        unique=False,
    )

    op.drop_column("source_documents", "content_hash")
    op.drop_column("source_documents", "document_metadata")
    op.drop_column("source_documents", "ingest_mode")
    op.drop_column("source_documents", "document_class")
