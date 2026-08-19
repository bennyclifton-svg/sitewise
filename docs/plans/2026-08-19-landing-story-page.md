# Landing page — story-derived rebuild

**Date:** 2026-08-19
**Surface:** `frontend/public/landing.html` (Persuade)
**Supersedes on structure:** the section list in `2026-08-06-landing-messaging.md`
**Does not supersede:** that document's spine, its rejected alternatives, or its banned words

## Why

The product owner supplied the Act 1 brief for a future SiteWise film and asked
for a short landing page spawned from that story — hero plus three or four
beats, less dramatic than the film, with the townhouse feasibility case dropped
as a named sample. The 2026-08-12 five-chapter film landing is explicitly
deferred: no time to build it now.

The incumbent Mark 3 facet page was also broken on this branch — its hero
screenshot and all three source-document thumbnails are absent from the tree —
so replacing it cost nothing that was working.

## What carries over from 2026-08-06

- **The spine is unchanged: "You do the judgement. SiteWise does the assembly."**
  The film's own arc ends with a human reading the profile and making the call
  on the easement, so the story and the split-labour frame agree. The rejected
  persona-led and transformation-led headlines stay rejected.
- `INGEST` and `GENERATE` remain banned.
- "Editable working draft" stays a promise completing, never an apology.
- "You get a document, not an answer" and "You've still got the last word"
  are kept verbatim — they were already the sharpest lines on the page.
- Source citations are a handover mechanism for cheap spot-checking, not a
  trust badge. The `#facts` copy says exactly that.

## What changed

The four-label production line (`READ → SORT → RETRIEVE → BUILD`) is gone with
the graphic it labelled. The page is now four beats, each one a step of the
film's pulse:

| Beat | Film moment | Page claim |
| --- | --- | --- |
| `#reads` | scan004.pdf classified | It knows what `scan004.pdf` is |
| `#facts` | noise dims, facts remain | One line out of forty pages |
| `#constraint` | footprint over easement, amber | Then the facts meet each other |
| `#builds` | tokens resolve into the profile | You get a document, not an answer |

`READ` and `SORT` are now one beat (`#reads`) because the register shows both
at once, and it shows them in the product's own words.

Nav anchors changed with the sections: *How it reads / What it catches / What
it makes*.

## Decisions worth not re-litigating

- **The classification register carries no confidence score.** The film's
  `REPORT · GEOTECHNICAL · 94%` is a good beat but an invented number. The
  register shows the real class-and-discipline pair and the real destination
  folder from `backend/app/intake/classifier.py` instead, which is both true
  and more impressive. If that routing table changes, the page is wrong.
- **The named case is dropped, the evidence types are kept.** No address, no
  lot/DP, no dwelling count, no `$6.4m`. A drainage easement, a fill depth and
  a contingency percentage stay, because they are generic to any infill
  feasibility and the page dies without specifics.
- **Amber earns its one appearance.** The film's rule — 95% neutral, amber
  only for uncertainty and constraints — is honoured literally: amber exists
  on this page only at the footprint/easement intersection and its two labels.
- **The hero fabricates no document content.** A fragment shows its filename,
  its body as abstract rules, and only the surviving fact as real text.

## Still open

- The remainder of the storyboard (Acts 2+) was requested but the paste came
  through as a duplicate of Act 1. Later acts may argue for a fifth beat.
- The 2026-08-08 iteration beats (SiteWise not tiring of scale; tender
  evaluation as the payoff) still have no home. The tender-comparison claim
  broadened to consultants + contractors + trades remains **unverified** and is
  not on this page.
- The 2026-08-12 five-chapter film landing remains the intended eventual
  replacement; `feature/landing-film` holds the shell.
