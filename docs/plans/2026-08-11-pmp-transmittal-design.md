# PMP Transmittal section and Save control placement

**Date:** 2026-08-11  
**Status:** Design validated  
**Applies to:** Taxonomy-backed Create/Update PMP scaffold, draft Transmittal load/save UI (PMP + RFP)

## Goal

Give the Project Management Plan the same curated document register as procurement RFPs: an empty Transmittal section before Citation key that the user can load, edit via the document repository, and save back into the active PMP. Put Save Transmittal next to Load Transmittal on the draft so the control clearly targets the middle-pane artefact. Keep Project Summary’s permanent budget row labelled **Budget**.

## Decisions

| Topic | Choice |
| --- | --- |
| Approach | Reuse RFP Transmittal path (shared heading/table + existing replace API) |
| Initial PMP Transmittal | Empty table (`0 documents`) |
| Save button location | Middle pane only, beside Load Transmittal |
| Repository Save | Remove |
| Backend API | No new endpoint; reuse `POST .../drafts/{draft_id}/transmittal` |
| Existing PMPs without Transmittal | Hidden Load/Save until create/update adds the section |
| Project Summary budget label | Permanent row labelled **Budget** (never Project Budget) |

## Section order (PMP)

1. Project Summary  
2. Brief  
3. FFE Schedule (when present)  
4. Consultants  
5. Planning and Compliance  
6. Programme  
7. Cost Planning  
8. Procurement and Delivery  
9. Risks and mitigations  
10. Actions and decisions  
11. **Transmittal** (new; empty on create/regenerate)  
12. **Citation key** (always last)

## Project Summary

Identity table opening rows, in order:

1. Project  
2. Address  
3. Owner  
4. Description  
5. **Budget**

Budget is always present. Value comes from profile / user-provided budget when known; otherwise the same empty-detail pattern as other summary fields (`Not provided` / TBC). Create/update prompts and greenfield structure checks require these five opening rows.

## Transmittal scaffold

Inserted immediately before Citation key:

```markdown
## Transmittal (0 documents)

| Document number | Title | Rev | Category |
| --- | --- | --- | --- |
```

Same heading and table shape as RFP so parse/match/`replace_transmittal_section` work unchanged. Citation key stays last.

## UI and cockpit flow

1. User opens a draft with a Transmittal-style heading (RFP or PMP).  
2. **Load Transmittal** (on the Transmittal `h2` row) parses the table, matches evidence, selects rows in the repository, and starts a draft-scoped `transmittalSession`.  
3. Repository enters multi-select curation mode; Save is no longer in the repository toolbar.  
4. **Save Transmittal** (same `h2` row) posts selected evidence IDs for that draft, replaces the Transmittal section, refreshes markdown (heading count updates), and clears the session.  
5. create-pmp `DraftReviewPanel` receives the same repository/selection/session props as procurement. Cockpit keeps the create-pmp workbench open while curating, mirroring procurement-requests.

Load/Save remain hidden for accepted/locked drafts and for drafts without a Transmittal-style heading.

## Edge cases

- Switching away from the session draft clears or ignores the session so Save cannot target the wrong artefact.  
- Empty selection: Save disabled or rejected with the current RFP behaviour.  
- Older PMPs pick up Budget and Transmittal on the next create/update rewrite of those sections; no bulk migration of historical drafts.  
- Standalone `create_transmittal` workflow is out of scope.

## Errors

Reuse existing replace-transmittal failures (unknown evidence IDs, missing section, auth). Surface save failures near the middle-pane buttons.

## Touch points

| Area | Files (indicative) |
| --- | --- |
| PMP scaffold | `pmp_renderer.py`, `section_contracts.py`, taxonomy section order / weights |
| Summary + prompts | create/update PMP instructions, `pmp_greenfield_brief.py` structure checks |
| Replace path | Existing `rfp_renderer.replace_transmittal_section` + drafts transmittal API |
| UI | `MarkdownContent.tsx`, `DraftReviewPanel.tsx`, `DocumentRepositoryPanel.tsx`, `ProjectCockpitPage.tsx`, `ProjectControlBoard.tsx` |
| Tests | Greenfield/order/summary-row tests; MarkdownContent Load/Save placement; create-pmp load/save wiring; repository Save removed |

## Out of scope

- New transmittal APIs or PMP-only UI forks  
- Changing how RFPs seed their initial issued-document set  
- Standalone create_transmittal artefact workflow  

