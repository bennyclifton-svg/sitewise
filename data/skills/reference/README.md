# Skill References

This folder holds skill-adjacent reference material that is not itself an invokable workflow.

Reference material can be loaded by system skills or app workflows when it is part of the governed SiteWise context. It must not be treated as active-project evidence unless the active project folder also contains matching project evidence.

## Index

- `nsw-residential-cost-breakdown-reference.md` - NSW Class 1 house/townhouse cost taxonomy.
- `nsw-multi-residential-cost-breakdown-reference.md` - NSW apartment, BTR, student-housing and social/affordable-housing cost taxonomy.
- `nsw-commercial-fitout-cost-breakdown-reference.md` - NSW Class 5 office/coworking tenancy fit-out cost and pricing-returnable taxonomy.
- `nsw-commercial-base-building-cost-breakdown-reference.md` - NSW office and retail base-building cost taxonomy.
- `nsw-building-remediation-cost-breakdown-reference.md` - cross-class NSW building-rectification cost taxonomy.
- `nsw-industrial-warehouse-cost-breakdown-reference.md` - NSW Class 7b warehouse/logistics cost taxonomy.
- `nsw-industrial-process-facility-cost-breakdown-reference.md` - NSW manufacturing/process-facility cost taxonomy.
- `nsw-industrial-cold-chain-cost-breakdown-reference.md` - NSW cold-storage/food-processing cost taxonomy.
- `nsw-data-centre-cost-breakdown-reference.md` - NSW data-centre cost taxonomy.

All references are structure and pricing-returnable guidance only. Runtime
support is controlled by `backend/app/sitewise/cost_plan_coverage.py`; known
coverage and retention decisions are recorded in
`docs/guides/platform-knowledge-coverage.md`.
