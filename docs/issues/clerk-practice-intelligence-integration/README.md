---
title: Clerk Practice Intelligence Integration Issue Pack
status: draft
source: 99-docs/issues/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md
triage_label: needs-triage
labels: [needs-triage, clerk, sitewise, migration]
---

# Clerk Practice Intelligence Integration Issue Pack

This issue pack breaks the Clerk Practice Intelligence Integration PRD into vertical slices for implementation in the Clerk repo.

Target repo:

`D:/AI Projects/clerk`

Source PRD:

`99-docs/issues/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md`

## Dependency Order

1. `CPI-001-ratify-clerk-integration-prd-in-target-repo.md`
2. `CPI-002-import-sitewise-platform-knowledge-into-clerk.md`
3. `CPI-003-create-hosted-sitewise-project-catalog.md`
4. `CPI-004-open-a-minimal-project-cockpit.md`
5. `CPI-005-scope-clerk-chat-to-the-active-project.md`
6. `CPI-006-make-cross-project-search-explicit.md`
7. `CPI-007-implement-the-sitewise-three-overlay-gate.md`
8. `CPI-008-persist-draft-artefacts-with-provenance.md`
9. `CPI-009-run-create-pmp-through-clerk-workflow-runtime.md`
10. `CPI-010-review-create-pmp-draft-in-the-cockpit.md`
11. `CPI-011-retire-practice-node-hermes-runtime-from-product-path.md`
12. `CPI-012-prepare-vps-deployment-path-for-integrated-clerk.md`

### Hosted document intake (after cockpit foundation)

13. `CPI-013-add-hosted-inbox-upload-and-ingest-api.md` ✓
14. `CPI-014-use-repository-panel-as-inbox-upload-drop-zone.md` ✓
15. `CPI-017-port-practice-document-metadata-extraction.md` ✓ *(can start parallel with 013)*
16. `CPI-018-wire-ingest-document-metadata-persistence.md` ✓
17. `CPI-016-add-document-register-table-and-preview-api.md`
18. `CPI-015-run-document-intake-sort-files-workflow.md`

Intake sequence:

1. **Metadata engine** — port Practice `documentMetadata.ts` extraction to Python (`CPI-017`) ✓
2. **Upload** — user drags files onto the far-right repository panel; backend stores under `_inbox/` and auto-ingests with register metadata (`CPI-013` ✓ backend; `CPI-014` ✓ frontend)
3. **Register table** — panel shows Doc No | Title | Rev | Category from ingested metadata (`CPI-016`).
4. **Sort Files** — user runs Document Intake to classify, rename, file, and refresh register rows (`CPI-015`).

### Create PMP quality and speed (hybrid document compiler)

Source PRD: `docs/plans/2026-06-08-sitewise-document-compiler-hybrid-prd.md`

19. `CPI-019-implement-pmp-hybrid-document-compiler.md` — extract → render → small narrative LLM; replaces monolithic full-doc generation (depends on CPI-009; benefits from CPI-017)

## Notes

- Issues are written as local markdown issues so they can be copied into the Clerk repo.
- Each issue carries `needs-triage` in frontmatter.
- HITL issues require an explicit human decision or review before downstream work proceeds.
- AFK issues are intended to be implementable by an agent once copied into Clerk.
