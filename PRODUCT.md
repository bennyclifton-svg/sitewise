# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are construction management professionals working Australian built-environment projects. That includes architects, project managers, engineers, and contractors — including design-and-construct contractors. The audience is a mix of practice roles, not a single job title.

They are ordinary Australians in the built environment: creative and often flamboyant, and also intelligent. The product should speak to that register — not corporate jargon, not tech-bro hype.

## Product Purpose

SiteWise (`sitewise.au`; this repo is the hosted product codebase, historically called Clerk) is an evidence-grounded agentic workspace for construction project delivery.

It exists because residential and project delivery work runs on documents — briefs, PMPs, cost plans, tenders, registers — assembled under a professional standard of care, while generic AI assistants invent numbers, addresses, and clause references. In a domain where outputs can become contract instruments, fluency without provenance is a liability.

Success means SiteWise delivers on that promise: professionals get real leverage on slow, inefficient Australian delivery and planning friction, with enough technological hope that agentic AI feels present and credible — without abandoning the hard foundations of the work.

## Positioning

SiteWise is the agentic construction OS that fuses AI agency with bricks-and-mortar reality.

- The model is a language interface and classifier. It is never the calculator and never the source of a fact. Arithmetic, totals, deltas, and reconciliations are computed in software; claims trace to project evidence or versioned platform doctrine.
- The product must resonate as the agentic solution the industry expects is coming, while staying fused to construction’s material foundations — concrete, steel, cement, mortar — and to the clarity and synthesis an architect brings to a design: reduce noise, compose the essential structure, make the position legible.

Neighbouring chat tools can draft fluent prose. They cannot truthfully claim SiteWise’s determinism boundary, evidence ledger, and revision-safe project artefacts.

## Operating Context

Users work in a browser SPA against a FastAPI backend, with Supabase auth, Postgres, and project file storage. Day-to-day scenes include the project cockpit, document repository, grounded chat that can queue workflows and edit artefacts, and flagship Tender Comparison from natural language.

Domain materials include uploaded project evidence (quotes, reports, drawings, contracts), SiteWise platform doctrine/seed knowledge, and durable drafts (PMP, cost plan, tender comparison reports). Australian residential project norms, state overlays, and planning/authority friction are part of the operating reality — not optional colour.

Hermes is the headless agent runtime; Clerk MCP tools are the authorised action surface. Legacy grounded-RAG chat remains until the planned cutover gate passes.

## Capabilities and Constraints

Confirmed or in-flight product capabilities:

- Project-scoped workspaces with evidence ingest, retrieval, and grounded drafting
- Deterministic cost/tender arithmetic in Python; LLMs classify, extract, map, and draft narrative only
- Tender Comparison as the flagship Hermes workflow (taxonomy mapping, silence inference, benchmarks, auditable draft reports)
- PMP and cost-plan workflows; chat that can act through authorised tools
- Stripe billing and `sitewise.au` deployment on the declared stack (see repo README / AGENTS.md)

Constraints that future work must preserve:

- Stack is locked unless explicitly changed (FastAPI, Vite/React SPA, Supabase, Hermes, FastMCP, Stripe, Dokploy/VPS)
- TCM owns `tender_*` tables and stays severable from Clerk core
- No fabricated customer testimonials, benchmarks, pricing claims, or case studies beyond real evidence on hand
- Terminology: SiteWise is the product; Clerk is the hosted product repository name still used in engineering docs

Open / undecided for PRODUCT.md:

- Formal accessibility standard (e.g. WCAG level) not yet set as a product requirement
- Exact go-to-market wedge pricing and concierge-vs-self-serve customer surface details remain plan-era and should not be treated as frozen product truth here

## Brand Commitments

- **Name / domain:** SiteWise; public site `sitewise.au`
- **Voice:** Ordinary Australian. Intelligent, creative, built-environment — not stiff corporate and not empty AI theatre
- **Personality tension (binding):** Hard, gritty construction foundations (material, physical, real) fused with a clear technology / agentic undertone. Clarity and spatial synthesis over clutter — reduce and compose the way an architect synthesises a design
- **Hope without vapour:** Technology should feel like the agentic future arriving, but only if the product delivers; hope is earned by substance

Visual system details (palette, type, components) are not specified here; record them via `/impeccable document` or new-work when needed. Existing SPA tokens and landing assets are implementation evidence, not yet elevated to PRODUCT brand law beyond the commitments above.

## Evidence on Hand

- Product and architecture docs: `README.md`, `docs/architecture.md`, Hermes foundation plans, TCM PRD under `docs/plans/`
- Domain doctrine: `docs/clerk-brief.md` and SiteWise seed/platform knowledge paths referenced by the backend
- Runnable SPA and backend under `frontend/` and `backend/`
- Brand/marketing assets present in-repo (e.g. `frontend/public/landing-assets/`, favicon, hero asset) — treat as assets on hand, not as invented proof of market traction
- Do **not** fabricate testimonials, customer logos, win rates, or time-saved claims without real sources

## Product Principles

1. **Deliver before you dazzle.** Hope and agency only count if the artefact is true, checkable, and useful under professional scrutiny.
2. **Agency with foundations.** AI and agentic workflows are first-class, but they sit on concrete, steel, documents, registers, and contract reality — never float above them.
3. **Synthesise like an architect.** Reduce noise; compose the essential structure; make the project position spatially clear.
4. **Speak Australian built-environment.** Ordinary, intelligent, creative — flamboyant where the craft warrants it, never hollow.
5. **Provenance over fluency.** Numbers are computed; facts are evidenced; assumptions are labelled.
