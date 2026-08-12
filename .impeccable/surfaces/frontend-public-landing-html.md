---
version: 1
slug: "frontend-public-landing-html"
primary_target: "frontend/public/landing.html"
related_targets: ["frontend/public/landing-assets/landing.css","frontend/public/landing-assets/sitewise-hero.js","frontend/public/landing-assets/application/project-profile-greenbank.png","frontend/public/landing-assets/source-documents/","frontend/public/landing-assets/sitewise-export-preview.png"]
---

# Landing page surface brief

- Scope: `frontend/public/landing.html`; Persuade mode.
- Audience: Australian construction management professionals juggling several live projects, discipline hand-offs and fragmented incoming information who need to understand SiteWise in seconds without decoding AI infrastructure.
- Job: make the value tangible as the transformation from dense, differently structured project records into one source-grounded working artefact.
- Primary action: open SiteWise. Secondary action: see the working application.
- Proof on the page: five linked, attributable public-source records, the governed runtime boundary, the current SiteWise issue-export template, and the requested artefact set. The demonstration PMP cites only `DA-1100` (Ground Floor Plan); the other four records are available samples, not contributing evidence. No invented metrics, customers, or testimonials.
- Direction: preserve the approved artefact-forward production line, but express its runtime through the exact SiteWise Mark 3 geometry: three 60-degree axes, five occupied facets and one open aperture.
- Memorable moment: the real Greenbank project-profile view appears beside the promise while small public-document thumbnails leave a compact incoming window and land in the screenshot's actual right-hand repository; desktop scrolling then rotates the 3D mark into architectural depth and opens it into six sectors while one small blue judgement token visits the five deterministic facets.
- Constraints: preserve the existing SiteWise mark, blue-only accent, square faceted surfaces, Satoshi Light for display/brand with Hanken Grotesk / IBM Plex Mono for body and labels, `/login` actions, reduced-motion support, and the standalone static landing route. At `900px` and below, replace the sticky transition with project profile → facet engine → issued sheet in normal document flow. For reduced motion, keep both the document thumbnails and judgement token still.

## Composition and medium inventory

| Ingredient | Commitment | Medium |
| --- | --- | --- |
| Navigation | SiteWise mark, three anchors, sign-in | Semantic HTML + existing logo SVG |
| Opening promise | Plain-language headline, lede and primary action beside the actual Greenbank project-profile application view | Semantic HTML/CSS + supplied application screenshot |
| Repository ingest | A compact incoming-documents window emits one real document thumbnail at a time into the screenshot's actual right-hand repository column | CSS motion over real rendered source pages; hidden motion for reduced-motion users |
| Mark transition | Approved logo camera → architectural camera → plan view on desktop; omitted in sequential mobile and reduced-motion presentations | Existing Three.js SiteWise Mark 3 + static fallback |
| Runtime | Six exact isometric sectors containing parse, retrieve, filter, calculate, validate and issue | Semantic HTML/CSS facet geometry |
| Judgement | One small blue token visits the five deterministic facets on desktop and stays still in sequential presentations; never present it as calculator or source of fact | Scroll-driven DOM motion + static fallback |
| Output proof | A public-project PMP citing only `DA-1100`, rendered through the current SiteWise issue-export HTML template | Current application renderer + captured preview |
| Product proof | Public-source register, selected facts, current issue sheet, and restrained crop of the real PMP workspace | Semantic HTML/CSS + application screenshot |
| Trust boundary | Deterministic sequence beside selective AI judgement calls | Semantic lists in one shared technical board |
| Artefact register | Six outputs, inputs used, and deterministic checks | ARIA table roles + responsive CSS |
| Close | One plain-language CTA, no invented proof | Semantic HTML/CSS |

## Translation from the approved comp

- Keep the comp's artefact priority and asymmetry; replace its generic production machinery with the mark's own spatial system.
- Carry forward Grounded / Deterministic / Editable as the product-proof sequence. Base the source register on the implemented `UsageMarks` behaviour: a single azure dot means that document contributed to the artefact currently open. In this demonstration that dot belongs only to `DA-1100`; do not imply that the invoice, structural notes, specification, or legislation informed the PMP.
- Show only the facts visible in `DA-1100` as the demonstration transformation: project and drawing identity, preliminary status, ground-floor brief, parking and coordination controls, all tied to the single citation.
- Real source pages may stay visibly messy; architectural photographs are strongly tinted and clipped inside tool facets only.
- The production line must stay diagrammatic, legible, source-attributed, and clearly part of the current SiteWise system rather than a game HUD.
