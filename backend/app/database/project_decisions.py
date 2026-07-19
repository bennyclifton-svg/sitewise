from __future__ import annotations

from typing import Any

from app.projects.decisions import locked_selections, sync_decisions_from_markdown
from app.sitewise.pmp_decisions import PmpDecision

__all__ = [
    "decision_row_from_pmp",
    "locked_selections",
    "sync_decisions_from_markdown",
]


def decision_row_from_pmp(decision: PmpDecision) -> dict[str, Any]:
    return {
        "decision_id": decision.id,
        "section": decision.section,
        "label": decision.label,
        "options": [dict(option) for option in decision.options],
        "selected": decision.selected,
        "source": decision.source,
    }
