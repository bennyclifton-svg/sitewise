# PMP 2.0 acceptance checklist

Manual sign-off doc for Benny. Run each scenario in print preview and confirm the primary PMP stays within the 2–4 A4 page band, emphasis lands on the right sections, and annexures preserve overflow detail.

## Scenarios

- [ ] **No-document base case** — taxonomy-only project, zero uploaded documents; scaffold renders with User provided / Not evidenced labels and no Grounded claims.
- [ ] **Residential refurb** — residential / refurb / house; compliance and scope emphasis match the residential refurb profile.
- [ ] **Commercial new** — commercial / new build; procurement and programme sections carry the expected weight.
- [ ] **Commercial fire-services refurb** — fire-services work scope; compliance section foregrounds AS 2419.1 / AS 2941 references.
- [ ] **Advisory** — advisory work type; services/deliverables headings and advisory emphasis profile.
- [ ] **100-document sweep** — active corpus near the sweep cap; ActivityFeed shows batched `evidence_sweep` trace events; primary PMP remains in the word band with annexure overflow.
- [ ] **Deleted / superseded downgrade** — remove or supersede a supporting document, run Refresh PMP from documents; formerly grounded rows downgrade to Not evidenced and user-provided conflicts stay visible.

## Refresh UX checks

- [ ] Draft review shows **What changed in v{n}** with section badges after Update PMP.
- [ ] Evidence-change strip reports added / removed / superseded / downgraded counts and links to the sweep trace.
- [ ] User-locked `pmp-decision` blocks survive refresh.

## Recorded baseline exceptions

Pre-existing failures documented in `docs/plans/2026-07-05-pmp2-live-interactive-pmp.md` remain out of scope for this sign-off.
