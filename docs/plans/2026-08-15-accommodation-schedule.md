# Accommodation Schedule Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an Accommodation Schedule section to the PMP — a revisioned, agent-writable table of spaces with editable text areas and a derived Scheduled area total.

**Architecture:** Same pattern as FFE Schedule. Rows are shared project objects (`kind=accommodation_space`). A ~60-line data module lists, filters, sorts and totals them. The PMP renderer emits one markdown table. REST and MCP already take `kind` as a parameter. The generic markdown table editor needs no frontend work. A new `accommodation_dirty` category refreshes this section only.

**Tech Stack:** Python 3.12, FastAPI, existing `project_knowledge` / PMP renderer / emphasis-profiles taxonomy. No new dependencies.

---

## Locked decisions

| Topic | Choice |
| --- | --- |
| Placement | Insert `accommodation-schedule` immediately before `ffe-schedule`. Actual order: Brief → Consultants → Accommodation → FFE. Do not move Consultants. |
| Columns | `Space \| Level \| Area \| Characteristics \| Status` |
| Removed columns | No `dimensions`. No `notes`. Both live in Characteristics when known. |
| Area storage | Text. Users type `24`, `24 m²`, `approx 24`, `24–28`, `TBC`. |
| Totals | `parse_area_m2` (first number wins). Renderer footer **Scheduled area**. Not GFA/NLA. Do not reconcile to profile `gfa_sqm`. |
| Total exclusions | Soft-deleted `removed` rows, `Demolished` rows, and a row whose space is `total` / `scheduled area`. |
| Soft-delete | `status: removed` (casefold). Distinct from `Demolished`. |
| Sort | Canonical level order, then space name, then id. |
| Seeding | No typical-room invention. Chat or user only. |
| Applicability | `work_type_any: ["new", "extend", "refurb"]`. Advisory only via real scopes: `massing_study`, `highest_best_use`, `development_feasibility`, `design_audit`. Remediation excluded. |
| Dirty | New `accommodation_dirty`. Not `scope_dirty`, `design_dirty`, or `cost_dirty`. |
| Frontend | None. Generic `InlineTableRowEditor` is enough. |
| Out of scope | Profile field, drawing extraction, cost linkage, custom grid, NLA/GFA. |

Current `emphasis-profiles.json` section order is already `consultants` then `ffe-schedule`. Inserting before FFE produces the intended reading order without reordering issued PMPs.

---

## Data shape

Stored as shared objects, `kind="accommodation_space"`:

| Field | Type | Notes |
| --- | --- | --- |
| `space` | text | Identity column. Number repeats (`Bedroom 1`). |
| `level` | text | Free text. `Ground`, `First`, `Basement`, `External`, `Site`, `Roof` are all valid. |
| `area` | text | Loose. Parsed only for the footer. |
| `characteristics` | text | Catch-all: dimensions, aspect, existing-to-remain, uncertainty. `TBC` when empty. |
| `status` | text | `Existing` / `New` / `Retained` / `Demolished` / `TBC`. `removed` means delete from the schedule. |

---

## Task 1: Register the object kind

**Files:**
- Modify: `backend/app/projects/project_knowledge.py`
- Modify: `backend/app/mcp_bridge/server.py`
- Test: `backend/tests/mcp_bridge/test_dependency_offer_tools.py`

**Step 1: Write the failing test**

In `backend/tests/mcp_bridge/test_dependency_offer_tools.py`, add next to `test_upsert_shared_project_knowledge_writes_ffe_item`:

```python
def test_upsert_shared_project_knowledge_writes_accommodation_space(monkeypatch) -> None:
    project = _project()
    session = _Session(project)
    server, _access, mutation = _install(monkeypatch, session)

    result = _call(
        server,
        "upsert_shared_project_knowledge",
        {
            "project_id": str(PROJECT_ID),
            "kind": "accommodation_space",
            "object_id": "kitchen",
            "expected_revision": 0,
            "value": {
                "space": "Kitchen",
                "level": "Ground",
                "area": "18 m²",
                "characteristics": "north-facing",
                "status": "New",
            },
        },
    )

    assert result["id"] == "kitchen"
    assert result["kind"] == "accommodation_space"
    assert result["revision"] == 1
    assert result["value"]["space"] == "Kitchen"
    mutation.assert_called()
    listed = list_shared_project_objects(project, kind="accommodation_space")
    assert [item.id for item in listed] == ["kitchen"]
```

**Step 2: Run test to verify it fails**

```bash
cd backend
uv run pytest tests/mcp_bridge/test_dependency_offer_tools.py::test_upsert_shared_project_knowledge_writes_accommodation_space -v
```

Expected: FAIL — `invalid shared object kind` or a `Literal` validation error.

**Step 3: Register the kind**

`backend/app/projects/project_knowledge.py` — add `"accommodation_space"` to `ProjectObjectKind` (after `"ffe_item"`). Add to `_DIRTY_BY_KIND`:

```python
    "accommodation_space": ("accommodation_dirty",),
```

This will not type-check until Task 2 adds `accommodation_dirty` to `DirtyCategory`. If the suite is run at this point, keep the `_DIRTY_BY_KIND` value as `("scope_dirty",)` temporarily **or** do Task 1 and Task 2 in one sitting (preferred). This plan assumes Task 2 follows immediately in the same session.

`backend/app/mcp_bridge/server.py`:

- Add `"accommodation_space"` to `_SHARED_OBJECT_KINDS` (around line 1192).
- Extend the `upsert_shared_project_knowledge` docstring after the FFE sentence:

```text
    For Accommodation Schedule rows use kind=accommodation_space with a stable
    slug object_id and a value dict (space, level, area, characteristics,
    status). Missing fields may be "TBC". status "removed" deletes the row
    from the schedule; use "Demolished" when the space is coming out of the
    building. Put dimensions and other notes in characteristics — there is
    no dimensions or notes column.
```

That docstring is the agent's field-name contract. It is load-bearing.

**Step 4: Run the new test**

```bash
cd backend
uv run pytest tests/mcp_bridge/test_dependency_offer_tools.py::test_upsert_shared_project_knowledge_writes_accommodation_space -v
```

Expected: PASS once Task 2 has added `accommodation_dirty`. If you stop after Task 1 only, `_DIRTY_BY_KIND` will fail to type-check — continue to Task 2 before committing.

**Step 5: Commit** (after Task 2, or with Task 2)

```bash
git add backend/app/projects/project_knowledge.py backend/app/mcp_bridge/server.py backend/tests/mcp_bridge/test_dependency_offer_tools.py
```

Do not commit yet if `accommodation_dirty` is still missing. Commit with Task 2.

---

## Task 2: `accommodation_dirty` wiring

FFE has a dedicated dirty category so a row edit refreshes the FFE section and not Brief/risks/RFPs. Mirror that.

**Files:**
- Modify: `backend/app/projects/dependencies.py`
- Modify: `backend/app/projects/project_knowledge.py` (`_DIRTY_BY_KIND` if not done)
- Test: `backend/tests/projects/test_block_dirty_marking.py`
- Test: `backend/tests/projects/test_dependency_offers.py`

**Step 1: Write the failing tests**

`backend/tests/projects/test_block_dirty_marking.py`:

```python
def test_accommodation_schedule_section_marks_accommodation_dirty() -> None:
    assert dirty_categories_for_block_sections(["accommodation-schedule"]) == (
        "accommodation_dirty",
    )


def test_scope_section_does_not_mark_accommodation_dirty() -> None:
    assert "accommodation_dirty" not in dirty_categories_for_block_sections(
        ["scope-client-requirements"]
    )
```

`backend/tests/projects/test_dependency_offers.py` — add next to `test_ffe_change_identifies_only_package_dependants`:

```python
def test_accommodation_change_identifies_only_the_schedule_section() -> None:
    affected = resolve_concrete_affected(
        ["accommodation_dirty"],
        source_kind="accommodation_space",
        object_id="kitchen",
        previous_value={"space": "Kitchen", "level": "Ground", "area": "16"},
        new_value={"space": "Kitchen", "level": "Ground", "area": "18"},
        pmp_blocks=(
            {
                "id": "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "section_id": "accommodation-schedule",
                "content": "| Kitchen | Ground | 16 m² | TBC | New |",
            },
            {
                "id": "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "section_id": "scope-client-requirements",
                "content": "Brief prose",
            },
            {
                "id": "blk_cccccccccccccccccccccccccccccccc",
                "section_id": "ffe-schedule",
                "content": "| Basin | Ensuite | 1 | TBC | Selected | — |",
            },
        ),
    )

    by_type = {item.artefact_type: item for item in affected}
    assert set(by_type) == {"pmp"}
    assert by_type["pmp"].selector.section_ids == ("accommodation-schedule",)
    assert by_type["pmp"].selector.block_ids == (
        "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    assert "cost_plan" not in by_type
    assert "rft" not in by_type
```

**Step 2: Run tests to verify they fail**

```bash
cd backend
uv run pytest tests/projects/test_block_dirty_marking.py tests/projects/test_dependency_offers.py::test_accommodation_change_identifies_only_the_schedule_section -v
```

Expected: FAIL — `accommodation_dirty` is not a valid `DirtyCategory`.

**Step 3: Wire the category**

In `backend/app/projects/dependencies.py`:

1. Add `"accommodation_dirty"` to `DirtyCategory` (after `"ffe_dirty"`).

2. `_SECTION_BY_DIRTY_BLOCK` — after the FFE entries:

```python
    "accommodation": "accommodation-schedule",
    "accommodation-schedule": "accommodation-schedule",
```

3. `_DIRTY_TEMPLATES` — after `ffe_dirty`:

```python
    "accommodation_dirty": (
        _Template("pmp", "project", ("accommodation",)),
    ),
```

PMP only. No RFT, no cost plan.

4. `dirty_categories_for_block_sections` mapping — after `"ffe-schedule"`:

```python
        "accommodation-schedule": ("accommodation_dirty",),
```

5. `_matching_pmp_block_ids` — treat accommodation like FFE:

```python
    if "ffe" in blocks or "ffe-schedule" in blocks:
        wanted_sections.add("ffe-schedule")
    if "accommodation" in blocks or "accommodation-schedule" in blocks:
        wanted_sections.add("accommodation-schedule")
```

and extend the `not old_name` branch:

```python
        elif not old_name and (
            section_id in {"ffe-schedule", "accommodation-schedule", "consultants"}
            or "ffe" in content.lower()
        ):
```

6. `_name_from` — add `"space"` to the key list so a renamed room can carry a reference patch:

```python
    for key in ("name", "firm", "label", "title", "space"):
```

7. Confirm `_DIRTY_BY_KIND["accommodation_space"] = ("accommodation_dirty",)` in `project_knowledge.py`.

**Step 4: Run tests**

```bash
cd backend
uv run pytest tests/projects/test_block_dirty_marking.py tests/projects/test_dependency_offers.py::test_accommodation_change_identifies_only_the_schedule_section tests/mcp_bridge/test_dependency_offer_tools.py::test_upsert_shared_project_knowledge_writes_accommodation_space -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/projects/project_knowledge.py backend/app/projects/dependencies.py backend/app/mcp_bridge/server.py backend/tests/mcp_bridge/test_dependency_offer_tools.py backend/tests/projects/test_block_dirty_marking.py backend/tests/projects/test_dependency_offers.py
git commit -m "feat: register accommodation_space and accommodation_dirty"
```

---

## Task 3: Data layer

**Files:**
- Create: `backend/app/sitewise/accommodation_schedule.py`
- Test: `backend/tests/sitewise/test_accommodation_schedule.py`

Model on `backend/app/sitewise/ffe_schedule.py` (46 lines). Read it first.

**Step 1: Write the failing tests**

Create `backend/tests/sitewise/test_accommodation_schedule.py`:

```python
"""Accommodation Schedule shared-knowledge helpers."""

from __future__ import annotations

import uuid

from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.sitewise.accommodation_schedule import (
    accommodation_schedule_rows,
    parse_area_m2,
    scheduled_area_total,
)


def _project() -> Project:
    return Project(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        owner_user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        slug="harbour-house",
        title="Harbour House",
        workspace_path="04-projects/harbour-house",
        phase="brief-planning",
        building_class="residential",
        work_type="new",
        state="NSW",
        project_metadata={"taxonomy": {"subclasses": ["house"]}},
    )


def _add(project: Project, object_id: str, value: dict) -> None:
    upsert_shared_project_object(
        project,
        kind="accommodation_space",
        object_id=object_id,
        update=SharedProjectObjectUpdate(expected_revision=0, value=value),
        source="user",
    )


def test_parse_area_m2_reads_loose_text() -> None:
    assert parse_area_m2(24) == 24.0
    assert parse_area_m2("24") == 24.0
    assert parse_area_m2("24 m²") == 24.0
    assert parse_area_m2("approx 24") == 24.0
    assert parse_area_m2("24–28") == 24.0
    assert parse_area_m2("TBC") is None
    assert parse_area_m2("") is None
    assert parse_area_m2("pending survey") is None


def test_rows_skip_removed_and_sort_by_level() -> None:
    project = _project()
    _add(project, "courtyard", {
        "space": "Courtyard",
        "level": "External",
        "area": "40",
        "status": "New",
    })
    _add(project, "kitchen", {
        "space": "Kitchen",
        "level": "Ground",
        "area": "18 m²",
        "characteristics": "north-facing",
        "status": "New",
    })
    _add(project, "basement-store", {
        "space": "Store",
        "level": "Basement",
        "area": "8",
        "status": "Existing",
    })
    _add(project, "old-laundry", {
        "space": "Laundry",
        "level": "Ground",
        "status": "removed",
    })
    _add(project, "fake-total", {
        "space": "Scheduled area",
        "area": "999",
        "status": "TBC",
    })

    rows = accommodation_schedule_rows(project)
    assert [row["space"] for row in rows] == ["Store", "Kitchen", "Courtyard"]
    assert rows[1]["characteristics"] == "north-facing"
    assert rows[0]["characteristics"] == "TBC"


def test_scheduled_area_total_skips_demolished_and_unparseable() -> None:
    project = _project()
    _add(project, "kitchen", {"space": "Kitchen", "level": "Ground", "area": "18 m²", "status": "New"})
    _add(project, "deck", {"space": "Covered deck", "level": "External", "area": "approx 24", "status": "New"})
    _add(project, "old-bath", {"space": "Bathroom", "level": "Ground", "area": "6", "status": "Demolished"})
    _add(project, "study", {"space": "Study", "level": "First", "area": "TBC", "status": "New"})

    rows = accommodation_schedule_rows(project)
    assert scheduled_area_total(rows) == 42.0
```

**Step 2: Run tests to verify they fail**

```bash
cd backend
uv run pytest tests/sitewise/test_accommodation_schedule.py -v
```

Expected: FAIL — `ModuleNotFoundError: app.sitewise.accommodation_schedule`.

**Step 3: Implement the module**

Create `backend/app/sitewise/accommodation_schedule.py`:

```python
"""Deterministic Accommodation Schedule helpers from shared space facts."""

from __future__ import annotations

import re
from typing import Any

from app.database.project import Project
from app.projects.project_knowledge import list_shared_project_objects

_ACCOMMODATION_FIELDS = (
    "space",
    "level",
    "area",
    "characteristics",
    "status",
)

_TOTAL_LABELS = frozenset({"total", "scheduled area", "**scheduled area**"})

_LEVEL_ORDER = {
    "basement": 0,
    "lower ground": 1,
    "ground": 2,
    "ground floor": 2,
    "first": 3,
    "first floor": 3,
    "level 1": 3,
    "second": 4,
    "second floor": 4,
    "level 2": 4,
    "third": 5,
    "level 3": 5,
    "roof": 80,
    "external": 90,
    "site": 91,
}

_AREA_PATTERN = re.compile(r"(\d[\d,]*(?:\.\d+)?)")


def accommodation_schedule_rows(project: Project) -> list[dict[str, Any]]:
    """Return active accommodation rows for PMP rendering and agent edits."""
    rows: list[dict[str, Any]] = []
    for item in list_shared_project_objects(project, kind="accommodation_space"):
        value = item.value if isinstance(item.value, dict) else {}
        status = str(value.get("status") or "").strip()
        if status.casefold() == "removed":
            continue
        label = str(value.get("space") or item.id).strip()
        if not label or label.casefold() in _TOTAL_LABELS:
            continue
        row = {field: _cell(value.get(field)) for field in _ACCOMMODATION_FIELDS}
        row["space"] = label
        row["id"] = item.id
        row["revision"] = item.revision
        rows.append(row)
    rows.sort(
        key=lambda row: (
            _level_rank(row["level"]),
            row["level"].casefold(),
            row["space"].casefold(),
            row["id"],
        )
    )
    return rows


def parse_area_m2(raw: object) -> float | None:
    """Read a square-metre figure out of the loose text a PM actually types.

    Handles "24", "24 m²", "approx 24", "24–28". First number wins.
    Returns None rather than guessing when nothing parses.
    """
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) if raw > 0 else None
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or text.casefold() in {"tbc", "—", "-"}:
        return None
    match = _AREA_PATTERN.search(text.replace("m²", " ").replace("m2", " "))
    if match is None:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    return amount if amount > 0 else None


def scheduled_area_total(rows: list[dict[str, Any]]) -> float | None:
    """Sum parseable areas, excluding demolished spaces."""
    total = 0.0
    found = False
    for row in rows:
        if str(row.get("status") or "").casefold() == "demolished":
            continue
        amount = parse_area_m2(row.get("area"))
        if amount is None:
            continue
        total += amount
        found = True
    return total if found else None


def _level_rank(level: str) -> int:
    return _LEVEL_ORDER.get(level.strip().casefold(), 70)


def _cell(raw: object) -> str:
    text = str(raw or "").strip()
    return text or "TBC"
```

**Step 4: Run tests**

```bash
cd backend
uv run pytest tests/sitewise/test_accommodation_schedule.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/sitewise/accommodation_schedule.py backend/tests/sitewise/test_accommodation_schedule.py
git commit -m "feat: add accommodation schedule data layer with parsed area totals"
```

---

## Task 4: Renderer, heading, config, and existing-test updates

Do the renderer **and** the config in this task. Adding the section to `emphasis-profiles.json` before the renderer exists makes every qualifying PMP raise `RuntimeError("PMP scaffold missing required sections: …")`. Adding the heading to `PMP_SECTION_HEADINGS` without adding the section to the config breaks `test_section_contracts.py`. Flip both switches together.

**Files:**
- Modify: `backend/app/sitewise/pmp_renderer.py`
- Modify: `backend/app/sitewise/section_contracts.py`
- Modify: `backend/app/sitewise/pmp_greenfield_brief.py`
- Modify: `backend/app/sitewise/pmp_length.py`
- Modify: `data/taxonomy/emphasis-profiles.json`
- Modify: `backend/tests/sitewise/test_section_contracts.py`
- Modify: `backend/tests/sitewise/test_ffe_schedule.py`
- Modify: `backend/tests/test_project_taxonomy_api.py`
- Test: `backend/tests/sitewise/test_accommodation_schedule.py` (add render / applicability cases)

**Step 1: Write the failing render and applicability tests**

Append to `backend/tests/sitewise/test_accommodation_schedule.py`:

```python
from types import SimpleNamespace

from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.sitewise.taxonomy import applicable_sections
from app.workflows.create_pmp import markdown_section_headings


def test_applicable_for_new_absent_for_remediation() -> None:
    assert "accommodation-schedule" in applicable_sections(
        work_type="new", work_scope=[]
    )
    assert "accommodation-schedule" not in applicable_sections(
        work_type="remediation", work_scope=[]
    )
    assert "accommodation-schedule" not in applicable_sections(
        work_type="advisory", work_scope=["building_condition"]
    )
    assert "accommodation-schedule" in applicable_sections(
        work_type="advisory", work_scope=["massing_study"]
    )


def test_taxonomy_scaffold_renders_spaces_and_scheduled_area() -> None:
    project = _project()
    _add(project, "kitchen", {
        "space": "Kitchen",
        "level": "Ground",
        "area": "18 m²",
        "characteristics": "4.2 × 3.6 m, north-facing",
        "status": "New",
    })
    _add(project, "deck", {
        "space": "Covered deck",
        "level": "External",
        "area": "24",
        "status": "New",
    })

    markdown = render_pmp_scaffold(
        project, MobilisationEvidencePack(), "platform_seeded"
    )
    headings = markdown_section_headings(markdown)
    assert headings.index("Consultants") + 1 == headings.index(
        "Accommodation Schedule"
    )
    assert headings.index("Accommodation Schedule") + 1 == headings.index(
        "FFE Schedule"
    )
    assert "| Space | Level | Area | Characteristics | Status |" in markdown
    assert "| Kitchen | Ground | 18 m² | 4.2 × 3.6 m, north-facing | New |" in markdown
    assert "| **Scheduled area** |  | 42 m² |  |  |" in markdown


def test_remediation_project_omits_the_section() -> None:
    project = SimpleNamespace(
        slug="plant-swap",
        title="Plant swap",
        workspace_path="04-projects/plant-swap",
        phase="brief-planning",
        building_class="industrial",
        work_type="remediation",
        state="NSW",
        project_metadata={"taxonomy": {"subclasses": ["warehouse"]}},
    )
    markdown = render_pmp_scaffold(
        project, MobilisationEvidencePack(), "platform_seeded"
    )
    assert "Accommodation Schedule" not in markdown_section_headings(markdown)
```

**Step 2: Run tests to verify they fail**

```bash
cd backend
uv run pytest tests/sitewise/test_accommodation_schedule.py -v
```

Expected: FAIL — section not in `applicable_sections` / heading missing.

**Step 3: Renderer**

In `backend/app/sitewise/pmp_renderer.py`, add next to `_render_taxonomy_ffe_schedule` (around line 1517):

```python
def _render_taxonomy_accommodation_schedule(project: Project) -> str:
    from app.sitewise.accommodation_schedule import (
        accommodation_schedule_rows,
        scheduled_area_total,
    )

    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    rows = accommodation_schedule_rows(project)
    table = [
        "| Space | Level | Area | Characteristics | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    if rows:
        for row in rows:
            table.append(
                "| {space} | {level} | {area} | {characteristics} | {status} |".format(
                    space=row["space"],
                    level=row["level"],
                    area=row["area"],
                    characteristics=row["characteristics"],
                    status=row["status"],
                )
            )
        total = scheduled_area_total(rows)
        total_cell = f"{total:g} m²" if total is not None else "TBC"
        table.append(f"| **Scheduled area** |  | {total_cell} |  |  |")
    else:
        table.append(
            "| — | — | TBC | TBC | To be confirmed |"
        )
    return "\n".join(
        [
            f"## {heading_for_section_id('accommodation-schedule', work_type=context.work_type)}",
            "",
            "Rooms, zones and outdoor spaces the project covers. Area is "
            "scheduled area, not GFA or NLA. Add or tidy rows in chat. "
            "Missing fields stay TBC.",
            _emphasis_note(project, "accommodation-schedule"),
            "",
            "\n".join(table),
        ]
    )
```

Register it in the `renderers` dict (around line 1975), **immediately before** `"ffe-schedule"`:

```python
        "accommodation-schedule": lambda: _render_taxonomy_accommodation_schedule(project),
        "ffe-schedule": lambda: _render_taxonomy_ffe_schedule(project),
```

Never hardcode the heading string. `section_id_for_heading` must round-trip.

**Step 4: Heading and length register**

`backend/app/sitewise/section_contracts.py` — insert after `"consultants"`:

```python
    "accommodation-schedule": "Accommodation Schedule",
```

`backend/app/sitewise/pmp_length.py` — add to `_REGISTER_SECTIONS` so length condensation does not crush the table:

```python
_REGISTER_SECTIONS = frozenset(
    {"snapshot", "accommodation-schedule", "ffe-schedule", "citation-key"}
)
```

`backend/app/sitewise/pmp_greenfield_brief.py` — add a focus line before the FFE branch, and retarget FFE from "after Consultants" to "after the Accommodation Schedule (or after Consultants when that section is absent)":

```python
    if section_id == "accommodation-schedule":
        return (
            "cover the Accommodation Schedule after Consultants: one table of "
            "spaces (rooms, zones, outdoor areas, plant rooms, loading docks, "
            "circulation cores) with level, area, characteristics and status; "
            "preserve user-added shared accommodation_space rows; put dimensions "
            "in characteristics; keep unspecified fields as TBC; do not invent "
            "rooms the user did not describe; do not bury the schedule inside "
            "the Brief prose"
        )
    if section_id == "ffe-schedule":
        return (
            "cover the unified Finishes, Fixtures and Equipment schedule after "
            "the Accommodation Schedule (or after Consultants when that section "
            "is absent): one table for interior and exterior finishes, fixtures, and "
            ...
        )
```

**Step 5: Config**

`data/taxonomy/emphasis-profiles.json`:

1. Insert `"accommodation-schedule"` into `sections` immediately before `"ffe-schedule"`:

```json
  "sections": [
    "snapshot",
    "scope-client-requirements",
    "consultants",
    "accommodation-schedule",
    "ffe-schedule",
    "compliance-approvals",
    "programme",
    "cost-budget",
    "procurement-delivery",
    "risks",
    "actions-decisions",
    "citation-key"
  ],
```

2. Add `"accommodation-schedule"` to **all 20** `base_weights` entries including `default`. A missing key silently becomes `0.0` via `raw_weights.get(section, 0.0)`. Suggested values:

- `0.04` on keys whose work type is `new`, `extend`, or `refurb`
- `0.01` on `remediation`, `advisory`, and `default`

Existing values do not need hand-balancing; `_normalise_weights` rescales to 1.0.

3. Add applicability. **Every `work_scope` value must exist in `data/taxonomy/work-scopes.json`.** The draft list in the original brief (`fitout`, `internal_fitout`, `landscape`, `extension`, `additional_storey`, `external_works` as an item) does **not**. Use only real item values. `work_type_any` already covers new/extend/refurb, so `work_scope_any` is only for advisory:

```json
    "accommodation-schedule": {
      "include_when": {
        "work_type_any": ["new", "extend", "refurb"],
        "work_scope_any": [
          "massing_study",
          "highest_best_use",
          "development_feasibility",
          "design_audit"
        ]
      }
    },
```

Place it next to the existing `ffe-schedule` applicability block. Semantics in `_applicability_matches`: any listed trigger firing is enough (`work_type_any` OR `work_scope_any`).

**Step 6: Update tests that hardcode the section list**

These will fail as soon as the heading and `sections` array change. Update them in this same commit.

`backend/tests/sitewise/test_section_contracts.py` — expected universal skeleton becomes:

```python
    expected = (
        "Project Summary",
        "Brief",
        "Consultants",
        "Accommodation Schedule",
        "FFE Schedule",
        "Planning and Compliance",
        "Programme",
        "Cost Planning",
        "Procurement and Delivery",
        "Risks and mitigations",
        "Actions and decisions",
        "Citation key",
    )
```

In `test_advisory_drops_procurement_and_delivery`, assert the section is absent for a condition-assessment advisory:

```python
    assert "Accommodation Schedule" not in headings
```

`backend/tests/test_project_taxonomy_api.py` — insert `"accommodation-schedule"` before `"ffe-schedule"` in the expected `emphasis_profiles.sections` list (around line 525).

`backend/tests/sitewise/test_ffe_schedule.py` — `test_taxonomy_scaffold_renders_shared_ffe_rows_after_brief` currently asserts Consultants is immediately followed by FFE. Change to:

```python
    assert headings.index("Accommodation Schedule") + 1 == headings.index(
        "FFE Schedule"
    )
```

**Step 7: Run tests**

```bash
cd backend
uv run pytest tests/sitewise/test_accommodation_schedule.py tests/sitewise/test_section_contracts.py tests/sitewise/test_ffe_schedule.py tests/sitewise/test_taxonomy.py::test_emphasis_weights_normalised_for_every_combo tests/test_project_taxonomy_api.py::test_taxonomy_endpoint_returns_frontend_option_shape -v
```

Expected: PASS. `test_emphasis_weights_normalised_for_every_combo` will fail if any of the 20 weight objects is missing the new key (the key will be `0.0` and the set-equality still passes, but add the key anyway so the section is weighted).

Then a broader check:

```bash
cd backend
uv run pytest tests/sitewise tests/projects/test_block_dirty_marking.py tests/projects/test_dependency_offers.py -q
```

**Step 8: Commit**

```bash
git add backend/app/sitewise/pmp_renderer.py backend/app/sitewise/section_contracts.py backend/app/sitewise/pmp_greenfield_brief.py backend/app/sitewise/pmp_length.py data/taxonomy/emphasis-profiles.json backend/tests/sitewise/test_accommodation_schedule.py backend/tests/sitewise/test_section_contracts.py backend/tests/sitewise/test_ffe_schedule.py backend/tests/test_project_taxonomy_api.py
git commit -m "feat: render Accommodation Schedule before FFE with scheduled-area total"
```

---

## Task 5: Agent instructions

Learn from commit `4480c68`: the asset-register instruction was written around mechanical plant, was read literally, and a facade and a basement slab went unrecorded. Write this instruction with explicit breadth from the first draft.

**Files:**
- Modify: `backend/app/agent/turn_context.py`
- Modify: `backend/app/agent/workspace_instructions.py`
- Test: `backend/tests/agent/test_turn_context.py`
- Test: `backend/tests/agent/test_workspace_instructions.py`

**Step 1: Write the failing tests**

`backend/tests/agent/test_turn_context.py` — next to the FFE assertion around line 519, add a dedicated test (or extend that one):

```python
def test_prompt_teaches_accommodation_schedule_breadth() -> None:
    prompt = build_agent_prompt(
        "New kitchen, two bedrooms and a covered deck",
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype=None,
        state="NSW",
        phase="brief-planning",
        building_class="residential",
        work_type="new",
        history=[],
    )
    assert "accommodation_space" in prompt
    assert "courtyard" in prompt
    assert "loading dock" in prompt
    assert "circulation core" in prompt
    assert "Demolished" in prompt
    assert "characteristics" in prompt
```

`backend/tests/agent/test_workspace_instructions.py` — add:

```python
    assert "accommodation_space" in WORKSPACE_AGENTS_MD
    assert "Accommodation Schedule" in WORKSPACE_AGENTS_MD
```

**Step 2: Run tests to verify they fail**

```bash
cd backend
uv run pytest tests/agent/test_turn_context.py::test_prompt_teaches_accommodation_schedule_breadth tests/agent/test_workspace_instructions.py::test_writes_agents_md_into_workspace -v
```

Expected: FAIL — `accommodation_space` not in prompt / `WORKSPACE_AGENTS_MD`.

**Step 3: Write the instruction**

In `backend/app/agent/turn_context.py`:

1. `_DOCUMENT_ACCESS_GUIDANCE` — after the FFE paragraph (around line 48), add a sibling paragraph. Also retarget the FFE sentence that says the table is "after Consultants":

```text
For Accommodation Schedule adds or edits (rooms, zones and outdoor spaces
in the PMP section after Consultants), call list_shared_project_knowledge
with kind accommodation_space, then upsert_shared_project_knowledge with a
stable object id slug and fields space, level, area, characteristics, status
(use TBC when unspecified). A courtyard, a landscape zone, a covered deck,
a plant room, a loading dock and a circulation core are all spaces with a
level, an area and a status — not only bedrooms and kitchens. Number
repeated rooms (Bedroom 1, Bedroom 2). Put dimensions and other notes in
characteristics; there is no dimensions or notes column. status "removed"
deletes the row from the schedule; use "Demolished" when the space is
coming out of the building. If a create_pmp artefact exists, also call
get_artefact_blocks and apply_artefact_operations to ADD or UPDATE the
matching row in the Accommodation Schedule section. Do not invent rooms
the user did not describe.
```

Change the FFE line "after Consultants" to "after the Accommodation Schedule (or after Consultants when that section is absent)".

2. `_ROLE_GUIDANCE` — after the FFE bullet (around line 162), add:

```text
- For Accommodation Schedule changes, upsert_shared_project_knowledge with
  kind accommodation_space, then optionally patch the PMP Accommodation
  Schedule section (after Consultants) via get_artefact_blocks and
  apply_artefact_operations when a create_pmp artefact exists. Record every
  space the user names, including outdoor and service spaces.
```

3. Near the asset-register guidance (around lines 271–290), add a short capture rule so a prose brief that names spaces lodges them without being asked, the same way assets are recorded on an opening description:

```text
- When the user describes spaces the project covers — rooms, outdoor areas,
  landscape zones, plant rooms, loading docks, circulation cores — lodge
  them with upsert_shared_project_knowledge kind=accommodation_space. Do
  this on the opening description without being asked. Do not skip a
  courtyard, a covered deck, or a loading dock because they are not rooms.
```

In `backend/app/agent/workspace_instructions.py`, add a matching FFE-style paragraph for `accommodation_space`, and retarget the FFE "after Consultants" wording the same way.

**Step 4: Run tests**

```bash
cd backend
uv run pytest tests/agent/test_turn_context.py::test_prompt_teaches_accommodation_schedule_breadth tests/agent/test_workspace_instructions.py -v
```

Expected: PASS.

This is the one task unit tests cannot fully prove. After the suite is green, a live chat turn against a brief that names several spaces including an external one is the real check. Record the prompt and the resulting rows in the commit message, as `4480c68` did.

**Step 5: Commit**

```bash
git add backend/app/agent/turn_context.py backend/app/agent/workspace_instructions.py backend/tests/agent/test_turn_context.py backend/tests/agent/test_workspace_instructions.py
git commit -m "feat: teach the agent to capture accommodation spaces with explicit breadth"
```

---

## Verification gate

After all five tasks:

```bash
cd backend
uv run pytest tests/sitewise/test_accommodation_schedule.py tests/sitewise/test_section_contracts.py tests/sitewise/test_ffe_schedule.py tests/sitewise/test_taxonomy.py tests/projects/test_block_dirty_marking.py tests/projects/test_dependency_offers.py tests/mcp_bridge/test_dependency_offer_tools.py tests/agent/test_turn_context.py tests/agent/test_workspace_instructions.py tests/test_project_taxonomy_api.py::test_taxonomy_endpoint_returns_frontend_option_shape -q
```

Expected: PASS.

Manual check (optional, Task 5):

1. Open a `residential|new` project.
2. In chat: "knock-down rebuild, new kitchen, two bedrooms, a covered deck and a courtyard."
3. Confirm four `accommodation_space` rows land with sensible levels.
4. Confirm the PMP shows Accommodation Schedule between Consultants and FFE, with a Scheduled area footer.
5. Open an `industrial|remediation` plant upgrade. Confirm the section is absent and scaffold does not raise.

---

## Deliberately excluded

- Profile field for the room list
- Numeric `area` column or a `CostPlanGrid`-style editor
- GFA / NLA / measurement-standard reconciliation
- Drawing extraction
- Cost linkage / `cost_dirty`
- Typical-room seeding
- Frontend changes
- Reordering Consultants ahead of the schedules (already the current order)

---

## Implementation notes

- One commit per task. Do not add the section to `emphasis-profiles.json` `sections` or `applicability` before the renderer and `PMP_SECTION_HEADINGS` entry exist.
- Verify every applicability `work_scope` against `data/taxonomy/work-scopes.json`. A typo fails silently: the section never appears.
- `status: removed` is soft-delete. `Demolished` is a visible row excluded from the total.
- The Scheduled area footer is a rendered row. `accommodation_schedule_rows` must ignore a space named `total` / `scheduled area` so a user edit cannot persist a fake object.
- Do not mark `design_dirty` or `cost_dirty`.
- No new MCP tools. No frontend files.
