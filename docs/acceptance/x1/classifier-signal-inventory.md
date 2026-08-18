# Classifier B signal inventory (Stage 6.1)

Source: `backend/app/intake/classifier.py` on branch `x1/stage-6-collapse-classifiers`,
after Stage 5 (`90f12255`). Disposition follows
[`stage-06-collapse-classifiers.md`](../../plans/2026-08-18-pulse/stage-06-collapse-classifiers.md)
Task 6.1. Semantic = "what is this document". Routing = "given what this is, where
does it live".

Reviewer: plan author (stage-06 table). This agent confirmed each family against
the live file and recorded families the sketch omitted.

| Signal family | Kind | Disposition |
|---|---|---|
| `INBOX_PACKAGE_DESTINATIONS` (37 entries) | **routing** — folder→folder | **Keep in filing.** Not semantic. |
| `_AUTHORITY_FILENAME_PATTERNS` | semantic | Port → `certificate` / `report` + `planning` |
| `_PREVIEW_AUTHORITY_PATTERNS` | semantic (content) | **Split.** Port specific headings (`# planning pathway memo`, principal certifier appointed, certifier engagement on file). **Do not** port bare `Development Application (DA)` / `Complying Development (CDC)` as class — they appear in many reports and would steal semantic class. Chen pack filenames already cover those cases. |
| `_CONSULTANT_COMMERCIAL_PATTERNS` | semantic | Port → `commercial`, `commercial_type=fee_proposal` |
| `_PREVIEW_CONSULTANT_COMMERCIAL_PATTERNS` | semantic (content) | Port → Stage D (`# fee proposal`, `# letter of engagement`, `# engagement letter`). Omitted from the stage-06 sketch; same disposition as the filename family. |
| `_BRIEF_FILENAME_PATTERNS` | semantic | Port → `report` + `brief_kind` |
| `_PREVIEW_BRIEF_PATTERNS` | semantic (content) | Port → Stage D brief headings / sign-off. Omitted from the sketch; same disposition as the filename family. |
| `_DUE_DILIGENCE_FILENAME_PATTERNS` | semantic | Port → `report` + subject (geotech/survey/heritage) or `due_diligence=true` for dilapidation / Sydney Water / sewer / generic due diligence |
| `_PREVIEW_DUE_DILIGENCE_PATTERNS` | semantic (content) | Port → Stage D. Omitted from the sketch; same disposition as the filename family. |
| `_PROGRAMME_PATTERNS` | semantic | Port → `schedule` + `programme` (already partly in Stage 4 scoring) |
| `_PREVIEW_QUOTE_PATTERNS` | semantic (content) | Port → `commercial`, `commercial_type=quote` |
| `_FILENAME_DESTINATION_PATTERNS` | **mixed** | **Split.** Keep discipline routing: `^CC-A-`, `M-?\d{2,4}`, `E-?\d{2,4}`, `^H-`, `^F-`, `^S\d{3}`, `\bctmp\b`. Port semantic: `\bprice[-_ ]?schedule\b`, `\b(tender\|submission\|procurement\|quote)\b`, `\b(invoice\|claim\|estimate\|budget\|cost)\b`, `\b(minutes\|meeting)\b`. |
| `_infer_discipline_slug` | **routing** | Keep — maps discipline → folder. Fed from `classification.document_metadata["discipline"]` when present; filename fallback remains for sheet prefixes. |
| `_consultant_destination` | **routing** | Keep — `commercial_type=fee_proposal` → `02-consultant/{discipline}`. Omitted from the sketch. |
| `is_intake_manifest` | routing | Keep |
| `inbox_package_folder` | routing | Keep |

## Filing metadata the Stage 6.3 table does not name

These destinations exist in Classifier B and in `tests/intake/test_classifier.py`.
They are not `(class, subject)` pairs in the sketch `_ROUTES` table. After port
they live as metadata that `filing_destination` reads — still routing, not a
second semantic engine:

| Metadata | Destination |
|---|---|
| `brief_kind` | `00-brief-pmp` |
| `commercial_type=fee_proposal` | `02-consultant` (+ discipline slug) |
| `commercial_type=quote` | `05-procurement/quotes` |
| `due_diligence=true` | `03-design/01-due-diligence` |
| `procurement_stage` | `05-procurement` (as specified in 6.3) |

## Order after collapse

1. Inbox package folder (user-declared intent).
2. Metadata routes (`procurement_stage`, `commercial_type`, `brief_kind`, `due_diligence`).
3. `_ROUTES` then `_ROUTES_BY_CLASS`.
4. Kept filename discipline prefixes.
5. Discipline slug → `03-design/{slug}`.
6. Else `None`.
