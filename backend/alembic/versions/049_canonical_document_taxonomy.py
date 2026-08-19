"""Rewrite stored document_class values onto the frozen Stage 3 vocabulary (X1 Stage 8).

Revision ID: 049_canonical_document_taxonomy
Revises: 048_classification_overrides

document_class is String(64), not an enum. This revision is data-only.
Prints class counts before and after so the rewrite is auditable.
"""

from __future__ import annotations

import json

from alembic import op
from sqlalchemy import text

revision = "049_canonical_document_taxonomy"
down_revision = "048_classification_overrides"
branch_labels = None
depends_on = None

LEGACY_CLASS_MARKER = "_legacy_document_class"

# Historical rewrite table. Extra keys (corpus_catalog, inbox_pending) were
# never emitted by classify_entry; they existed only as stored document_class.
MAPPING: dict[str, tuple[str, dict[str, str]]] = {
    "tep": ("commercial", {"procurement_stage": "tep"}),
    "eoi": ("commercial", {"procurement_stage": "eoi"}),
    "rft": ("commercial", {"procurement_stage": "rft"}),
    "addendum": ("commercial", {"procurement_stage": "addendum"}),
    "tender_submission": ("commercial", {"procurement_stage": "submission"}),
    "evaluation": ("commercial", {"procurement_stage": "evaluation"}),
    "trr": ("commercial", {"procurement_stage": "trr"}),
    "planning_instrument": ("statutory_instrument", {}),
    "doctrine": ("report", {"reference_kind": "doctrine"}),
    "reference_guide": ("report", {"reference_kind": "reference_guide"}),
    "corpus_catalog": ("schedule", {"synthetic": "true"}),
    "inbox_pending": ("unknown", {}),
}


def apply_class_mapping(
    document_class: str, metadata: dict | None
) -> tuple[str, dict]:
    existing = dict(metadata or {})
    mapped = MAPPING.get(document_class)
    if mapped is None:
        return document_class, existing
    new_class, extra = mapped
    return new_class, {**existing, **extra, LEGACY_CLASS_MARKER: document_class}


def revert_class_mapping(
    document_class: str, metadata: dict | None
) -> tuple[str, dict]:
    existing = dict(metadata or {})
    old = existing.get(LEGACY_CLASS_MARKER)
    if not isinstance(old, str) or old not in MAPPING:
        return document_class, existing
    _new, extra = MAPPING[old]
    restored = {
        key: value
        for key, value in existing.items()
        if key != LEGACY_CLASS_MARKER
        and not (key in extra and extra[key] == value)
    }
    return old, restored


def _count_class(conn, document_class: str) -> int:
    return int(
        conn.execute(
            text("SELECT count(*) FROM source_documents WHERE document_class = :c"),
            {"c": document_class},
        ).scalar()
        or 0
    )


def _print_counts(conn, label: str) -> None:
    print(f"taxonomy migration {label}:")
    for old_class in MAPPING:
        print(f"  {old_class}: {_count_class(conn, old_class)}")
    print(f"  statutory_instrument: {_count_class(conn, 'statutory_instrument')}")
    print(f"  commercial: {_count_class(conn, 'commercial')}")
    print(f"  report: {_count_class(conn, 'report')}")
    print(f"  schedule: {_count_class(conn, 'schedule')}")
    print(f"  unknown: {_count_class(conn, 'unknown')}")


def upgrade() -> None:
    conn = op.get_bind()
    _print_counts(conn, "before")
    for old_class, (new_class, extra) in MAPPING.items():
        payload = {**extra, LEGACY_CLASS_MARKER: old_class}
        conn.execute(
            text(
                """
                UPDATE source_documents
                SET document_class = :new_class,
                    document_metadata = COALESCE(document_metadata, '{}'::jsonb)
                      || CAST(:extra_metadata AS jsonb)
                WHERE document_class = :old_class
                """
            ),
            {
                "new_class": new_class,
                "extra_metadata": json.dumps(payload),
                "old_class": old_class,
            },
        )
    _print_counts(conn, "after")
    conn.execute(
        text(
            """
            UPDATE source_documents
            SET document_metadata = document_metadata - :marker
            WHERE document_metadata ? :marker
            """
        ),
        {"marker": LEGACY_CLASS_MARKER},
    )
    assert_canonical_classes(conn)


def assert_canonical_classes(conn) -> None:
    from typing import get_args

    from ingest.types import DocumentClass

    classes = get_args(DocumentClass)
    placeholders = ", ".join(f":c{i}" for i in range(len(classes)))
    params = {f"c{i}": value for i, value in enumerate(classes)}
    leftover = conn.execute(
        text(
            f"""
            SELECT document_class, count(*)
            FROM source_documents
            WHERE document_class NOT IN ({placeholders})
            GROUP BY document_class
            """
        ),
        params,
    ).all()
    assert leftover == [], f"non-canonical classes remain: {leftover}"


def downgrade() -> None:
    conn = op.get_bind()
    _print_counts(conn, "downgrade before")
    for old_class, (_new_class, extra) in MAPPING.items():
        strip_expr = "document_metadata"
        for key in (LEGACY_CLASS_MARKER, *extra.keys()):
            strip_expr += f" - '{key}'"
        conn.execute(
            text(
                f"""
                UPDATE source_documents
                SET document_class = :old_class,
                    document_metadata = {strip_expr}
                WHERE document_metadata ->> :marker = :old_class
                """
            ),
            {
                "old_class": old_class,
                "marker": LEGACY_CLASS_MARKER,
            },
        )
    _print_counts(conn, "downgrade after")
