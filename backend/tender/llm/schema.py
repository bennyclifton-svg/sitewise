from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from typing import Any


def openai_strict_json_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy shaped for OpenAI strict structured outputs."""

    return _stricten(deepcopy(dict(schema)))


def _stricten(node: Any) -> Any:
    if isinstance(node, list):
        return [_stricten(item) for item in node]
    if not isinstance(node, dict):
        return node

    node.pop("default", None)
    for key, value in list(node.items()):
        node[key] = _stricten(value)

    properties = node.get("properties")
    if isinstance(properties, dict):
        node["required"] = list(properties)
        node["additionalProperties"] = False
    elif node.get("type") == "object":
        node["additionalProperties"] = False

    return node
