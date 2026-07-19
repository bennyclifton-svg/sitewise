"""Cut over SourceDocument path uniqueness to project scope.

Revision ID: 021b_source_doc_path_contract
Revises: 021_source_document_uuid_expand

The expand migration deliberately retains legacy global path uniqueness while
the dual-write application is deployed. This migration opens the bounded
repair window in which shared legacy evidence can be split into project-scoped
rows before migration 022 enforces the UUID ownership contract.

``IF EXISTS`` keeps upgrades safe for databases that ran the earlier form of
migration 021, which removed the constraint prematurely.
"""

from alembic import op

revision = "021b_source_doc_path_contract"
down_revision = "021_source_document_uuid_expand"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE source_documents
        DROP CONSTRAINT IF EXISTS source_documents_relative_path_key
        """
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
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'source_documents'::regclass
              AND conname = 'source_documents_relative_path_key'
          ) THEN
            ALTER TABLE source_documents
            ADD CONSTRAINT source_documents_relative_path_key UNIQUE (relative_path);
          END IF;
        END $$;
        """
    )
