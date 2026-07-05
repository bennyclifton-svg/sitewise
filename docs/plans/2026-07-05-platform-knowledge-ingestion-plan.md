# Platform Knowledge Ingestion Plan

Date: 2026-07-05

## Goal

Make SiteWise seed knowledge available to Pi/Hermes as authorised shared
platform knowledge for every project, without duplicating it into each project
or treating it as project evidence.

The agent should prefer this curated platform knowledge over general model
knowledge for construction-management questions, while still treating uploaded
project documents as the source of truth for project facts.

## Storage Model

Ingest platform knowledge once into the database:

- `docs/clerk-brief.md` as `source_type = doctrine`
- `data/seed/*.md` as `source_type = reference`
- `data/skills/reference/*.md` as `source_type = reference`
- `project = sitewise-platform`
- `phase = reference`
- `document_metadata.knowledge_scope = platform`
- `document_metadata.platform = sitewise`
- YAML frontmatter persisted under `document_metadata.frontmatter`

Store both:

- whole-document text in `source_documents.normalized_content`, for exact
  section reads via `read_platform_knowledge`
- retrieval chunks plus embeddings in `document_chunks`, for semantic platform
  search

Do not store these rows as `project_evidence`, and do not copy them into every
project.

## Implementation Tasks

1. Enable chunking and embeddings for platform knowledge.

   Today `ingest.router.should_persist_chunks()` skips `doctrine` and
   `reference_guide`. Change that so markdown platform knowledge is chunked
   with the prose chunker and embedded. Keep register-only drawings excluded.

2. Add an idempotent platform ingest command.

   Provide a clear command or script that ingests:

   - `docs/clerk-brief.md`
   - `data/seed/`
   - `data/skills/reference/`

   It should use content hashes so reruns skip unchanged files, and support a
   force mode for rebuilding embeddings after chunking/model changes.

3. Add `search_platform_knowledge`.

   Add an MCP tool:

   ```text
   search_platform_knowledge(project_id, query, topics=None, max_results=8)
   ```

   Behaviour:

   - authorise the turn token for the project
   - require the project overlay gate to pass
   - search only platform rows (`knowledge_scope = platform` or
     `source_type in doctrine/reference`)
   - filter/rank by project overlays and YAML frontmatter
   - return path, title, section, snippet, score, topics, source type, and
     whether the source is mandatory for PMP/cost-plan workflows

4. Harden `read_platform_knowledge`.

   Enforce that the requested path is applicable to the project overlays, not
   merely present in the platform corpus. The tool should allow:

   - paths returned by `list_platform_knowledge`
   - paths returned by `search_platform_knowledge`
   - mandatory workflow paths from `select_required_paths`

   Unknown or inapplicable paths should return a tool error that tells the
   agent to call `list_platform_knowledge` or `search_platform_knowledge`.

5. Update agent instructions.

   Strengthen `backend/app/agent/turn_context.py` and workspace `AGENTS.md` so
   Pi/Hermes follows this strategy:

   - for factual questions about the active project, use project evidence tools
   - for construction-management guidance, consult platform knowledge before
     using general model knowledge
   - label platform knowledge as guidance, not project evidence
   - general model knowledge is last resort only

6. Add tests.

   Cover:

   - seed/doctrine ingest produces `source_documents` rows with platform
     metadata and frontmatter
   - platform knowledge produces retrieval chunks and embeddings
   - `search_platform_knowledge` does not return project evidence
   - overlay filtering prevents irrelevant seeds from being read
   - `read_platform_knowledge` rejects inapplicable paths
   - existing project document search still excludes platform knowledge

7. Run a smoke ingest.

   Execute the platform ingest on a local database, then ask Pi:

   - a Walsh Reno fact question, expecting project document tools
   - a contract-administration guidance question, expecting platform tools
   - a mixed question, expecting project evidence first and platform guidance
     second

## Workflow Impact

### PMP and Cost Plan

This should improve and align the existing PMP/cost-plan workflows, not break
them. They already depend on `select_required_paths()` and seed frontmatter.
The important guardrail is to keep the deterministic required-source lists as
the contract for generated drafts, while letting chat use
`search_platform_knowledge` for exploratory guidance.

Do not remove existing `seed_consulted` or required-platform-source audit
behaviour.

### Tender Comparison

Do not wire this into TCM internals. Tender Comparison remains governed by its
own `data/tender/` seeds, taxonomy, prompts, report language, and eval harness.
TCM does not use Clerk RAG or platform knowledge for extraction, mapping,
arithmetic, or report language.

The only useful impact is chat-side guidance around procurement/tender process
questions before or after a comparison. The TCM pipeline itself should remain
schema-oriented and separate.

## Acceptance Criteria

- Platform knowledge is ingested once and available to every authorised project.
- Pi/Hermes can discover relevant seed guidance semantically without raw
  filesystem access.
- Project evidence remains clearly separate from platform guidance.
- PMP/cost-plan required-source behaviour remains unchanged.
- TCM internals remain untouched.
