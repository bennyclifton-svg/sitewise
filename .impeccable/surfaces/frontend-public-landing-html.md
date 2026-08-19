---
version: 1
slug: "frontend-public-landing-html"
primary_target: "frontend/public/landing.html"
related_targets: ["frontend/public/landing-assets/landing-story.css","frontend/public/landing-assets/sitewise-app-workspace.png","frontend/public/landing-assets/sitewise-export-preview.png","frontend/public/style-guide/tokens.css","frontend/public/style-guide/light.css","frontend/public/style-guide/motion.css"]
---

# Landing page surface brief

Replaces the Mark 3 facet-engine brief (2026-08-06). That page depended on
`landing-assets/application/project-profile-greenbank.png` and
`landing-assets/source-documents/*`, none of which exist in this tree, so its
entire first viewport was broken. The old markup is recoverable from git; the
old stylesheet is still on disk at `landing-assets/landing.css`, unused.

- **Scope:** `frontend/public/landing.html`; Persuade mode. Standalone static route, outside the React SPA.
- **Audience:** Australian construction management professionals who receive project evidence as it lands — forwarded threads, phone photos, scans nobody renamed — and have to hold the project in their head across all of it.
- **Job:** show that fragmented project evidence becomes one connected, checkable project, and that the constraint inside it surfaces early.
- **Primary action:** open SiteWise. Secondary: see what it makes.
- **Length:** hero plus four beats plus a close. Deliberately short; it is not a feature tour.

## Structure

| Section | Claim | Medium |
| --- | --- | --- |
| Hero | You do the judgement, SiteWise does the assembly | Copy + the evidence field and reading pulse |
| `#reads` | It knows what `scan004.pdf` is | Classification register, drawn |
| `#facts` | One line out of forty pages | Real application crop, citations visible |
| `#constraint` | Then the facts meet each other | Site overlay, drawn, one amber intersection |
| `#builds` | You get a document, not an answer | Real issued PMP with its citation key |
| Close | You've still got the last word | Copy + CTA |

## Direction

Near-black graphite ground from `style-guide/tokens.css`, bone type, Satoshi
Light display over Hanken Grotesk and IBM Plex Mono. Square by default,
hairline rules, elevation as luminance rather than drop shadow — the existing
light system (`light.css`) is mounted unchanged.

**Colour rule.** Blue (`--sw-facet-blue` / `--sw-beam`) is SiteWise reading:
the pulse, the facts it keeps, the routes it files to, the concept footprints.
Amber (`oklch(72% 0.14 75)`) appears **exactly once on the page** — the
intersection of footprint and easement in `#constraint`, plus its callout and
flag. This extends the incumbent blue-only rule rather than breaking it: amber
means constraint or unresolved, nowhere else. Do not introduce a third hue and
do not reuse amber for emphasis.

**Motion.** One authored moment: the pulse crossing the evidence field, once,
on load, with each fragment resolving as the pulse reaches its x position.
Nothing else animates on scroll — `sw-reveal` was deliberately removed from
every beat so the page does not repeat one identical entrance per section.
Reduced motion drops the pulse and presents the settled reading.

## Proof, and its limits

- The two screenshots are real application output. Both are CSS-cropped: the
  workspace capture to source `x 250-1240, y 150-830`, which excludes an OS
  watermark and the signed-in username; the export to `x 244-1020, y 44-1200`,
  which removes the capture's own grey page mat.
- Cropped images need explicit `height: auto`. The `width`/`height` HTML
  attributes act as presentational hints and will otherwise pin the intrinsic
  pixel height and silently break the crop scale.
- The classification register uses the intake classifier's **real** vocabulary
  and **real** filing routes (`backend/app/intake/classifier.py`, `_ROUTES` and
  `_ROUTES_BY_CLASS`). If those routes change, this table is wrong. It carries
  no confidence percentages, because the numbers in the film brief were
  illustrative and would read as an invented metric.
- The hero fragments show a document's shape as abstract rules and only the
  one surviving fact as real text. No document body copy is fabricated.
- The constraint overlay is a drawing, labelled as illustrating the check.
- Standing constraint: no invented metrics, customers, or testimonials.
  Australian spelling throughout. `/login` for both primary actions.

## Responsive

- ≤980px: hero and beats collapse to one column.
- ≤720px: the classification register becomes stacked records rather than a
  table whose third column — the filing route, the whole point of the beat —
  scrolls out of reach.
- ≤620px: the hero's absolutely-placed pile becomes a stacked, overlapping
  pile; the ghost cards and the pulse are dropped. The constraint overlay's
  in-drawing annotation is hidden because it renders below legibility at that
  width; the amber flag and the body copy carry the words instead.
- Section classes must use `padding-block`, never the `padding` shorthand —
  the shorthand wipes `.lp-shell`'s `padding-inline` and the page loses its
  side gutters entirely on narrow viewports.

## Known asset issue

`landing-assets/sitewise-export-preview.png` is a JPEG carrying a `.png`
extension. Browsers sniff it, so it renders, but a strict `Content-Type` from
the host is wrong. Rename with the reference when convenient.
