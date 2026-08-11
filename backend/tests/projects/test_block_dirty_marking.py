"""F6: relevant block mutations mark project dirty categories."""

from __future__ import annotations

from app.projects.dependencies import dirty_categories_for_block_sections


def test_consultant_section_block_marks_consultants_dirty() -> None:
    assert dirty_categories_for_block_sections(["consultants"]) == (
        "consultants_dirty",
    )


def test_ffe_schedule_section_marks_ffe_dirty() -> None:
    assert dirty_categories_for_block_sections(["ffe-schedule"]) == ("ffe_dirty",)


def test_scope_section_no_longer_marks_ffe_dirty() -> None:
    assert "ffe_dirty" not in dirty_categories_for_block_sections(
        ["scope-client-requirements"]
    )


def test_unrelated_actions_section_marks_nothing() -> None:
    assert dirty_categories_for_block_sections(["actions-decisions"]) == ()
