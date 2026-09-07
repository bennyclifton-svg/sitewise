"""Lossless, deterministic accounting for saved profile inputs in a PMP."""

from __future__ import annotations

import html
import re

from app.schemas.projects import ProjectProfileView

_PROFILE_BLOCK = re.compile(
    r"\n*<!-- profile-basis:start -->.*?<!-- profile-basis:end -->", re.S
)
_SECTIONS = {
    "work_scope": "Brief",
    "scope_narrative": "Brief",
    "assets": "Brief",
    "budget": "Cost Planning",
    "complexity": "Brief; Risks and mitigations",
    "user_role": "Actions and decisions",
}


def profile_clarifications(profile: ProjectProfileView) -> list[str]:
    notes = []
    if (
        "decontamination" in profile.work_scope
        and profile.complexity.get("contamination_level") == "nil"
    ):
        notes.append(
            "Decontamination is selected although contamination is recorded as nil. Confirm whether an allowance is required."
        )
    subclasses = [
        item if isinstance(item, str) else item.value for item in profile.subclasses
    ]
    if "vertical_transport" in profile.work_scope and "house" in subclasses:
        notes.append(
            "Vertical transport is selected for this house. Confirm whether a lift or other vertical transport is required."
        )
    return notes


def profile_basis_rows(profile: ProjectProfileView) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []

    def visit(path: str, value: object) -> None:
        if value is None or value == "" or value == [] or value == {}:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                visit(f"{path}.{key}", item)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(f"{path}.{index + 1}", item)
        else:
            section = _SECTIONS.get(path.split(".")[0], "Project Summary")
            if path == "complexity.procurement_route":
                section = "Procurement and Delivery"
            elif path == "complexity.planning":
                section = "Planning and Compliance"
            rows.append((path, str(value), section))

    for key, value in profile.model_dump(
        mode="json", exclude={"project_id", "profile_revision"}
    ).items():
        visit(key, value)
    return rows


def apply_profile_basis(markdown: str, profile: ProjectProfileView) -> str:
    """Replace the coverage appendix on refresh; never rely on model recall."""
    markdown = _PROFILE_BLOCK.sub("", markdown).rstrip()
    lines = ["", "<!-- profile-basis:start -->"]
    notes = profile_clarifications(profile)
    if notes:
        lines.extend(
            ["## Profile clarifications", "", *[f"- {note}" for note in notes], ""]
        )
    lines.extend(
        [
            "## Profile basis",
            "",
            f"Saved profile revision {profile.profile_revision}. These are user-supplied inputs, not independently verified document evidence. "
            "The section column identifies where each input belongs; this appendix preserves every populated value. "
            "Platform guidance informs the plan but does not verify these inputs. Missing information remains to be confirmed.",
            "",
            "| Profile field | Saved value | Plan section |",
            "| --- | --- | --- |",
        ]
    )
    for row in profile_basis_rows(profile):
        row = (row[0].replace("_", " ").replace(".", " / "), row[1].replace("_", " "), row[2])
        cells = [
            html.escape(cell)
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\n", " ")
            .replace("\r", " ")
            for cell in row
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("<!-- profile-basis:end -->")
    return markdown + "\n" + "\n".join(lines) + "\n"
