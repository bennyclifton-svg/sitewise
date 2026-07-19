"""Contract SourceDocument identity to project UUID plus relative path.

Revision ID: 022_source_doc_uuid_contract
Revises: 021b_source_doc_path_contract
"""

from alembic import op

revision = "022_source_doc_uuid_contract"
down_revision = "021b_source_doc_path_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM source_documents
            WHERE source_type = 'project_evidence' AND project_id IS NULL
          ) THEN
            RAISE EXCEPTION
              'SourceDocument UUID cutover refused: unresolved project evidence ownership';
          END IF;
          IF EXISTS (
            SELECT 1 FROM source_documents
            WHERE document_metadata->>'knowledge_scope' = 'platform'
              AND project_id IS NOT NULL
          ) THEN
            RAISE EXCEPTION
              'SourceDocument UUID cutover refused: platform knowledge has a project owner';
          END IF;
        END $$;
        """
    )
    op.create_check_constraint(
        "ck_source_documents_project_evidence_owner",
        "source_documents",
        "source_type <> 'project_evidence' OR project_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_source_documents_platform_projectless",
        "source_documents",
        "document_metadata->>'knowledge_scope' <> 'platform' OR project_id IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_source_documents_platform_projectless", "source_documents", type_="check"
    )
    op.drop_constraint(
        "ck_source_documents_project_evidence_owner", "source_documents", type_="check"
    )
