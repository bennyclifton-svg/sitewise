"""Canonical Project Profile export content."""

from __future__ import annotations

from app.schemas.projects import ProjectAsset, ProjectProfileView, ProjectSubclassSelection
from app.sitewise.taxonomy import (
    building_class_label,
    complexity_dimensions_for,
    scale_field_label,
    scale_fields_for,
    subclass_label,
    work_scope_groups_for,
    work_type_label,
)

_NOT_STATED = "Not stated"

_ASSET_FIELDS = (
    ("type", "Type"),
    ("count", "Count"),
    ("location", "Location"),
    ("make_model", "Make / model"),
    ("capacity", "Capacity"),
    ("age_years", "Age (years)"),
    ("condition", "Condition"),
    ("action", "Action"),
    ("replacement_spec", "Replacement spec"),
    ("notes", "Notes"),
)


def profile_export_markdown(profile: ProjectProfileView) -> str:
    subclass_values = _subclass_values(profile)
    rows = [
        ("Project name", _text(profile.title)),
        ("Site address", _text(profile.site_address)),
        ("Client / owners", _text(profile.client)),
        ("State", _text(profile.state)),
        ("Class", building_class_label(profile.building_class) or _NOT_STATED),
        ("Work type", work_type_label(profile.work_type) or _NOT_STATED),
        ("Subclass", _subclass_display(profile) or _NOT_STATED),
        ("Budget", _text(profile.budget)),
        *_scale_rows(profile, subclass_values),
        *_complexity_rows(profile, subclass_values),
    ]

    sections = [
        "# Project Profile",
        "",
        _markdown_row(["Field", "Value"]),
        _markdown_row(["---", "---"]),
        *[_markdown_row([label, value]) for label, value in rows],
    ]

    sections.extend(["", "## Work scope", ""])
    sections.extend(_work_scope_lines(profile))

    narrative = [item.strip() for item in profile.scope_narrative if item.strip()]
    if narrative:
        sections.extend(["", "## Scope notes", "", *narrative])

    if profile.assets:
        headers = [label for key, label in _ASSET_FIELDS if _asset_column_used(profile.assets, key)]
        keys = [key for key, label in _ASSET_FIELDS if _asset_column_used(profile.assets, key)]
        sections.extend(
            [
                "",
                "## Assets",
                "",
                _markdown_row(headers),
                _markdown_row(["---"] * len(headers)),
                *[
                    _markdown_row([_asset_cell(asset, key) for key in keys])
                    for asset in profile.assets
                ],
            ]
        )

    return "\n".join(sections).rstrip() + "\n"


def _scale_rows(
    profile: ProjectProfileView,
    subclass_values: tuple[str, ...],
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    if profile.building_class:
        for subclass in subclass_values:
            for field in scale_fields_for(profile.building_class, subclass):
                if field.key in seen:
                    continue
                seen.add(field.key)
                rows.append((field.label, _scale_value(profile.scale.get(field.key))))
    for key, value in profile.scale.items():
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            (
                scale_field_label(profile.building_class, subclass_values, key),
                _scale_value(value),
            )
        )
    return rows


def _complexity_rows(
    profile: ProjectProfileView,
    subclass_values: tuple[str, ...],
) -> list[tuple[str, str]]:
    if not profile.building_class:
        return [
            (key.replace("_", " ").title(), _text(str(value) if value else None))
            for key, value in profile.complexity.items()
        ]
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for dimension in complexity_dimensions_for(profile.building_class, subclass_values):
        seen.add(dimension.key)
        selected = profile.complexity.get(dimension.key)
        if not selected:
            rows.append((dimension.label, _NOT_STATED))
            continue
        option = next(
            (item for item in dimension.options if item.value == str(selected)),
            None,
        )
        rows.append((dimension.label, option.label if option else str(selected)))
    for key, value in profile.complexity.items():
        if key in seen:
            continue
        rows.append((key.replace("_", " ").title(), _text(str(value) if value else None)))
    return rows


def _work_scope_lines(profile: ProjectProfileView) -> list[str]:
    groups = work_scope_groups_for(profile.work_type, profile.work_scope)
    if not groups:
        return [_NOT_STATED]
    lines: list[str] = []
    for category, items in groups:
        if lines:
            lines.append("")
        lines.append(f"### {category}")
        lines.append("")
        lines.extend(f"- {item}" for item in items)
    return lines


def _subclass_values(profile: ProjectProfileView) -> tuple[str, ...]:
    return tuple(
        item if isinstance(item, str) else item.value for item in profile.subclasses
    )


def _subclass_display(profile: ProjectProfileView) -> str:
    labels: list[str] = []
    for item in profile.subclasses:
        if isinstance(item, ProjectSubclassSelection):
            labels.append(
                item.label or subclass_label(profile.building_class, item.value)
            )
            continue
        labels.append(subclass_label(profile.building_class, item))
    return ", ".join(label for label in labels if label)


def _text(value: str | None) -> str:
    stripped = (value or "").strip()
    return stripped or _NOT_STATED


def _scale_value(value: object) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None or value == "":
        return _NOT_STATED
    return str(value)


def _asset_column_used(assets: list[ProjectAsset], key: str) -> bool:
    return any(_asset_cell(asset, key) for asset in assets)


def _asset_cell(asset: ProjectAsset, key: str) -> str:
    value = getattr(asset, key)
    if value is None or value == "":
        return ""
    return str(value)


def _markdown_row(values: list[str]) -> str:
    return "| " + " | ".join(_markdown_cell(value) for value in values) + " |"


def _markdown_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")
