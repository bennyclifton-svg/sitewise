"""project taxonomy columns

Revision ID: 018_project_taxonomy
Revises: 017_project_activity_events
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_project_taxonomy"
down_revision: Union[str, Sequence[str], None] = "017_project_activity_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("building_class", sa.String(length=64)))
    op.add_column("projects", sa.Column("work_type", sa.String(length=64)))
    op.execute(
        """
        UPDATE projects
        SET building_class = CASE
            WHEN archetype IN ('new-dwelling', 'renovation', 'multi-dwelling', 'ancillary')
                THEN 'residential'
            WHEN archetype = 'small-commercial'
                THEN 'commercial'
            ELSE building_class
        END
        WHERE building_class IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("projects", "work_type")
    op.drop_column("projects", "building_class")
