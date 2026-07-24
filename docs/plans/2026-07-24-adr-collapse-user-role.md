# ADR — Collapse `user_role` to a Single Pinned Role

**Status:** Accepted · Implemented 2026-07-24
**Supersedes:** the four-way "Your role" overlay (`owner-builder`, `architect-pm`, `builder`, `d-and-c`)
**Implements:** `docs/plans/2026-07-23-user-role-collapse` (Phases 1–5, 7; Phase 6 deferred)

## Context

"Your role" was a required four-way choice that blocked three workflows (Project Plan,
Cost Plan, Consultant Procurement) until set, and it changed which document the product
generated. It added setup friction for no user-visible benefit: Cost Plan only ever
supported `architect-pm` (the other three were hard-rejected), and `architect-pm` was
already the frontend create default with the deepest section-brief coverage.

## Decision

Remove role as a user-facing concept. Every project is pinned server-side to a single
role and the value is never read for behaviour.

| # | Decision |
|---|---|
| **D1** | Collapse target is **`architect-pm`** — the only role Cost Plan supported, the create default, and the deepest-covered overlay. |
| **D2** | **Do not drop** the `projects.user_role` DB column. It is left nullable and unread; a cleanup migration can follow a release cycle later. |
| **D3** | Role is **not a request field**. The API stops accepting `user_role` on create/patch. The column is written once server-side with `DEFAULT_USER_ROLE = "architect-pm"` (single source of truth in `backend/app/sitewise/gate.py`) and never read for behaviour. |
| **D4** | The three non-architect role seeds (`role-owner-builder.md`, `role-builder.md`, `role-d-and-c.md`) are **retired from the knowledge catalog but kept on disk** with a retirement note. `role-architect-pm.md` is the sole role overlay the catalog resolves. |
| **D5** | Keep the "what kind of project" overlays (`building_class`, `work_type`, `state`, subclasses) — they carry real capability meaning (Cost Plan is NSW-residential-only; Tender Comparison is Class 1a NSW/VIC/QLD-only). The gate is now a **two-overlay** gate (taxonomy + state). |
| **D6** | Phases shipped independently, each CI-green. Phase 6 (merging the four role overlays into a single evidence-conditional `role-project-lead.md`) was **deferred** — it is a statutory-content rewrite requiring construction-domain sign-off, not a refactor. |

## Open questions — answers recorded

- **Q1 (production rows with a non-architect role):** handled by the project owner outside this change. The code is safe either way — new rows are written with the constant, and any client-supplied `user_role` on create is ignored rather than erroring. A backfill (`UPDATE projects SET user_role='architect-pm' WHERE user_role IS DISTINCT FROM 'architect-pm'`) is available if prod holds non-architect rows.
- **Q2 (merge the four role overlays — Phase 6):** **No.** Output is unchanged from the historical architect-PM path. The product is therefore quietly architect-PM-shaped; revisiting this is the deferred Phase 6.
- **Q3 (downstream readers of `user_role`):** protected by D2 (the column stays).

## Consequences

- No role selector in the UI; no workflow is ever blocked or `needs_input` because of role.
- `overlay_status()`, the workflow-capability checks, the PMP/Cost-Plan sources, renderers, greenfield briefs, knowledge catalog, agent turn context, and MCP snapshot payloads no longer take or emit `user_role`.
- Generated Project Plan / Cost Plan output is the single architect-PM shape regardless of any historical role value.
- `projects.user_role` remains a constant column (`architect-pm`). A future migration to drop it is logged as a deferred follow-up.

## Deploy note

Backend (Phase 1) and frontend (Phase 2) must deploy **together or backend-first**.
`ProjectProfilePatch` keeps `extra="forbid"`, so an old frontend that still sends
`user_role` on a profile PATCH against a new backend would 422 until it reloads —
deploying both together closes that window.
