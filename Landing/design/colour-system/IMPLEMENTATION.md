# SiteWise colour implementation

8 September 2026 · Current tokens v1.1.0 · Implemented locally; not deployed

The approved Chalk, Air & Citron system is integrated into the React application and existing landing page. A separate implementation agent handled the app and delegated the landing work; the parent agent independently reviewed the source changes and browser output. No Impeccable skill was used.

## Implemented

- Shared OKLCH/HEX masters feed the public stylesheet, browser JavaScript, TypeScript constants, published JSON, pre-paint theme bootstrap and favicon through `frontend/scripts/sync-colour-tokens.mjs`.
- The existing application theme bridge now separates Citron actions, cyan evidence/selection, green success, amber unresolved attention and red errors. Both themes retain the prescribed text, surface, input and control-border pairs.
- Shared buttons, inputs, badges, workflow indicators, document selection, links and custom chat controls use the appropriate roles. Enabled repository delete icons no longer multiply opacity reductions. Disabled primary controls use explicit opaque tokens.
- Keyboard focus uses one 2px outline with a 3px offset, without a duplicate Tailwind ring.
- Landing-page calls to action, selected sources, cost tables, programme marks, procurement documents and local tablet themes consume the shared palette. The outer marketing canvas stays light while the tablet switches independently.
- Current S and wordmark silhouettes are preserved by CSS masks using existing image alpha. The generated favicon embeds the existing S image and applies Petrol/Air. Original logo images are unchanged.
- Browser-side cadastral and 3D material colour inputs use the approved families. Blender files and GLB source assets are unchanged.
- The Docker frontend builder explicitly copies the two required master colour files before its build step, so generation has the same inputs as local development.

## v1.1.0 near-black revision — 8 September 2026

Following review, broad dark-mode surfaces now use seven zero-chroma charcoal primitives. Basalt stays in brand/light-mode roles. The tablet frame now uses neutral charcoal; its dark workspace uses canvas `#0A0A0A`, with navigation, repository and console panels on surface `#171717`. Light mode, brand/accent colours, status families and all eight chart-series colours are unchanged.

| Dark surface | v1.0 HEX (previous implementation) | v1.1.0 HEX (current master) |
|---|---|---|
| Canvas / inset / input | `#1F1915` | `#0A0A0A` |
| Panel / chart surface / focus gap | `#2C241E` | `#171717` |
| Elevated / hover / disabled background | `#3C332D` | `#222222` |

Pressed surfaces, decorative map lines, chart grids and boundaries also use the new gray roles. The [colour specification](<D:/AI Projects/clerk/Landing/design/colour-system/COLOUR-SYSTEM.md>) contains every current mapping and the revised contrast ratios.

| Current revision check | Status |
|---|---|
| Prescribed master contrast pairs | Pass: all 116 in HEX and OKLCH |
| Canonical export sync / check | Pass: all six generated outputs current |
| Typecheck and lint | Pass |
| Focused theme tests | Pass: 3 suites / 15 tests (application theme, theme button, landing tablet theme) |
| Production build | Pass, including bundle limits; Node 22.20.0 / pnpm 11.5.2 |
| Browser review | Pass: near-black app canvas, charcoal panels, nested dark tablet, unchanged light theme and matching browser theme colour |

The current build measured 245,663 bytes gzip for the initial cockpit and 16,809 bytes for the tender workflow, within their existing limits. Browser-computed dark values match the new zero-chroma masters. The light canvas and surface still resolve to the original Chalk values; the original dark preference was restored after the theme-switch check.

## v1.0 verification — earlier on 8 September 2026

The following records the completed initial integration, before the near-black revision; it is not a rerun against v1.1.0.

| Check | Result |
|---|---|
| Declared toolchain | Node 22.20.0; pnpm 11.5.2 |
| `pnpm colours:check` | Pass: all six generated outputs match the masters |
| `pnpm typecheck` | Pass |
| `pnpm lint` | Pass |
| Focused Vitest suites | Pass: 11 suites, 173 tests |
| `pnpm build` | Pass, including enforced bundle limits |
| Prescribed master contrast pairs | 116 passed in HEX and OKLCH for v1.0 |
| Browser: application | Light/dark workbench, selected evidence, live project PMP, home input and disabled action checked |
| Browser: keyboard focus | Single 2px outline, 3px offset, no duplicate visible ring |
| Browser: landing | Hero, both tablet themes, cost, programme and procurement results checked |
| Browser: mobile landing | 390px viewport; 375px content/scroll width, no horizontal overflow |
| Browser: identity | Existing lockup silhouettes and generated favicon render correctly |

The focused tests cover application theme behaviour, theme switching, workspace-file rendering, Markdown provenance, Gantt and repository behaviour, plus landing theme, composition, controls, programme/PMP and procurement surfaces. Tests used `pnpm exec node node_modules/vitest/vitest.mjs run …` because the Vitest command shim was unavailable in the local environment. No dependency versions were changed.

The v1.0 initial cockpit bundle measured 245,672 bytes gzip against a 256,000-byte limit; the tender bundle is 16,814 bytes against a 153,600-byte limit. The build retains an existing large-chunk advisory for the separate Three.js style-genome demo. See [build log](<D:/AI Projects/clerk/Landing/design/colour-system/audit/implementation-build.log>).

## v1.0 browser measurements — earlier on 8 September 2026

These controls were measured against the previous dark grounds. Their recorded action, text and focus colours remain unchanged; v1.1.0 surface validation is tracked separately above.

| Rendered control | Verified values |
|---|---|
| Light Create PMP | Foreground `oklch(0.220 0.012 58)`; fill `oklch(0.883 0.109 109)`; border `oklch(0.447 0.075 107)`; opacity 1 |
| Dark Create PMP | Same foreground; fill and border `oklch(0.822 0.125 109)`; opacity 1 |
| Light disabled Create project | Foreground `oklch(0.470 0.018 65)`; fill `oklch(0.948 0.010 85)`; opacity 1 |
| Light project-title input | Foreground `oklch(0.267 0.016 58)`; fill `oklch(0.992 0.003 85)`; border `oklch(0.600 0.020 70)` |
| Dark focus outline | `oklch(0.816 0.064 215)`, solid 2px, offset 3px |

The signed-in browser redirected `/login` to the home page, so the existing user session was preserved and the home form was reviewed instead. Browser review did not submit forms, create projects or change project content. The original dark preference was restored after checks.

## Maintenance and remaining boundaries

Change the masters with `Landing/design/colour-system/build_colour_system.py`, regenerate them, then run `pnpm colours:sync` in `frontend`. `predev` and `prebuild` also synchronise the exports. Use `pnpm colours:check` to detect drift. Consume semantic roles inside components; do not edit generated exports independently.

The changes are ready for review in the local application and have not been committed or deployed. The Docker copy path was reviewed, but a full Docker image build was not run. This work does not claim a complete WCAG audit of every application route. New chart compositions, photographic backgrounds and transparent 3D renders still require checks against their actual adjacent pixels. Blender lighting/material integration remains the next separate visual checkpoint.
