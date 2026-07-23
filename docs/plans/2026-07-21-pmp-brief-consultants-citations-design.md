# PMP structure: Brief / Consultants split and numbered citations

**Date:** 2026-07-21  
**Status:** Design validated  
**Applies to:** Taxonomy-backed Create/Update PMP output (adaptive 2–4 page scaffold + narrative)

## Goal

Make the Project Management Plan read as a control document first: summary → physical brief → consultant appointments → delivery sections. Push provenance to numbered document citations and a single end-matter key. Stop mixing building scope with consultant briefs in one section.

## Decisions

| Topic | Choice |
| --- | --- |
| Citation grain | One stable number per active project evidence document |
| Snapshot status | Keep evidence-status wording in the middle column; third column is citation only |
| Consultants layout | Appointment register table |
| End matter | Single section titled **Citation key** (replaces front-loaded Evidence basis) |
| Section titles | User-specified names below |

## Section order

1. **Project Summary** (was Project snapshot)
2. **Brief** (was Scope and client requirements — physical / client brief only)
3. **Consultants** (new)
4. **Planning and Compliance** (was Compliance and approvals)
5. **Programme** (was Programme and milestones)
6. **Cost Planning** (was Cost and budget)
7. **Procurement and Delivery**
8. **Risks and mitigations**
9. **Actions and decisions**
10. **Citation key** (moved from front; was Evidence basis and document control)

## Project Summary

Table columns:

| Field | Current PMP position | Citation |

- Middle cell: value plus status label (e.g. `Walsh House renovation — Grounded`).
- Citation cell: `[n]` only, or `—` when user-provided / not evidenced / assumption with no document.
- No full document titles or prose in the citation column.

## Brief

Owns only the physical and client brief:

- Inclusions, exclusions, interfaces
- Finishes / fixtures / owner selections where relevant
- Acceptance criteria and brief-lock status

Does **not** include expected-consultant rosters or engagement/fee content. Those move to Consultants.

## Consultants

Appointment register:

| Discipline | Firm | Scope / services | Fee | Status | Citation |

Rules:

- Architect-PM engagement brief is the first row when that role applies (scope, fee, appointment status, citation to engagement letter / fee proposal).
- Taxonomy-expected disciplines without appointment evidence appear as Assumption / Not evidenced rows with `—` citation.
- Ground fee and scope from engagement letters and fee proposals via `[n]`; silent cells stay TBC / Assumption.
- Status values stay in the existing vocabulary (`Grounded`, `Partial`, `Assumption`, `Not evidenced`, `User provided`, etc.).

## Citations

- Each active project evidence document gets one number for the whole PMP (`[1]`, `[2]`, …).
- Numbering is deterministic (stable order by document register / path).
- Inline body refs, Summary citation column, Consultants citation column, and Citation key all share the same numbers.
- Do not invent citations for user-provided or assumption-only facts.

## Citation key (end matter)

Single closing section containing, in order:

1. Numbered document list: `[n] filename — date/status` (short; no pasted source prose)
2. Section evidence-status table: `Section | Evidence status | Citation` using `[n]` / `—`
3. Short document-control note (draft/version, supersede rule)

Body sections must not open with Evidence basis and document control.

## Implementation touchpoints (when built)

Likely files (not exhaustive):

- `backend/app/sitewise/section_contracts.py` — headings and section ids
- `data/taxonomy/emphasis-profiles.json` — insert `consultants` after brief; rename section ids/labels as needed
- `data/taxonomy/pmp-section-seed-map.json` — seed routing for Brief vs Consultants
- `backend/app/sitewise/pmp_renderer.py` — Summary columns, Brief without consultant roster, new Consultants table, Citation key at end
- `backend/app/workflows/create_pmp_instructions.md` (+ update path) — instruct model on new structure and `[n]` citations
- Evidence map / validation helpers and related tests under `backend/tests/sitewise/` and `backend/tests/workflows/`

Word-budget weights: move consultant-roster weight out of Brief into Consultants; keep primary PMP within the existing 2–4 page band.

## Out of scope

- Changing legacy non-taxonomy role section contracts beyond what taxonomy PMP generation already superseded
- Claim/passage-level citation numbering
- Redesigning companion annexures beyond what the primary PMP needs for the split
