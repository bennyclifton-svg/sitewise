"""YAML frontmatter parsing for platform markdown documents.

Seed guides and doctrine carry a frontmatter contract (tier, loaded_by,
topics, summary, required_by, doctrine_anchors — see data/README.md).
The parsed block is persisted into SourceDocument.document_metadata under
the "frontmatter" key so the platform-knowledge catalog can select and
describe documents without re-reading files.
"""

from __future__ import annotations

import datetime

import structlog
import yaml

logger = structlog.get_logger(__name__)


def parse_frontmatter(content: str) -> dict[str, object]:
    """Return the leading YAML frontmatter block as JSON-safe data.

    Returns {} when the document has no frontmatter, the block never
    closes, the YAML is invalid, or the block is not a mapping.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    close_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            close_index = index
            break
    if close_index is None:
        return {}

    block = "\n".join(lines[1:close_index])
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        logger.warning("frontmatter_parse_failed")
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): _json_safe(value) for key, value in data.items()}


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
