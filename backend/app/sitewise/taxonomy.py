"""Declarative PMP 2.0 taxonomy loader.

The JSON files under data/taxonomy are the source of truth. This module keeps
the runtime deterministic: validate combinations, expose typed options, derive
risk flags, and calculate section emphasis weights without LLM involvement.
"""

from __future__ import annotations

import json
import re
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
    """Load a taxonomy JSON file, re-reading when the file mtime changes.

    Uvicorn --reload only watches ``backend/``, so edits under ``data/taxonomy/``
    would otherwise stick in process memory until a full restart.
    """
    path = TAXONOMY_ROOT / filename
    return _cached_json_file(str(path.resolve()), path.stat().st_mtime_ns)


@lru_cache(maxsize=32)
def _cached_json_file(path: str, mtime_ns: int) -> dict[str, Any]:
    del mtime_ns  # cache key only; content is read from path
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _building_config() -> dict[str, Any]:
    return _read_json("building-classes.json")


def _complexity_config() -> dict[str, Any]:
    return _read_json("complexity-dimensions.json")


def _risk_config() -> dict[str, Any]:
    return _read_json("risk-flags.json")


def _work_scope_config() -> dict[str, Any]:
    return _read_json("work-scopes.json")


def _emphasis_config() -> dict[str, Any]:
    return _read_json("emphasis-profiles.json")


def _asset_register_config() -> dict[str, Any]:
    return _read_json("asset-register.json")


def asset_option_values(group: str) -> tuple[ComplexityOption, ...]:
    """Return the allowed options for an asset register field group."""
    return tuple(
        ComplexityOption(value=str(item["value"]), label=str(item["label"]))
        for item in _asset_register_config().get(group, [])
    )


def asset_register_fields() -> tuple[dict[str, Any], ...]:
    """Return the asset register field schema for the profile UI."""
    return tuple(dict(field) for field in _asset_register_config().get("fields", []))


def asset_register_applies_to(work_type: str | None) -> bool:
    """Assets describe what already exists, so a new build has none to register."""
    if not work_type:
        return False
    applies = _asset_register_config().get("applies_to_work_types", [])
    return work_type in {str(value) for value in applies}


def asset_option_label(group: str, value: str | None) -> str | None:
    if not value:
        return None
    for option in asset_option_values(group):
        if option.value == value:
            return option.label
    return value


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


def design_lead_discipline(
    work_type: str | None,
    work_scope: list[str] | tuple[str, ...],
) -> str:
    """Return the discipline that leads design for the dominant scope.

    Each work-scope item lists its consultants most-relevant-first, so the first
    consultant of the first selected scope is the discipline that actually leads
    the work. Architect remains the answer for architectural scope and the
    fallback when no scope is selected — but naming an Architect as design lead
    on a mechanical plant replacement or a fire-services upgrade was wrong.
    """
    for item in work_scope_items_for(work_type, work_scope):
        for consultant in item.consultants:
            name = consultant.strip()
            if name:
                return name
    return "Architect"


def work_scope_items_for(
    work_type: str | None,
    selected_values: list[str] | tuple[str, ...],
) -> tuple[WorkScopeItem, ...]:
    """Return selected work-scope item labels and consultant lists."""
    selected = {value for value in selected_values if value}
    if not work_type or not selected:
        return ()
    return tuple(
        item for item in work_scope_options_for(work_type) if item.value in selected
    )


def work_scope_options_for(work_type: str | None) -> tuple[WorkScopeItem, ...]:
    """Return the complete profiler scope schema applicable to a work type."""
    if not work_type:
        return ()
    raw_work_type = _work_scope_config()["work_types"].get(work_type)
    if not isinstance(raw_work_type, dict):
        return ()
    items: list[WorkScopeItem] = []
    for category in raw_work_type.get("categories", []):
        for raw_item in category.get("items", []):
            value = str(raw_item.get("value", ""))
            if not value:
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


_BUDGET_PATTERN = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(k|m|bn|b|million|billion|thousand)?",
    re.IGNORECASE,
)
_BUDGET_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "million": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
}


def parse_budget_amount(raw: object) -> float | None:
    """Read a dollar figure out of the loose text a PM actually types.

    Handles "$180k", "around $1.4m", "approximately $850,000", "$28m".
    Returns None rather than guessing when nothing parses.
    """
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) if raw > 0 else None
    if not isinstance(raw, str):
        return None
    match = _BUDGET_PATTERN.search(raw.replace("$", " "))
    if match is None:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    suffix = (match.group(2) or "").lower()
    amount *= _BUDGET_MULTIPLIERS.get(suffix, 1)
    return amount if amount > 0 else None


def scale_band_for(budget: object) -> str | None:
    """Resolve the scale band from a budget, or None when no budget is known.

    Without this an $80k plant swap and a $200m tower resolved to the same
    profile and produced documents of the same weight.
    """
    amount = parse_budget_amount(budget)
    if amount is None:
        return None
    for band in _emphasis_config().get("scale_bands", []):
        ceiling = band.get("max_budget")
        if ceiling is None or amount < float(ceiling):
            return str(band["band"])
    return None


def scale_band_word_target(band: str | None) -> int | None:
    """Return the word target for a band; None when the band is unknown."""
    if not band:
        return None
    for item in _emphasis_config().get("scale_bands", []):
        if str(item["band"]) == band and item.get("word_target") is not None:
            return int(item["word_target"])
    return None


def scale_band_word_bounds(
    band: str | None,
    *,
    section_count: int | None = None,
    default_min: int,
    default_max: int,
) -> tuple[int, int]:
    """Scale the acceptable length to the project's size and section count.

    A flat 800-word floor made no sense once small projects legitimately render
    fewer sections and carry a lower word target: the document would be correct
    and still fail validation for being short.
    """
    target = scale_band_word_target(band)
    if target is not None:
        minimum, maximum = int(target * 0.7), int(target * 1.45)
    else:
        minimum, maximum = default_min, default_max
    if section_count is not None and PMP_CORE_SECTIONS:
        ratio = max(section_count, 1) / len(PMP_CORE_SECTIONS)
        minimum = int(minimum * ratio)
    return max(minimum, 1), max(maximum, minimum + 1)


def applicable_sections(
    *,
    work_type: str | None,
    work_scope: list[str] | tuple[str, ...] = (),
    has_assets: bool = False,
) -> tuple[str, ...]:
    """Return the sections this project actually needs.

    Previously every project rendered all eleven, so a plant replacement carried
    an empty FFE schedule and an advisory engagement carried a procurement and
    delivery section it had no use for.
    """
    rules = _emphasis_config().get("applicability", {})
    scope = {str(value) for value in work_scope}
    sections: list[str] = []
    for section in PMP_CORE_SECTIONS:
        rule = rules.get(section)
        if rule is None:
            sections.append(section)
            continue
        if _applicability_matches(
            rule.get("exclude_when"), work_type, scope, has_assets
        ):
            continue
        include = rule.get("include_when")
        if include is not None and not _applicability_matches(
            include, work_type, scope, has_assets
        ):
            continue
        sections.append(section)
    return tuple(sections)


def _applicability_matches(
    condition: dict[str, Any] | None,
    work_type: str | None,
    scope: set[str],
    has_assets: bool,
) -> bool:
    """Any listed trigger firing is enough; an absent condition never matches."""
    if not condition:
        return False
    work_types = {str(value) for value in condition.get("work_type_any", [])}
    if work_types and work_type in work_types:
        return True
    scopes = {str(value) for value in condition.get("work_scope_any", [])}
    if scopes and scopes.intersection(scope):
        return True
    return bool(condition.get("has_assets")) and has_assets


def section_weights_for(
    *,
    building_class: str | None,
    work_type: str | None,
    work_scope: list[str],
    risk_flags: list[str],
    scale_band: str | None = None,
    sections: tuple[str, ...] | None = None,
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
            scale_band=scale_band,
        ):
            for section, boost in modifier.get("boost", {}).items():
                if section in weights:
                    weights[section] += float(boost)
    if sections is not None:
        allowed = set(sections)
        weights = {
            section: value if section in allowed else 0.0
            for section, value in weights.items()
        }
    return _normalise_weights(weights)


def _modifier_matches(
    when: dict[str, Any],
    *,
    building_class: str | None,
    work_type: str | None,
    work_scope: list[str],
    risk_flags: list[str],
    scale_band: str | None = None,
) -> bool:
    if "building_class" in when and when["building_class"] != building_class:
        return False
    if "work_type" in when and when["work_type"] != work_type:
        return False
    if "scale_band" in when and when["scale_band"] != scale_band:
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
        "asset_register": {
            "applies_to_work_types": list(
                _asset_register_config().get("applies_to_work_types", [])
            ),
            "fields": [dict(field) for field in asset_register_fields()],
            "condition": [asdict(option) for option in asset_option_values("condition")],
            "action": [asdict(option) for option in asset_option_values("action")],
        },
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
