# Official planning attachments

**Date:** 2026-08-16  
**Status:** Design validated  
**Applies to:** Official web research (`app/web_research/`), project ingest, answer trace

## Goal

Ground planning answers in the actual instrument text for the active project:
state legislation, the applicable LEP, and the applicable DCP. Stop treating a
blocked HTML scrape of `legislation.nsw.gov.au` as a sourced read.

## Decisions

| Topic | Choice |
| --- | --- |
| Scope | Per-project official attachment, added only when that project needs it |
| Shared LGA cache | No. Different LGAs, classes, and scopes rarely share the same clauses |
| State Acts / SEPPs / LEP | Official NSW legislation XML export, not Cloudflare-guarded HTML |
| DCP | Allowlisted council `.nsw.gov.au` PDF fetch, or user upload if the council site challenges |
| Storage plane | Official reference on the project, never `project_evidence` |
| Browser / stealth fetch | No. Do not automate around bot protection |
| Open-web roam for “the DCP” | No. Explicit URL or user file only |

## Why the current path fails

`search_web` ranks a local NSW legislation registry. `read_web_source` then
fetches the live HTML page. `legislation.nsw.gov.au` challenges that fetch.
Search hits stay discovery candidates. The UI falls back to “Internet search”
and the model answers from profile facts plus titles.

The Inner West LEP is an EPI on the same site, so it has the same HTML problem
and is not in the registry. A DCP is a council PDF, not legislation, and has no
fetch or ingest path today.

`docs/architecture.md` already forbids automating around a browser challenge.
The sanctioned machine channel is the NSW legislation XML export.

## Four-plane rule

Official attachments stay in plane 3 (official reference). They are stored on
the project so this project can retrieve them, but they are never owner
evidence.

| Field | Value |
| --- | --- |
| `project_id` | Active project |
| `source_type` | `reference` |
| `document_class` | `planning_instrument` (already declared, not classified today) |
| `knowledge_scope` | `official` |
| Provenance | Canonical official URL, publisher, jurisdiction, authority class, version status, effective date, retrieved-at, content hash |

Answer trace: a successfully attached/read instrument is a **Web source** (or
equivalent official-instrument chip), not **Internet search**. Search without a
read stays a discovery candidate.

Project document tools may retrieve these rows only when labelled as official
controls. They must not be cited as if the client issued them. Identity
bootstrap (client, address, budget) must ignore them.

## Attach paths

1. **State law and LEP.** Resolve the instrument from the NSW registry (expand
   it to include the project LGA’s LEP). Read the official XML export for that
   instrument id. Persist the snapshot on the project with provenance. Section
   reads go against the snapshot.
2. **DCP.** User or agent supplies a specific council PDF URL, or the user
   uploads the PDF. Fetch only HTTPS `.gov.au` hosts already allowed by the
   web fetcher. Persist the same way. If the council site challenges, fail
   clearly and ask for upload.
3. **Refresh.** Re-fetch when the user asks, or when the snapshot is older than
   a stated freshness window. Keep the previous hash so a change is visible.

Do not ingest a fetched instrument as an ordinary inbox upload. Do not copy it
into platform knowledge.

## Agent behaviour

When a planning question needs current controls and the project has no matching
official attachment, the agent says so, then attaches the needed instrument
(or asks for the DCP PDF). It does not answer from titles or model memory as if
the page had been read.

Once attached, later turns on that project reuse the snapshot. They still
state retrieval date and that legal interpretation may need professional
confirmation.

## Out of scope

- Shared LGA or statewide instrument warehouse
- Spatial Viewer / zoning-map scrape
- Headless browser or user-agent spoofing
- Auto-discovery of “the” DCP by crawling a council site
- Changing the four-plane doctrine so official text becomes project evidence

## Next step

Write the implementation plan (`docs/plans/2026-08-16-official-planning-attachments.md`)
with test-first tasks for: XML read adapter, `planning_instrument` classify +
persist, attach tool, answer-trace labelling, and DCP PDF attach/upload.
