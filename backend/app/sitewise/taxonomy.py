"""Declarative PMP 2.0 taxonomy loader.

The JSON files under data/taxonomy are the source of truth. This module keeps
the runtime deterministic: validate combinations, expose typed options, derive
risk flags, and calculate section emphasis weights without LLM involvement.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TAXONOMY_ROOT = REPO_ROOT / "data" / "taxonomy"


@dataclass(frozen=True, slots=True)
class WorkType:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class ScaleField:
    key: str
    label: str
    type: str = "text"
    typical: str | None = None
    placeholder: str | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None


@dataclass(frozen=True, slots=True)
class Subclass:
    value: str
    label: str
    ncc_class: str | None
    scale_fields: tuple[ScaleField, ...]


@dataclass(frozen=True, slots=True)
class BuildingClass:
    value: str
    label: str
    multi_subclass: bool
    work_types: tuple[str, ...]
    subclasses: tuple[Subclass, ...]


@dataclass(frozen=True, slots=True)
class ComplexityOption:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class ComplexityDimension:
    key: str
    label: str
    options: tuple[ComplexityOption, ...]


@dataclass(frozen=True, slots=True)
class RiskFlag:
    value: str
    severity: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class WorkScopeItem:
    value: str
    label: str
    consultants: tuple[str, ...]
    risk_flag: str | None = None
    complexity_points: int | None = None


def _read_json(filename: str) -> dict[str, Any]:
    return json.loads((TAXONOMY_ROOT / filename).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _building_config() -> dict[str, Any]:
    return _read_json("building-classes.json")


@lru_cache(maxsize=1)
def _complexity_config() -> dict[str, Any]:
    return _read_json("complexity-dimensions.json")


@lru_cache(maxsize=1)
def _risk_config() -> dict[str, Any]:
    return _read_json("risk-flags.json")


@lru_cache(maxsize=1)
def _work_scope_config() -> dict[str, Any]:
    return _read_json("work-scopes.json")


@lru_cache(maxsize=1)
def _emphasis_config() -> dict[str, Any]:
    return _read_json("emphasis-profiles.json")


def _scale_field(raw: dict[str, Any]) -> ScaleField:
    return ScaleField(
        key=str(raw["key"]),
        label=str(raw["label"]),
        type=str(raw.get("type", "text")),
        typical=str(raw["typical"]) if "typical" in raw else None,
        placeholder=str(raw["placeholder"]) if "placeholder" in raw else None,
        minimum=raw.get("min"),
        maximum=raw.get("max"),
    )


def _subclass(raw: dict[str, Any]) -> Subclass:
    return Subclass(
        value=str(raw["value"]),
        label=str(raw["label"]),
        ncc_class=str(raw["ncc_class"]) if raw.get("ncc_class") is not None else None,
        scale_fields=tuple(_scale_field(field) for field in raw.get("scale_fields", [])),
    )


def _building_class(raw: dict[str, Any]) -> BuildingClass:
    return BuildingClass(
        value=str(raw["value"]),
        label=str(raw["label"]),
        multi_subclass=bool(raw.get("multi_subclass", False)),
        work_types=tuple(str(value) for value in raw.get("work_types", [])),
        subclasses=tuple(_subclass(item) for item in raw.get("subclasses", [])),
    )


@lru_cache(maxsize=1)
def work_types() -> tuple[WorkType, ...]:
    return tuple(
        WorkType(value=str(item["value"]), label=str(item["label"]))
        for item in _building_config()["work_types"]
    )


@lru_cache(maxsize=1)
def building_classes() -> tuple[BuildingClass, ...]:
    return tuple(_building_class(item) for item in _building_config()["building_classes"])


def subclasses_for(building_class: str) -> tuple[Subclass, ...]:
    cls = _building_class_by_value().get(building_class)
    return cls.subclasses if cls is not None else ()


def scale_fields_for(building_class: str, subclass: str) -> tuple[ScaleField, ...]:
    for item in subclasses_for(building_class):
        if item.value == subclass:
            return item.scale_fields
    return ()


def complexity_dimensions_for(
    building_class: str,
    subclasses: list[str] | tuple[str, ...] | None = None,
) -> tuple[ComplexityDimension, ...]:
    config = _complexity_config()
    raw_dimensions: list[dict[str, Any]] = list(config["universal"])
    raw_dimensions.extend(config.get("class_overlays", {}).get(building_class, []))
    for subclass in subclasses or []:
        raw_dimensions.extend(
            config.get("subclass_overlays", {})
            .get(building_class, {})
            .get(subclass, [])
        )
    return tuple(_complexity_dimension(item) for item in raw_dimensions)


def _complexity_dimension(raw: dict[str, Any]) -> ComplexityDimension:
    return ComplexityDimension(
        key=str(raw["key"]),
        label=str(raw["label"]),
        options=tuple(
            ComplexityOption(value=str(option["value"]), label=str(option["label"]))
            for option in raw.get("options", [])
        ),
    )


@lru_cache(maxsize=1)
def risk_flag_definitions() -> dict[str, RiskFlag]:
    return {
        key: RiskFlag(
            value=key,
            severity=str(raw["severity"]),
            title=str(raw["title"]),
            description=str(raw["description"]),
        )
        for key, raw in _risk_config()["definitions"].items()
    }


def derive_risk_flags(complexity: dict[str, str], work_scope: list[str]) -> list[RiskFlag]:
    definitions = risk_flag_definitions()
    work_scope_values = set(work_scope)
    derived: list[RiskFlag] = []
    seen: set[str] = set()
    for rule in _risk_config().get("derivations", []):
        flag = str(rule.get("flag", ""))
        if flag in seen or flag not in definitions:
            continue
        when = rule.get("when", {})
        if _risk_rule_matches(when, complexity, work_scope_values):
            seen.add(flag)
            derived.append(definitions[flag])
    return derived


def work_scope_items_for(
    work_type: str | None,
    selected_values: list[str] | tuple[str, ...],
) -> tuple[WorkScopeItem, ...]:
    """Return selected work-scope item labels and consultant lists."""
    selected = {value for value in selected_values if value}
    if not work_type or not selected:
        return ()
    raw_work_type = _work_scope_config()["work_types"].get(work_type)
    if not isinstance(raw_work_type, dict):
        return ()
    items: list[WorkScopeItem] = []
    for category in raw_work_type.get("categories", []):
        for raw_item in category.get("items", []):
            value = str(raw_item.get("value", ""))
            if value not in selected:
                continue
            items.append(
                WorkScopeItem(
                    value=value,
                    label=str(raw_item.get("label", value)),
                    consultants=tuple(
                        str(consultant)
                        for consultant in raw_item.get("consultants", [])
                    ),
                    risk_flag=(
                        str(raw_item["riskFlag"])
                        if raw_item.get("riskFlag") is not None
                        else None
                    ),
                    complexity_points=(
                        int(raw_item["complexityPoints"])
                        if raw_item.get("complexityPoints") is not None
                        else None
                    ),
                )
            )
    return tuple(items)


def complexity_option_labels(
    *,
    building_class: str | None,
    subclasses: tuple[str, ...],
    complexity: dict[str, str],
) -> dict[str, str]:
    """Map selected complexity option values to their display labels."""
    if not building_class:
        return {}
    dimensions = complexity_dimensions_for(building_class, subclasses)
    labels: dict[str, str] = {}
    for dimension in dimensions:
        selected = complexity.get(dimension.key)
        if not selected:
            continue
        option = next(
            (item for item in dimension.options if item.value == selected),
            None,
        )
        labels[dimension.key] = (
            f"{dimension.label}: {option.label if option else selected}"
        )
    return labels


def _risk_rule_matches(
    when: dict[str, Any],
    complexity: dict[str, str],
    work_scope_values: set[str],
) -> bool:
    if "dimension" in when:
        dimension = str(when["dimension"])
        values = {str(value) for value in when.get("values", [])}
        return complexity.get(dimension) in values
    if "work_scope_any" in when:
        values = {str(value) for value in when.get("work_scope_any", [])}
        return bool(values.intersection(work_scope_values))
    return False


def validate_project_taxonomy(
    *,
    building_class: str | None,
    work_type: str | None,
    subclasses: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    building_class = _clean(building_class)
    work_type = _clean(work_type)
    clean_subclasses = [_clean(item) for item in subclasses or []]
    clean_subclasses = [item for item in clean_subclasses if item is not None]

    if building_class is None and work_type is None and not clean_subclasses:
        return []

    class_record = _building_class_by_value().get(building_class or "")
    if class_record is None:
        errors.append(f"Unknown building_class: {building_class!r}")

    work_type_values = {item.value for item in work_types()}
    if work_type is not None and work_type not in work_type_values:
        errors.append(f"Unknown work_type: {work_type!r}")

    if class_record is not None and work_type is not None:
        if work_type not in class_record.work_types:
            errors.append(
                f"work_type {work_type!r} is not valid for {building_class!r}"
            )

    if clean_subclasses and class_record is None:
        errors.append("subclasses require a valid building_class")
    elif class_record is not None:
        valid_subclasses = {item.value for item in class_record.subclasses}
        for subclass in clean_subclasses:
            if subclass not in valid_subclasses:
                errors.append(
                    f"Unknown subclass for {building_class!r}: {subclass!r}"
                )
        if len(clean_subclasses) > 1 and not class_record.multi_subclass:
            errors.append(f"{building_class!r} allows only one subclass")

    return errors


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@lru_cache(maxsize=1)
def _building_class_by_value() -> dict[str, BuildingClass]:
    return {item.value: item for item in building_classes()}


PMP_CORE_SECTIONS: tuple[str, ...] = tuple(_emphasis_config()["sections"])


def section_weights_for(
    *,
    building_class: str | None,
    work_type: str | None,
    work_scope: list[str],
    risk_flags: list[str],
) -> dict[str, float]:
    config = _emphasis_config()
    key = f"{building_class}|{work_type}"
    raw_weights = config["base_weights"].get(key, config["base_weights"]["default"])
    weights = {section: float(raw_weights.get(section, 0.0)) for section in PMP_CORE_SECTIONS}

    for modifier in config.get("modifiers", []):
        if _modifier_matches(
            modifier.get("when", {}),
            building_class=building_class,
            work_type=work_type,
            work_scope=work_scope,
            risk_flags=risk_flags,
        ):
            for section, boost in modifier.get("boost", {}).items():
                if section in weights:
                    weights[section] += float(boost)
    return _normalise_weights(weights)


def _modifier_matches(
    when: dict[str, Any],
    *,
    building_class: str | None,
    work_type: str | None,
    work_scope: list[str],
    risk_flags: list[str],
) -> bool:
    if "building_class" in when and when["building_class"] != building_class:
        return False
    if "work_type" in when and when["work_type"] != work_type:
        return False
    if "risk_flag" in when and when["risk_flag"] not in set(risk_flags):
        return False
    if "work_scope_any" in when:
        values = {str(value) for value in when["work_scope_any"]}
        if not values.intersection(work_scope):
            return False
    return True


def _normalise_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in weights.values())
    if total <= 0:
        equal = 1.0 / len(weights)
        return {section: equal for section in weights}
    return {section: max(value, 0.0) / total for section, value in weights.items()}


def taxonomy_options_payload() -> dict[str, Any]:
    return {
        "work_types": list(_building_config()["work_types"]),
        "building_classes": list(_building_config()["building_classes"]),
        "complexity_dimensions": {
            item.value: [_dimension_payload(dimension) for dimension in complexity_dimensions_for(item.value)]
            for item in building_classes()
        },
        "risk_flags": {
            key: asdict(flag) for key, flag in risk_flag_definitions().items()
        },
        "work_scopes": _work_scope_config()["work_types"],
        "emphasis_profiles": {
            "sections": list(PMP_CORE_SECTIONS),
            "base_weights": _emphasis_config()["base_weights"],
            "modifiers": _emphasis_config()["modifiers"],
        },
    }


def _dimension_payload(dimension: ComplexityDimension) -> dict[str, Any]:
    return {
        "key": dimension.key,
        "label": dimension.label,
        "options": [asdict(option) for option in dimension.options],
    }
