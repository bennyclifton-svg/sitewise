# Landing film — design

**Date:** 2026-08-12  
**Surface:** `frontend/public/landing.html` (Persuade)  
**Status:** Validated with product owner; ready for implementation planning

## Decision

Replace the current Mark 3 / production-line landing entirely with the Claude Design handoff in `frontend/assets/design_handoff_sitewise_films`, scoped as the **full five-chapter** experience from `Sitewise Landing.dc.html` over the **106s full film**.

## Host architecture

- Keep the **standalone static** route at `/landing.html` (outside the React SPA).
- Do **not** move the landing into React/R3F for v1.
- Faithful static port: adapt handoff modules into `frontend/public/`, rewrite Design Component runtime as plain ES modules.

## Page structure

1. Fixed nav — mark, Product mega-menu, Pricing, Get a Demo, Log In, Sign Up
2. 500vh scroll track with sticky full-viewport film stage
3. Dual cube canvases (Invoice-era kit → Transmittal-era kit) with crossfade ~40s film time
4. Left copy overlays per chapter; scroll dots; progress; post-hold “Scroll” hint
5. “Get started” CTA section
6. Minimal footer

## Motion contract

Scroll **selects** a chapter; the chapter **plays on its authored clock** and holds. Do not scrub film time from scroll position.

Chapter cuts (film seconds):

| Index | Range | Hold loop |
| --- | --- | --- |
| 0 | 0 – 13.9 | [13.1, 13.9] |
| 1 | 13.9 – 39.4 | — |
| 2 | 39.4 – 48.9 | [48.1, 48.9] |
| 3 | 48.9 – 69.6 | — |
| 4 | 69.6 – 106 | — |

Fidelity: camera paths, easing, canvas screen layouts, and timing stay exact from the handoff. Only structure/tooling adapts.

## Module port map

| Handoff | Production |
| --- | --- |
| `style-guide/3d/film-stage.js` + screens/composer/surfaces/cube-geometry | `frontend/public/style-guide/3d/` |
| `transmittal-stage.js` + `transmittal-screens.js` | same |
| `profile-screens.js`, `reveal.js`, lighting | same |
| Landing DC chapter clock | `frontend/public/landing-assets/film/chapter-clock.js` |
| `Sitewise Landing.dc.html` markup | `frontend/public/landing.html` (semantic HTML + CSS classes) |
| Logo / tokens | sync into existing `frontend/public/style-guide/` |

Retire facet landing: `sitewise-hero.js` and production-line-only CSS/sections once unused.

Three.js: verify film modules against pinned CDN version; bump from `0.180.0` toward handoff expectation (~r184) if lighting/faces break.

## Content & CTAs

- Keep handoff headlines; fix mega-menu typos to real product language.
- Sign Up / Log In → `/login`.
- Get a Demo / Pricing: real destinations when known; otherwise in-page stubs — no fake tours.
- No invented metrics, customers, or testimonials.

## Fallbacks

- `prefers-reduced-motion`: still frames + readable copy + CTA; no autoplaying chapter clocks.
- WebGL failure: static mark + copy + CTA.
- Mobile (&lt;900px): chapter scroll retained; mega-menu simplified; primary actions must not require hover.

## Out of scope (v1)

- Separate style-guide site
- Standalone full-film player page
- React / R3F migration

## Finish criteria

1. Desktop: five chapters play/hold with correct cuts; dual-cube crossfade clean
2. Reduced-motion and no-WebGL paths usable
3. Mobile: nav + CTA work; stage does not block scroll
4. Old facet assets unused by the route
5. Surface brief rewritten for this film landing; DESIGN.md updated at finish if the public face shifts
