---
version: 2
slug: "frontend-public-landing-html"
primary_target: "frontend/public/landing.html"
related_targets: ["frontend/public/landing-assets/landing-story.css", "frontend/public/style-guide/tokens.css", "frontend/public/style-guide/satoshi-font.css", "frontend/public/style-guide/logo/mark-solid.svg"]
---

# Landing page surface brief

- **Scope:** `frontend/public/landing.html`; Persuade mode. Standalone static route outside the React SPA.
- **Audience:** Australian client-side project managers and construction professionals who need to reconcile fragmented evidence before making commercial decisions.
- **Job:** make SiteWise’s core value legible through one credible project thread: an OSD requirement that affects briefing, tender comparison, live project controls, correspondence and invoice review.
- **Primary action:** open SiteWise. Secondary action: follow the evidence down the page.
- **Proof boundary:** Seven Hills is explicitly labelled as a synthetic, fictional demonstration project. The UI states are semantic HTML/CSS illustrations of supported product behaviour, not customer screenshots.
- **Length:** one outcome-led hero, four connected beats and a close. No feature-card catalogue.

## Story structure

| Section | Message | Product proof |
| --- | --- | --- |
| Hero | The cheapest submitted tender omitted the OSD tank | Three-bidder comparison with the explicit exclusion, clarification and comparable arithmetic |
| `#project` | The file pile becomes a live project | Evidence rail, cited PMP facts, inline edit and “Not evidenced” state |
| `#appointments` | A reviewed appointment carries through shared controls | 15 proposals, five controlled appointments, 25 invoices and one authorised update path |
| `#tenders` | The comparison follows scope, not headline total | C-201 → stated tender exclusion → RG-26031-ADD-01 → computed comparable basis |
| `#change` | New evidence proposes downstream changes; it does not silently make them | Pulse intake, S-202 Rev C supersession, PMP/cost/programme review and unsent email draft |
| Close | The evidence stays attached and the decision stays human | One CTA |

## Direction

Dark graphite ground, bone typography and one evidence blue. Use Satoshi Light for display, Hanken Grotesk for prose and IBM Plex Mono only for document identifiers, costs and compact system labels. Surfaces are square, flat and separated by hairline rules. No gradients, shadows, glass, screenshot crops or decorative illustration.

Amber is reserved for one moment only: Redgum’s explicit OSD exclusion in the hero comparison. Other review and authorisation states use blue, bone or neutral grey. There is no third accent colour.

The layout behaves like a project record rather than a feature-card grid: comparison tables, evidence registers, source chains and a change ledger. Headings carry their own hierarchy; never add kickers or section-number decoration.

## Motion

One authored moment only: a solid blue evidence line resolves from C-201 through the bidder exclusion to the clarification on first load. It uses an exponential ease-out and finishes in a settled, already-legible state. Reduced-motion mode presents the line immediately. No scroll entrances, drifting lights, cursor effects or looping animation.

## Copy and truth rules

- Project: fictional `14–18 Wianamatta Avenue, Seven Hills NSW`; 11 townhouses. Formal entities, if named, are Wianamatta Developments Pty Ltd and Ridgeline Project Management Pty Ltd.
- Tender facts: Redgum $9.080m with a stated 120 m³ OSD exclusion in RG-26031 and +$420k clarification in RG-26031-ADD-01 dated 24 April 2026; Ironbark $9.340m including OSD and appointed by the project team; Calderline $9.460m including OSD.
- Do not rank, recommend or infer builder motives. “Excluded” is used only where the submission states it. Silence is “not explicitly itemised — confirm with builder”.
- Project controls: 15 consultant proposals, five controlled appointments, 25 consultant invoices, 52 drawings and 13 reports.
- Change: S-202 Rev C supersedes Rev B; QS advice is +$68,500 ex GST; programme note is +10 calendar days; PMP v3 → v4, cost and programme changes are reviewed/user-authorised; the reply remains `Draft — not sent` until Send.
- Pulse surfaces and files evidence. It does not autonomously approve downstream mutations or send email.
- CTA destination is `/login`. Australian spelling throughout.

## Responsive and accessibility

- ≤1080px: hero and beats become one column while preserving their narrative order.
- ≤760px: source rail stacks above PMP; multi-stage controls become vertical; comparison and appointment tables remain complete in labelled horizontal scroll regions.
- ≤540px: proof line becomes a compact stacked trace, PMP fields become single-column and the change ledger becomes a readable list.
- All data tables have captions and row/column headers. Scroll regions are keyboard-focusable and labelled. Decorative logo artwork has empty alt text while the brand name remains visible.
- Body text meets 4.5:1 contrast, controls have visible keyboard focus and touch targets are at least 44px where interactive.
