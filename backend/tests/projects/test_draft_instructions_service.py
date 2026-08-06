import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.projects.draft_instructions_service import (
    AllInstructionsFailedError,
    InstructionInput,
    StaleAnchorError,
    apply_draft_instructions,
    changed_block_ranges,
)
from app.workflows.create_pmp import WorkflowValidationError
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

SECTION_ONE = """\
## Procurement posture

The head builder is procured through a single-stage invited tender.

Tender list lock is scheduled before the DA determination.
"""

SECTION_TWO = """\
## Programme

Slab, frame, lockup and fixing are the tracked milestones.

Practical Completion is targeted for the fourth quarter.
"""

DOCUMENT = f"# Project Management Plan\n\nPreamble sentence.\n\n{SECTION_ONE}\n{SECTION_TWO}"


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="test-project-112",
        title="Chen Residence",
        workspace_path="04-projects/test-project-112",
        phase="brief-planning",
        archetype="new-dwelling",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata=None,
        created_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
    )


def _draft(markdown: str = DOCUMENT, version: int = 3) -> DraftArtifact:
    return DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=version,
        status="draft",
        title="Project Management Plan",
        workspace_path="04-projects/test-project-112/00-brief-pmp/PMP.md",
        author_user_id=USER_ID,
        content_markdown=markdown,
        model="gpt-5.6",
        runtime="clerk-sitewise",
        provenance_metadata={"sections_changed": ["stale"]},
    )


def _anchor(source: str, needle: str, instruction: str) -> InstructionInput:
    start = source.index(needle)
    return InstructionInput(
        anchor_start=start,
        anchor_end=start + len(needle),
        quoted_text=needle,
        instruction=instruction,
    )


def _publisher(markdown_sink: list[str]):
    async def _publish(session, **kwargs):
        markdown_sink.append(kwargs["content_markdown"])
        revision = _draft(kwargs["content_markdown"], version=kwargs["expected_base_version"] + 1)
        revision.provenance_metadata = {"sections_changed": ["stale"]}
        return revision

    return AsyncMock(side_effect=_publish)


def _apply(
    instructions: list[InstructionInput],
    *,
    slice_mock: AsyncMock,
    publish_mock: AsyncMock,
    draft: DraftArtifact | None = None,
):
    with (
        patch("app.projects.draft_instructions_service.run_slice_revision", new=slice_mock),
        patch(
            "app.projects.draft_instructions_service.revise_workflow_artefact",
            new=publish_mock,
        ),
    ):
        return run_async(
            apply_draft_instructions(
                AsyncMock(),
                project=_project(),
                draft=draft if draft is not None else _draft(),
                expected_base_version=3,
                author_user_id=USER_ID,
                instructions=instructions,
            )
        )


def test_untouched_sections_are_byte_identical() -> None:
    """The core contract, inherited from Task 5.6's acceptance test."""
    revised_one = SECTION_ONE.replace(
        "through a single-stage invited tender", "by single-stage invited tender"
    )
    published: list[str] = []
    result = _apply(
        [_anchor(DOCUMENT, "single-stage invited tender", "tighten this")],
        slice_mock=AsyncMock(return_value=revised_one),
        publish_mock=_publisher(published),
    )

    assert result.applied_count == 1
    assert result.failed == []
    assert SECTION_TWO in published[0]
    assert published[0].startswith("# Project Management Plan\n\nPreamble sentence.\n")
    assert "by single-stage invited tender" in published[0]


def test_stale_anchor_raises_before_model_call() -> None:
    slice_mock = AsyncMock()
    publish_mock = AsyncMock()
    stale = InstructionInput(
        anchor_start=0,
        anchor_end=20,
        quoted_text="text that has since been rewritten",
        instruction="tighten this",
    )
    with pytest.raises(StaleAnchorError):
        _apply([stale], slice_mock=slice_mock, publish_mock=publish_mock)

    slice_mock.assert_not_awaited()
    publish_mock.assert_not_awaited()


def test_out_of_bounds_anchor_raises() -> None:
    slice_mock = AsyncMock()
    out_of_bounds = InstructionInput(
        anchor_start=len(DOCUMENT) - 5,
        anchor_end=len(DOCUMENT) + 500,
        quoted_text="anything",
        instruction="tighten this",
    )
    with pytest.raises(StaleAnchorError):
        _apply([out_of_bounds], slice_mock=slice_mock, publish_mock=AsyncMock())

    slice_mock.assert_not_awaited()


def test_anchor_matches_under_whitespace_and_case_folding() -> None:
    start = DOCUMENT.index("Slab, frame, lockup and fixing")
    instruction = InstructionInput(
        anchor_start=start,
        anchor_end=start + len("Slab, frame, lockup and fixing"),
        quoted_text="  slab,   frame, LOCKUP and fixing  ",
        instruction="tighten this",
    )
    result = _apply(
        [instruction],
        slice_mock=AsyncMock(return_value=SECTION_TWO.replace("tracked", "reported")),
        publish_mock=_publisher([]),
    )
    assert result.applied_count == 1


def test_instructions_grouped_by_section() -> None:
    slice_mock = AsyncMock(
        side_effect=[
            SECTION_ONE.replace("single-stage", "two-stage"),
            SECTION_TWO.replace("tracked", "reported"),
        ]
    )
    result = _apply(
        [
            _anchor(DOCUMENT, "single-stage invited tender", "make it two-stage"),
            _anchor(DOCUMENT, "Tender list lock", "clarify timing"),
            _anchor(DOCUMENT, "tracked milestones", "say reported"),
        ],
        slice_mock=slice_mock,
        publish_mock=_publisher([]),
    )

    assert slice_mock.await_count == 2
    assert result.applied_count == 3
    first_call_items = slice_mock.await_args_list[0].kwargs["instructions"]
    assert len(first_call_items) == 2


def test_descending_splice_preserves_offsets() -> None:
    shorter = "## Procurement posture\n\nSingle-stage invited tender.\n"
    longer = SECTION_TWO.replace(
        "Practical Completion is targeted for the fourth quarter.",
        "Practical Completion is targeted for the fourth quarter, subject to weather "
        "and to the Superintendent's assessment of any extension of time.",
    )
    published: list[str] = []
    _apply(
        [
            _anchor(DOCUMENT, "single-stage invited tender", "shorten"),
            _anchor(DOCUMENT, "fourth quarter", "expand"),
        ],
        slice_mock=AsyncMock(side_effect=[shorter, longer]),
        publish_mock=_publisher(published),
    )

    assert "Single-stage invited tender." in published[0]
    assert "subject to weather" in published[0]
    assert "Tender list lock" not in published[0]
    assert published[0].startswith("# Project Management Plan\n\nPreamble sentence.\n")


def test_duplicate_headings_are_addressed_by_section_id() -> None:
    duplicated = (
        "# Plan\n\n"
        "## Notes\n\nFirst notes body.\n\n"
        "## Notes\n\nSecond notes body.\n"
    )
    start = duplicated.index("Second notes body")
    instruction = InstructionInput(
        anchor_start=start,
        anchor_end=start + len("Second notes body"),
        quoted_text="Second notes body",
        instruction="tighten this",
    )
    slice_mock = AsyncMock(return_value="## Notes\n\nSecond notes rewritten.\n")
    published: list[str] = []
    _apply(
        [instruction],
        slice_mock=slice_mock,
        publish_mock=_publisher(published),
        draft=_draft(duplicated),
    )

    assert "First notes body." in published[0]
    assert "Second notes rewritten." in published[0]
    assert "Second notes body" not in published[0]
    assert slice_mock.await_args.kwargs["section_markdown"].startswith("## Notes")
    assert "Second notes body" in slice_mock.await_args.kwargs["section_markdown"]


def test_anchor_outside_any_section_is_reported_not_applied() -> None:
    published: list[str] = []
    result = _apply(
        [
            _anchor(DOCUMENT, "Preamble sentence", "tighten this"),
            _anchor(DOCUMENT, "tracked milestones", "say reported"),
        ],
        slice_mock=AsyncMock(return_value=SECTION_TWO.replace("tracked", "reported")),
        publish_mock=_publisher(published),
    )

    assert result.applied_count == 1
    assert [item.index for item in result.failed] == [0]
    assert "outside any section" in result.failed[0].reason


def test_partial_failure_publishes_good_sections_and_reports_failures() -> None:
    published: list[str] = []
    result = _apply(
        [
            _anchor(DOCUMENT, "single-stage invited tender", "make it two-stage"),
            _anchor(DOCUMENT, "tracked milestones", "say reported"),
        ],
        slice_mock=AsyncMock(
            side_effect=[
                WorkflowValidationError("heading line was modified"),
                SECTION_TWO.replace("tracked", "reported"),
            ]
        ),
        publish_mock=_publisher(published),
    )

    assert result.applied_count == 1
    assert [item.index for item in result.failed] == [0]
    assert "heading line was modified" in result.failed[0].reason
    assert "reported milestones" in published[0]
    assert SECTION_ONE in published[0]


def test_read_transaction_is_released_before_the_model_runs() -> None:
    """Slice calls take minutes; holding the request transaction open across them
    gets the connection killed as idle-in-transaction, and the resulting commit
    failure lands in dependency teardown as a bare 500."""
    order: list[str] = []
    session = AsyncMock()
    session.commit = AsyncMock(side_effect=lambda: order.append("commit"))

    async def _slice(**kwargs):
        order.append("slice")
        return SECTION_ONE.replace("single-stage", "two-stage")

    with (
        patch(
            "app.projects.draft_instructions_service.run_slice_revision",
            new=AsyncMock(side_effect=_slice),
        ),
        patch(
            "app.projects.draft_instructions_service.revise_workflow_artefact",
            new=_publisher([]),
        ),
    ):
        run_async(
            apply_draft_instructions(
                session,
                project=_project(),
                draft=_draft(),
                expected_base_version=3,
                author_user_id=USER_ID,
                instructions=[
                    _anchor(DOCUMENT, "single-stage invited tender", "make it two-stage")
                ],
            )
        )

    assert order.index("commit") < order.index("slice")


def test_revision_is_refreshed_after_provenance_update() -> None:
    """The final flush expires server-generated timestamps such as ``updated_at``.

    The API serializes the returned ORM row synchronously with Pydantic.  Returning
    it while those attributes are expired makes Pydantic attempt async database IO
    and raises ``MissingGreenlet`` while the endpoint builds its response.
    """
    session = AsyncMock()
    revision = _draft(version=4)

    with (
        patch(
            "app.projects.draft_instructions_service.run_slice_revision",
            new=AsyncMock(
                return_value=SECTION_ONE.replace("single-stage", "two-stage")
            ),
        ),
        patch(
            "app.projects.draft_instructions_service.revise_workflow_artefact",
            new=AsyncMock(return_value=revision),
        ),
    ):
        result = run_async(
            apply_draft_instructions(
                session,
                project=_project(),
                draft=_draft(),
                expected_base_version=3,
                author_user_id=USER_ID,
                instructions=[
                    _anchor(
                        DOCUMENT,
                        "single-stage invited tender",
                        "make it two-stage",
                    )
                ],
            )
        )

    session.refresh.assert_awaited_once_with(result.revision)


def test_no_transaction_is_released_when_every_anchor_is_stale() -> None:
    """A stale batch must not commit anything, not even an empty transaction."""
    session = AsyncMock()
    stale = InstructionInput(
        anchor_start=0,
        anchor_end=20,
        quoted_text="text that has since been rewritten",
        instruction="tighten this",
    )
    with (
        patch(
            "app.projects.draft_instructions_service.run_slice_revision", new=AsyncMock()
        ),
        patch(
            "app.projects.draft_instructions_service.revise_workflow_artefact",
            new=AsyncMock(),
        ),
        pytest.raises(StaleAnchorError),
    ):
        run_async(
            apply_draft_instructions(
                session,
                project=_project(),
                draft=_draft(),
                expected_base_version=3,
                author_user_id=USER_ID,
                instructions=[stale],
            )
        )

    session.commit.assert_not_awaited()


def test_unexpected_slice_error_fails_only_its_own_section() -> None:
    """A model timeout must not throw away the sections that succeeded."""
    published: list[str] = []
    result = _apply(
        [
            _anchor(DOCUMENT, "single-stage invited tender", "make it two-stage"),
            _anchor(DOCUMENT, "tracked milestones", "say reported"),
        ],
        slice_mock=AsyncMock(
            side_effect=[
                TimeoutError("read timeout"),
                SECTION_TWO.replace("tracked", "reported"),
            ]
        ),
        publish_mock=_publisher(published),
    )

    assert result.applied_count == 1
    assert [item.index for item in result.failed] == [0]
    assert "TimeoutError" in result.failed[0].reason
    assert "reported milestones" in published[0]
    assert SECTION_ONE in published[0]


def test_cancellation_is_never_swallowed() -> None:
    with pytest.raises(asyncio.CancelledError):
        _apply(
            [_anchor(DOCUMENT, "single-stage invited tender", "make it two-stage")],
            slice_mock=AsyncMock(side_effect=asyncio.CancelledError()),
            publish_mock=AsyncMock(),
        )


def test_changed_ranges_survive_a_revision_that_adds_a_stray_fence() -> None:
    """Offsets come from splice arithmetic, not from re-parsing the result.

    A lone ``` flips split_sections' fence state and swallows every heading
    after it, which used to mis-index the final section lookup.
    """
    revised_one = SECTION_ONE.replace(
        "Tender list lock is scheduled before the DA determination.",
        "Tender list lock is scheduled before the DA determination.\n\n```\nstray fence\n",
    )
    published: list[str] = []
    result = _apply(
        [
            _anchor(DOCUMENT, "Tender list lock", "add an example"),
            _anchor(DOCUMENT, "tracked milestones", "say reported"),
        ],
        slice_mock=AsyncMock(
            side_effect=[revised_one, SECTION_TWO.replace("tracked", "reported")]
        ),
        publish_mock=_publisher(published),
    )

    assert result.applied_count == 2
    ranges = result.revision.provenance_metadata["changed_ranges"]
    assert ranges
    # Every range must still address the text it was computed for.
    assert any(
        "stray fence" in published[0][entry["start"] : entry["end"]] for entry in ranges
    )
    assert any(
        "reported milestones" in published[0][entry["start"] : entry["end"]]
        for entry in ranges
    )


def test_all_failures_raise_without_publishing() -> None:
    publish_mock = AsyncMock()
    with pytest.raises(AllInstructionsFailedError) as exc:
        _apply(
            [_anchor(DOCUMENT, "single-stage invited tender", "make it two-stage")],
            slice_mock=AsyncMock(side_effect=WorkflowValidationError("bad slice")),
            publish_mock=publish_mock,
        )

    publish_mock.assert_not_awaited()
    assert [item.index for item in exc.value.failed] == [0]
    assert "bad slice" in exc.value.failed[0].reason


def test_changed_ranges_cover_only_modified_blocks() -> None:
    revised = SECTION_ONE.replace(
        "Tender list lock is scheduled before the DA determination.",
        "Tender list lock closes before the DA determination.",
    )
    published: list[str] = []
    result = _apply(
        [_anchor(DOCUMENT, "Tender list lock", "tighten this")],
        slice_mock=AsyncMock(return_value=revised),
        publish_mock=_publisher(published),
    )

    ranges = result.revision.provenance_metadata["changed_ranges"]
    assert len(ranges) == 1
    sliced = published[0][ranges[0]["start"] : ranges[0]["end"]]
    assert sliced.strip() == "Tender list lock closes before the DA determination."


def test_provenance_records_instructions_and_sections_changed() -> None:
    revised = SECTION_ONE.replace("single-stage", "two-stage")
    result = _apply(
        [_anchor(DOCUMENT, "single-stage invited tender", "make it two-stage")],
        slice_mock=AsyncMock(return_value=revised),
        publish_mock=_publisher([]),
    )

    provenance = result.revision.provenance_metadata
    assert provenance["sections_changed"] == ["Procurement posture"]
    applied = provenance["applied_instructions"]
    assert len(applied) == 1
    assert applied[0]["section_id"] == "procurement-posture"
    assert applied[0]["instruction"] == "make it two-stage"
    assert applied[0]["quoted_text"] == "single-stage invited tender"
    assert applied[0]["anchor"]["start"] == DOCUMENT.index("single-stage invited tender")


def test_provenance_truncates_long_quotes() -> None:
    long_quote = DOCUMENT[DOCUMENT.index("The head builder") :][:600]
    start = DOCUMENT.index(long_quote)
    instruction = InstructionInput(
        anchor_start=start,
        anchor_end=start + len(long_quote),
        quoted_text=long_quote,
        instruction="tighten this",
    )
    result = _apply(
        [instruction],
        slice_mock=AsyncMock(return_value=SECTION_ONE.replace("single-stage", "two-stage")),
        publish_mock=_publisher([]),
    )

    quoted = result.revision.provenance_metadata["applied_instructions"][0]["quoted_text"]
    assert len(quoted) <= 500


def test_normalization_applied_before_anchor_check() -> None:
    raw = DOCUMENT.replace(
        "Tender list lock is scheduled before the DA determination.",
        "- | Section | Status |\n- | --- | --- |",
    )
    normalized = raw.replace("- | Section | Status |", "| Section | Status |").replace(
        "- | --- | --- |", "| --- | --- |"
    )
    start = normalized.index("| Section | Status |")
    instruction = InstructionInput(
        anchor_start=start,
        anchor_end=start + len("| Section | Status |"),
        quoted_text="| Section | Status |",
        instruction="add a Ref column",
    )
    published: list[str] = []
    result = _apply(
        [instruction],
        slice_mock=AsyncMock(return_value="## Procurement posture\n\nRewritten body here.\n"),
        publish_mock=_publisher(published),
        draft=_draft(raw),
    )

    assert result.applied_count == 1
    assert "- |" not in published[0]


def test_changed_block_ranges_ignores_unmodified_blocks() -> None:
    original = "Alpha.\n\nBravo.\n\nCharlie.\n"
    revised = "Alpha.\n\nBravo revised.\n\nCharlie.\n"
    ranges = changed_block_ranges(original, revised, offset=100)

    assert ranges == [{"start": 108, "end": 123}]
    assert revised[8:23] == "Bravo revised.\n"


def test_changed_block_ranges_treats_a_fenced_block_as_one_unit() -> None:
    fence = "```text\nline one\n\nline two\n```"
    original = f"Alpha.\n\n{fence}\n\nCharlie.\n"
    revised = f"Alpha.\n\n{fence}\n\nCharlie revised.\n"
    ranges = changed_block_ranges(original, revised, offset=0)

    assert len(ranges) == 1
    assert revised[ranges[0]["start"] : ranges[0]["end"]].strip() == "Charlie revised."
