"""Expand SourceDocument tenancy with a nullable project UUID.

Revision ID: 021_source_document_uuid_expand
Revises: 020_tender_extract_cache
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021_source_document_uuid_expand"
down_revision = "020_tender_extract_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source_documents",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_source_documents_project_id_projects",
        "source_documents",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        """
        UPDATE source_documents AS document
        SET project_id = owner.project_id
        FROM (
            SELECT source_document_id, min(project_id::text)::uuid AS project_id
            FROM (
                SELECT source_document_id, project_id
                FROM workspace_files
                WHERE source_document_id IS NOT NULL
                UNION
                SELECT citation.document_id AS source_document_id, thread.project_id
                FROM message_citations AS citation
                JOIN chat_messages AS message ON message.id = citation.message_id
                JOIN chat_threads AS thread ON thread.id = message.thread_id
                WHERE thread.project_id IS NOT NULL
            ) AS ownership_edges
            GROUP BY source_document_id
            HAVING count(DISTINCT project_id) = 1
        ) AS owner
        WHERE document.id = owner.source_document_id
          AND document.source_type = 'project_evidence'
        """
    )
    op.create_index(
        "uq_source_documents_project_path",
        "source_documents",
        ["project_id", "relative_path"],
        unique=True,
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )
    op.create_index(
        "uq_source_documents_platform_path",
        "source_documents",
        ["relative_path"],
        unique=True,
        postgresql_where=sa.text(
            "project_id IS NULL AND document_metadata->>'knowledge_scope' = 'platform'"
        ),
    )
    op.drop_constraint(
        "source_documents_relative_path_key", "source_documents", type_="unique"
    )
    op.drop_index(
        "ix_source_documents_project_source_type_relative_path",
        table_name="source_documents",
    )
    op.create_index(
        "ix_source_documents_project_source_type_relative_path",
        "source_documents",
        ["project_id", "source_type", "relative_path"],
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT relative_path FROM source_documents
            GROUP BY relative_path HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION
              'Cannot restore global relative_path uniqueness while duplicate paths exist';
          END IF;
        END $$;
        """
    )
    op.drop_index(
        "ix_source_documents_project_source_type_relative_path",
        table_name="source_documents",
    )
    op.create_index(
        "ix_source_documents_project_source_type_relative_path",
        "source_documents",
        ["project", "source_type", "relative_path"],
    )
    op.drop_index("uq_source_documents_platform_path", table_name="source_documents")
    op.drop_index("uq_source_documents_project_path", table_name="source_documents")
    op.create_unique_constraint(
        "source_documents_relative_path_key", "source_documents", ["relative_path"]
    )
    op.drop_constraint(
        "fk_source_documents_project_id_projects", "source_documents", type_="foreignkey"
    )
    op.drop_column("source_documents", "project_id")
