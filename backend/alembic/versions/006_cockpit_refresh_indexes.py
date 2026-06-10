"""cockpit refresh indexes

Revision ID: 006_cockpit_refresh_indexes
Revises: 005_polar_billing
Create Date: 2026-06-08

"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_cockpit_refresh_indexes"
down_revision: Union[str, Sequence[str], None] = "005_polar_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_source_documents_project_source_type_relative_path",
        "source_documents",
        ["project", "source_type", "relative_path"],
        unique=False,
    )
    op.execute(
        """
        CREATE INDEX ix_source_documents_platform_knowledge_kind
        ON source_documents (
            ((document_metadata ->> 'knowledge_scope')),
            ((document_metadata ->> 'sitewise_knowledge_kind'))
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_source_documents_platform_knowledge_kind")
    op.drop_index(
        "ix_source_documents_project_source_type_relative_path",
        table_name="source_documents",
    )
