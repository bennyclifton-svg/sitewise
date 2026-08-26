"""Persist typed Programme dependency records.

Revision ID: 061_programme_dependencies
Revises: 060_programme_collapsed_stages
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "061_programme_dependencies"
down_revision = "060_programme_collapsed_stages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "programme_versions",
        sa.Column(
            "dependencies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    # Dependency keys contain literal colons, which SQLAlchemy text() interprets
    # as bind parameters. Send this static migration SQL directly to psycopg.
    op.get_bind().exec_driver_sql(
        """
        UPDATE programme_versions AS version
        SET dependencies = COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'dependency_key', activity.predecessor_key || ':finish->'
                            || activity.activity_key || ':start',
                        'source_activity_key', activity.predecessor_key,
                        'target_activity_key', activity.activity_key,
                        'source_endpoint', 'finish',
                        'target_endpoint', 'start',
                        'lag_days', activity.lag_days
                    )
                    ORDER BY activity.display_order, activity.activity_key
                )
                FROM programme_activities AS activity
                WHERE activity.programme_version_id = version.id
                  AND activity.predecessor_key IS NOT NULL
            ),
            '[]'::jsonb
        )
        """
    )
    op.drop_column("programme_activities", "lag_days")
    op.drop_column("programme_activities", "predecessor_key")


def downgrade() -> None:
    op.add_column(
        "programme_activities",
        sa.Column("predecessor_key", sa.String(255), nullable=True),
    )
    op.add_column(
        "programme_activities",
        sa.Column("lag_days", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        """
        WITH ranked_dependencies AS (
            SELECT
                version.id AS programme_version_id,
                dependency.value,
                row_number() OVER (
                    PARTITION BY
                        version.id,
                        dependency.value->>'target_activity_key'
                    ORDER BY dependency.value->>'dependency_key'
                ) AS position
            FROM programme_versions AS version
            CROSS JOIN LATERAL jsonb_array_elements(version.dependencies) AS dependency(value)
        )
        UPDATE programme_activities AS activity
        SET predecessor_key = dependency.value->>'source_activity_key',
            lag_days = COALESCE((dependency.value->>'lag_days')::integer, 0)
        FROM ranked_dependencies AS dependency
        WHERE activity.programme_version_id = dependency.programme_version_id
          AND activity.activity_key = dependency.value->>'target_activity_key'
          AND dependency.position = 1
        """
    )
    op.drop_column("programme_versions", "dependencies")
