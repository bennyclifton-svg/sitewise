---
title: Practice Node And Hermes Runtime Retirement
date: 2026-06-07
status: accepted-for-migration
source: docs/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md
---

# Practice Node And Hermes Runtime Retirement

Clerk is the canonical hosted product path after the Practice Intelligence migration. The Practice dashboard, Practice Node backend, and Hermes runtime remain reference material for cockpit behavior, workflow contracts, storage semantics, and trace expectations. They are not production runtimes for new Clerk workflow work.

## Decision

New SiteWise workflow implementation lands in Clerk's FastAPI backend, SQLAlchemy/Alembic schema, Supabase-backed retrieval, and React cockpit. Practice Node and Hermes are retired as separate product-path runtimes once Clerk can run and review Create PMP through the integrated cockpit path.

The product owner directed the CPI issue pack through implementation on 2026-06-07. Final operational retirement still requires human review of the deployed Create PMP path before removing any remaining Practice-only planning references.

## Reference Material To Keep

- Practice cockpit layout and draft review patterns.
- Practice storage adapter behavior as a contract reference for workspace paths and draft locations.
- Practice agent runtime traces as reference for workflow event shape.
- SiteWise doctrine, seed, skills, and project template material migrated into Clerk platform knowledge.

## Product Path

- New project catalog, cockpit, chat scope, workflow runtime, draft persistence, and deployment work belongs in Clerk.
- Production deployment documentation must describe one Clerk frontend and one Clerk FastAPI backend.
- No production deployment path depends on the Practice Node backend or Hermes runtime.
