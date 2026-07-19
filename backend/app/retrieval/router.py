from app.chat.intent import (
    is_corpus_catalog_question,
    is_drawing_register_question,
    is_pure_catalog_question,
    platform_inventory_scope,
)
from app.retrieval.schemas import RetrievalFilters


_PLATFORM_KNOWLEDGE_HINTS = (
    "pmp",
    "project management plan",
    "seed",
    "doctrine",
    "sitewise",
    "platform",
    "skill",
    "template",
    "programme",
    "program",
    "residential construction",
    "defects",
    "dlp",
)

_PROJECT_EVIDENCE_HINTS = (
    "trr",
    "tender",
    "evaluation",
    "submission",
    "claim",
    "contract",
    "specification",
    "summar",
    "tell me about",
    "compare",
    "block b",
    "petersham",
    "correspondence",
    "drawing",
    "rft",
    "addendum",
    "eoi",
    "tep",
)


def should_use_whole_document_path(
    user_text: str,
    filters: RetrievalFilters | None,
) -> bool:
    if platform_inventory_scope(user_text) is not None:
        return False
    if is_drawing_register_question(user_text):
        return False
    if is_corpus_catalog_question(user_text) and is_pure_catalog_question(user_text):
        return False
    if filters is not None and filters.cross_project:
        return False
    if (
        filters is not None
        and filters.active_project_id
        and not filters.include_platform_knowledge
    ):
        return False

    lower = user_text.lower()
    if any(hint in lower for hint in _PROJECT_EVIDENCE_HINTS):
        return False
    if any(hint in lower for hint in _PLATFORM_KNOWLEDGE_HINTS):
        return True
    if filters is None:
        return True
    if filters.include_platform_knowledge:
        return True
    return False
