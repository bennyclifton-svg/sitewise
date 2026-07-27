# Ingest Profile Identity Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** After document ingest, auto-fill empty `client` / `site_address` when confidence is high; otherwise open a quiet cockpit Accept/Reject proposal.

**Architecture:** Deterministic extract + confidence on ingest completion → `propose_project_profile_change` → optional immediate `accept_profile_proposal` with `actor_source="ingest"`. Never overwrite set fields. Cockpit reads `open_profile_proposals` from snapshot; HTTP accept/reject for UI buttons. Agent prompts stop re-asking when ingest already acted.

**Tech Stack:** FastAPI, SQLAlchemy async, existing profile_proposals module, React ControlBoard, vitest/pytest.

**Design:** `docs/plans/2026-07-21-ingest-profile-identity-design.md`

**Worktree:** `D:\AI Projects\clerk\.worktrees\ingest-profile-identity` on `feature/ingest-profile-identity`

---

### Task 1: Port identity profile fields

**Files:**
- Modify: `backend/app/schemas/projects.py` — add `site_address` / `client` to patch, view, field literal
- Modify: `backend/app/projects/profile.py` — PROFILE_FIELDS, read_profile, _write_profile, `_optional_text`
- Create: `backend/app/projects/identity.py` (from design / main workspace)
- Create: `backend/tests/projects/test_identity.py`

**Steps:** Port fields; copy identity helpers; run `uv run pytest tests/projects/test_identity.py tests/projects/test_profile.py -q`

---

### Task 2: Confidence scoring

**Files:**
- Create: `backend/app/projects/identity_confidence.py`
- Create: `backend/tests/projects/test_identity_confidence.py`

**Behaviour:**
- Score address/client per design thresholds (≥0.85 auto, 0.5–0.85 propose, else skip)
- Ambiguous client: `for ` / `X for Y` patterns → 0.55
- Strong address patterns → 0.9
- Return per-field decisions: `{field, value, confidence, action}` where action is `auto_apply` | `propose` | `skip`

---

### Task 3: Bootstrap orchestration + ingest hook

**Files:**
- Create: `backend/app/projects/identity_bootstrap.py`
- Create: `backend/tests/projects/test_identity_bootstrap.py`
- Modify: `backend/app/inbox/service.py` — after `ingest_status == "ingested"` and `source_doc_id` resolved, call bootstrap in try/except (log only)

**Behaviour:**
- Read `SourceDocument.normalized_content`
- If both identity fields set → no-op
- Build proposed_values for empty fields only
- Conflict with pending different value → propose only (no auto)
- Matching pending → skip duplicate
- High confidence → propose then accept with `proposer`/`actor_source` `"ingest"`

---

### Task 4: HTTP accept/reject + frontend API

**Files:**
- Modify: projects API router (find under `backend/app/api/`) — POST accept/reject
- Modify: `frontend/src/lib/api.ts` — helpers
- Extend: `frontend/src/lib/types/project.ts` — `open_profile_proposals` on snapshot types as needed

---

### Task 5: Cockpit UI + agent prompts

**Files:**
- Create: `frontend/src/components/project/ProfileProposalStrip.tsx` (+ test)
- Modify: `ProjectControlBoard.tsx` / `ProjectCockpitPage.tsx`
- Modify: `backend/app/agent/turn_context.py`, `workspace_instructions.py`

**Behaviour:** Pending card with Accept/Reject; auto-applied notice optional via accepted ingest proposals or profile values + toast. Agent: don't re-ask if profile set or pending proposal exists.

---

### Task 6: Verify

Run focused backend + frontend tests; fix regressions.
