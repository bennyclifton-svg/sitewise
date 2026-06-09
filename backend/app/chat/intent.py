import re
from typing import Literal

PlatformInventoryScope = Literal["seed", "all"]

_CATALOG_QUESTION = re.compile(
    r"\b("
    r"what projects|which projects|list projects|projects are you aware|"
    r"what corpus|what(?:'s| is) in the corpus|indexed projects"
    r")\b",
    re.IGNORECASE,
)

_SEED_INVENTORY = re.compile(
    r"\b("
    r"list(?:\s+the)?\s+seed|seed\s+(?:knowledge\s+)?files|seed\s+documents|"
    r"what\s+seed|which\s+seed|seed\s+knowledge|seed\s+guides"
    r")\b",
    re.IGNORECASE,
)

_PLATFORM_INVENTORY = re.compile(
    r"\b("
    r"platform\s+knowledge|sitewise\s+knowledge|"
    r"list(?:\s+the)?\s+(?:platform|doctrine|reference|skill|template)|"
    r"what(?:'s|\s+is)\s+ingested|knowledge\s+files\s+you\s+have\s+ingested"
    r")\b",
    re.IGNORECASE,
)

_DRAWING_REGISTER = re.compile(
    r"\b("
    r"drawing\s+register|list(?:\s+the)?\s+drawings|show(?:\s+me)?\s+the\s+drawings|"
    r"what\s+drawings|which\s+drawings|indexed\s+drawings"
    r")\b",
    re.IGNORECASE,
)

_CONTENT_HINTS = (
    "trr",
    "tender",
    "evaluation",
    "claim",
    "contract",
    "specification",
    "summar",
    "tell me about",
    "compare",
    "block b",
    "petersham",
    "defects",
    "doctrine",
)

_DRAWING_CONTENT_HINTS = (
    "what does",
    "describe",
    "details",
    "say about",
    "content of",
    "show me details",
)


def is_corpus_catalog_question(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    if _CATALOG_QUESTION.search(normalized):
        return True
    lower = normalized.lower()
    return lower.startswith("hello") and "project" in lower


def is_pure_catalog_question(text: str) -> bool:
    if not is_corpus_catalog_question(text):
        return False
    lower = text.lower()
    return not any(hint in lower for hint in _CONTENT_HINTS)


def platform_inventory_scope(text: str) -> PlatformInventoryScope | None:
    normalized = text.strip()
    if not normalized:
        return None
    if _SEED_INVENTORY.search(normalized):
        return "seed"
    if _PLATFORM_INVENTORY.search(normalized):
        return "all"
    lower = normalized.lower()
    if "seed" in lower and any(
        token in lower for token in ("list", "ingested", "indexed", "files", "documents")
    ):
        return "seed"
    return None


def is_drawing_register_question(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    if not _DRAWING_REGISTER.search(normalized):
        return False
    lower = normalized.lower()
    return not any(hint in lower for hint in _DRAWING_CONTENT_HINTS)
