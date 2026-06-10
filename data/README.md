# Data

Local document corpus for Clerk. All source material used to build and test ingestion, retrieval, and grounded Q&A lives here — nothing is fetched from external APIs at runtime.

The backend ingestion pipeline reads files from these folders, normalizes them into searchable text, chunks and embeds the content, and stores the result in Supabase. Clerk answers questions from this corpus only.

## Corpus folders

Twelve top-level folders — eleven project sets plus reference seed material (~1,900 files).

### Advisory

Due diligence, compliance, and specialist advisory reports.

| Folder | Files | Contents |
| ------ | ----- | -------- |
| `advisary-contamination-1/` | 23 | PGIM Bond Living Erskineville Stage 1 technical DD — contamination and environmental advisory. HazMat surveys, detailed site investigations, remediation cost estimates, RAP, site audit reports, planning advice, and supporting cost plans. |
| `advisary-NCCcompliance/` | 22 | NCC / building compliance advisory for 53 Britton — Feso report, compliance assessment annexures (AFSS, site inspection, services engineer recommendation, cost plan, programme), and consultant fee proposals and evaluations. |

### Delivery

Live construction and D&C contract administration records.

| Folder | Files | Contents |
| ------ | ----- | -------- |
| `delivery-house/` | 28 | House build delivery — contracts, BASIX/CC certificates, specifications, cost schedules, site plans, and compliance evidence. |
| `delivery-petersham/` | 405 | Petersham D&C delivery — contract & FIOA, LOI, annexures, progress claims, variations, EOT, and supporting correspondence. |
| `delivery-bankstown/` | 195 | Bankstown multi-dwelling delivery — general conditions, FIOA, PPR, DA consent, stamped drawings, consultant disciplines (architecture, structure, hydraulic, mechanical, electrical, BCA, BASIX, fire, landscape, access, acoustic), marketing suite, and airspace approvals. |

### Procurement

Tender packages from EOI/RFT through to recommendation.

| Folder | Files | Contents |
| ------ | ----- | -------- |
| `procurment-demo/` | 35 | Smallest procurement set — good smoke test for the ingestion pipeline. |
| `procurement-industrial-new/` | 25 | Industrial new-build procurement — LOI, FIA, AS 4902 contract, building performance brief, ERVM cost report, tenant info pack, and tender recommendation. |
| `procurement-blockb/` | 210 | Block B procurement — TEP, EOI, RFT, addenda, tender submissions, evaluation, and tender recommendation report (TRR). |
| `procurement-industrial-add/` | 311 | Industrial addition procurement — design brief, BCA compliance report, tender pack, letters, RFI & addenda, submissions, assessment, and recommendation. |
| `procurement-campy/` | 655 | Campy tender package — RFT, preliminary design, tender submissions, evaluation, and recommendation. Includes DWG drawings. |

### Consultants

| Folder | Files | Contents |
| ------ | ----- | -------- |
| `consultants-campy/` | — | Consultant procurement and appointment documents for the Campy project. *(Empty — ready to populate.)* |

### Reference

| Folder | Files | Contents |
| ------ | ----- | -------- |
| `seed/` | 23 | Reference knowledge — markdown guides on contracts, cost, procurement, programming, roles, NCC, and residential delivery. Supports grounding and agent instructions; not project-specific evidence. |

Folder names map to real project contexts. Treat each as an isolated document set with its own metadata (project name, phase, document type).

## File types

The corpus is mixed-format project documentation:

- **PDF** — contracts, certificates, reports, drawings issued as PDF, tender documents, advisory reports
- **Word** (`.doc`, `.docx`) — contracts, specifications, letters, DD reviews
- **Excel** (`.xlsx`) — cost reports, price schedules, claim trackers, fee evaluations
- **CAD** (`.dwg`) — drawings (`procurement-campy`)
- **Email** (`.msg`) — project correspondence (delivery and procurement folders)
- **Archive** (`.zip`) — bundled tender submissions (`procurement-industrial-add`)
- **Images** (`.jpg`, `.png`) — photos, marketing CGIs, site inspection figures
- **Markdown** (`.md`) — seed reference material in `seed/`

Ingestion should handle PDF and Word first; other formats can be added as the pipeline matures.

## How Clerk uses this data

1. **Discover** — walk the corpus folders and build a manifest of files (path, project, phase, type, size).
2. **Extract** — parse each file to normalized text (Markdown where possible).
3. **Chunk** — split into retrieval-ready passages with metadata (project, folder, filename, page/section).
4. **Index** — embed chunks and store in Supabase for hybrid semantic + full-text search.
5. **Query** — users ask questions in plain English; Clerk retrieves from these chunks and returns cited answers.

The corpus on disk is the source of truth. Do not assume documents exist elsewhere.

## Conventions

- Keep project documents inside their named folder; do not flatten the tree.
- Preserve original filenames — they carry useful context for citations.
- Add new projects as new top-level folders under `data/`, using a consistent prefix:
  - `delivery-<name>/` — construction administration
  - `procurement-<name>/` — tender packages
  - `advisary-<topic>/` — due diligence and specialist advisory *(folder name as on disk)*
  - `consultants-<name>/` — consultant appointments
- Tag each document with `phase` at ingestion: `advisory`, `delivery`, `procurement`, `consultants`, or `reference`.
- `seed/` is reference doctrine, not live project evidence. Ingest with `source_type: reference` so retrieval can distinguish seed knowledge from project records.

## Suggested ingestion order

Start small, validate, then scale:

1. `procurment-demo/` — smoke test
2. `delivery-house/` — compact delivery set
3. `procurement-industrial-new/` — small industrial procurement
4. `advisary-NCCcompliance/` — advisory reports and annexures
5. `advisary-contamination-1/` — environmental DD package
6. `procurement-blockb/` — medium procurement with correspondence
7. `procurement-industrial-add/` — larger industrial procurement (includes ZIP archives)
8. `delivery-bankstown/` — structured multi-dwelling delivery package
9. `delivery-petersham/` — large D&C delivery with claims and variations
10. `procurement-campy/` — largest set; includes DWG files
11. `seed/` — reference guides (tag separately)
12. `consultants-campy/` — when populated

## Git and size

Project payloads (PDFs, drawings, spreadsheets, archives) are large (~1,900 files across the corpus). If the repo grows unwieldy, consider gitignoring specific corpus folders and documenting how to obtain them locally — but for development, this folder is the working corpus.
