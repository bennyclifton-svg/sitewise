# SiteWise — Chalk, Air & Citron

Version 1.1.0 · 8 September 2026 · Colour specification and implementation handoff

This system translates the supplied graphic into a warm, architectural identity for SiteWise: **Basalt establishes authority, Chalk carries information, Air establishes the project context, Petrol reveals detail, and Citron invites action.** It serves both the animated development model and the dense application used to coordinate evidence, consultants, decisions and delivery.

Revision 1.1.0 responds to the dark UI feeling too brown: its canvas is now `#0A0A0A`, panels `#171717` and elevated surfaces `#222222`. Basalt remains a brand and light-mode colour. Light mode, accents, status families and chart-series colours are unchanged.

The system is implemented in the application and landing-page source, including both themes. These changes have not been deployed; Blender materials remain a separate visual checkpoint. The authoritative values are in [sitewise-colours.json](<D:/AI Projects/clerk/Landing/design/colour-system/sitewise-colours.json>); [sitewise-colours.css](<D:/AI Projects/clerk/Landing/design/colour-system/sitewise-colours.css>) provides the corresponding CSS custom properties. Regenerate masters with [build_colour_system.py](<D:/AI Projects/clerk/Landing/design/colour-system/build_colour_system.py>), then run `pnpm colours:sync` in `frontend` to publish the application exports. See [implementation verification](<D:/AI Projects/clerk/Landing/design/colour-system/IMPLEMENTATION.md>) for scope and checks.

## A. Reference analysis and direction

The reference works through a small number of relationships: warm brown-black against pale blue; a yellow-green accent against that darkness; and white space separating large, confident fields. The blue is airy rather than electric. The yellow is softened rather than fluorescent. Warm darkness prevents the composition from feeling cold or clinical.

Approximate photographic samples are charcoal `#2A231D`, cyan `#97CCDC` and citron `#DDDD87`. These are readings from a photographed reproduction, affected by lighting, shadows and compression; they are not claims about the source brand's original specifications. The SiteWise masters below deliberately regularise those samples into a usable system.

Keep the reference's restraint and warm/cool relationship. For SiteWise, the strongest visual subject remains the actual building and its site. Keep the source graphic's red photography, dotted typography, logos and ornamental shapes outside the colour specification.

| SiteWise colour | Master | Role | Main uses |
|---|---|---|---|
| Basalt | `neutral-900` · `#2C241E` | Primary identity neutral | Light-mode headings/actions, brand treatments |
| Chalk | `neutral-50` · `#F9F7F3` | Light atmosphere | Reading canvas, architectural model, quiet copy panels |
| Air | `cyan-300` · `#93CEDD` | Supporting brand colour | Site landscape, broad marketing fields, dark-mode links |
| Petrol | `cyan-700` · `#12606D` | Functional cyan | Light-mode links, selected systems against chalk, interactive boundaries |
| Citron | `citron-400` · `#DEDF88` | Action accent | Primary CTA, a deliberate point of emphasis |

## B. Hierarchy and perceptual rules

**Dense application:** aim for at least 95% neutral or quiet surfaces, with saturated brand accents occupying no more than about **5% of the viewport**. A primary action gets Citron; links, selection and information use the appropriate cyan role. Tables should be readable before colour is noticed. This is an art-direction guideline, not a pixel-count algorithm or a reason to suppress necessary alerts and data.

**Marketing:** allow up to about **10% concentrated brand accent**, with pale atmospheric cyan/citron fields covering roughly **25–35% of the hero** where useful. Basalt remains available for deliberate brand panels; broad dark-mode application surfaces use near-black charcoal. The pale landscape and a small Citron CTA perform different jobs; do not count them as interchangeable emphasis.

**Perceptual adjacency:** assess colours at their actual size, beside their actual neighbours. Air against Basalt looks more luminous than Air against Chalk. A white building on a blue site needs stronger local edges than an isolated white swatch. Give small coloured marks more contrast and physical size; avoid compensating with glow. Separate adjoining chart segments with the chart-surface colour when their difference is insufficient.

**Light and dark adaptation:** dark mode raises the lightness of text, links and chart marks; it does not invert every colour. Keep broad dark surfaces achromatic and near-black; retain the warm light-mode neutrals and readable warm text. Reserve cool cyan for information and project context, and use the warm Citron accent sparingly. Judge both modes after allowing the screen's overall brightness to settle; review a realistic table and a hero crop as well as swatches.

The ramps use OKLCH to control lightness, chroma and hue independently. It is the polar form of Oklab, whose D65 basis and perceptual design make it suitable for constructing these relationships. The values are design coordinates, not accessibility scores. [Björn Ottosson's Oklab reference](https://bottosson.github.io/posts/oklab/)

## C. Primitive palette

All values are exact exports from the current masters. `L` is on the 0–1 scale, `C` is chroma and `h` is degrees. HEX values are rounded 8-bit sRGB fallbacks; modern CSS uses the listed OKLCH values. The generator reduces out-of-gamut chroma while preserving lightness and hue, and records those reductions in JSON. The warm neutral, achromatic charcoal, cyan and citron ramps below require no gamut reduction.

### Warm neutral ramp — 12 steps

| Primitive | HEX | Exact OKLCH |
|---|---|---|
| `neutral-0` | `#FDFCFA` | `oklch(0.9920 0.003000 85)` |
| `neutral-50` | `#F9F7F3` | `oklch(0.9760 0.006000 85)` |
| `neutral-100` | `#F1EDE6` | `oklch(0.9480 0.010000 85)` |
| `neutral-200` | `#E2DDD4` | `oklch(0.9000 0.014000 85)` |
| `neutral-300` | `#CFC8BD` | `oklch(0.8350 0.017000 80)` |
| `neutral-400` | `#AFA69B` | `oklch(0.7300 0.019000 75)` |
| `neutral-500` | `#887E74` | `oklch(0.6000 0.020000 70)` |
| `neutral-600` | `#625950` | `oklch(0.4700 0.018000 65)` |
| `neutral-700` | `#504740` | `oklch(0.4050 0.017000 60)` |
| `neutral-800` | `#3C332D` | `oklch(0.3300 0.016000 58)` |
| `neutral-900` | `#2C241E` | `oklch(0.2670 0.016000 58)` |
| `neutral-950` | `#1F1915` | `oklch(0.2200 0.012000 58)` |

The light end is close to paper, with `C = 0.003–0.014`; it therefore remains useful over large reading surfaces. Chroma reaches only `0.020` in the middle and falls again in the darkest steps. Hue moves gradually from `85°` at the pale end to `58°` in Basalt, giving highlights a chalk tone and shadows a brown-charcoal tone. The deliberately uneven lightness spacing allocates more differentiation to text and surfaces rather than forcing every numbered step to be equally spaced.

### Achromatic charcoal — dark UI surfaces

| Primitive | HEX | Exact OKLCH |
|---|---|---|
| `charcoal-950` | `#0A0A0A` | `oklch(0.1450 0.000000 0)` |
| `charcoal-900` | `#171717` | `oklch(0.2050 0.000000 0)` |
| `charcoal-800` | `#222222` | `oklch(0.2500 0.000000 0)` |
| `charcoal-700` | `#2B2B2B` | `oklch(0.2900 0.000000 0)` |
| `charcoal-600` | `#3A3A3A` | `oklch(0.3500 0.000000 0)` |
| `charcoal-500` | `#808080` | `oklch(0.6000 0.000000 0)` |
| `charcoal-400` | `#A8A8A8` | `oklch(0.7300 0.000000 0)` |

All seven steps have zero chroma, so their hue coordinate is immaterial. The darkest three establish canvas, panel and elevation without a brown cast; the lighter steps provide gray boundaries. These supplement the warm neutral ramp rather than replacing its brand, light-mode or text roles.

### Cyan ramp — 11 steps

| Primitive | HEX | Exact OKLCH |
|---|---|---|
| `cyan-50` | `#EEF9FC` | `oklch(0.9740 0.012000 215)` |
| `cyan-100` | `#D8F0F7` | `oklch(0.9400 0.027000 215)` |
| `cyan-200` | `#BAE1EC` | `oklch(0.8860 0.044000 215)` |
| `cyan-300` | `#93CEDD` | `oklch(0.8160 0.064000 215)` |
| `cyan-400` | `#6BBACC` | `oklch(0.7440 0.082000 215)` |
| `cyan-500` | `#389FB4` | `oklch(0.6520 0.097000 214)` |
| `cyan-600` | `#1E7F92` | `oklch(0.5530 0.089000 214)` |
| `cyan-700` | `#12606D` | `oklch(0.4500 0.073000 213)` |
| `cyan-800` | `#15444D` | `oklch(0.3600 0.052000 213)` |
| `cyan-900` | `#152E33` | `oklch(0.2830 0.032000 213)` |
| `cyan-950` | `#0F1F22` | `oklch(0.2250 0.022000 213)` |

Lightness decreases monotonically from `0.974` to `0.225`. Chroma builds to `0.097` around `cyan-500`, then recedes towards the ends. Air at `300` supplies the reference's pale blue; Petrol at `700` provides its readable working counterpart. The tiny `215° → 213°` hue shift keeps the dark end coherent without drifting into navy or green. Do not use Air as small text on Chalk.

### Citron ramp — 11 steps

| Primitive | HEX | Exact OKLCH |
|---|---|---|
| `citron-50` | `#FAFAF0` | `oklch(0.9830 0.014000 109)` |
| `citron-100` | `#F5F6DD` | `oklch(0.9650 0.033000 109)` |
| `citron-200` | `#EFF0C3` | `oklch(0.9440 0.059000 109)` |
| `citron-300` | `#E8EAA9` | `oklch(0.9200 0.083000 109)` |
| `citron-400` | `#DEDF88` | `oklch(0.8830 0.109000 109)` |
| `citron-500` | `#CBCB66` | `oklch(0.8220 0.125000 109)` |
| `citron-600` | `#A9A745` | `oklch(0.7100 0.120000 108)` |
| `citron-700` | `#807E2C` | `oklch(0.5780 0.103000 108)` |
| `citron-800` | `#595721` | `oklch(0.4470 0.075000 107)` |
| `citron-900` | `#37361A` | `oklch(0.3280 0.045000 107)` |
| `citron-950` | `#232314` | `oklch(0.2500 0.025000 107)` |

Citron's highlight steps stay high in lightness, with the branded `400` at `L = 0.883`. Chroma peaks at `0.125` around `500`; the darker end becomes an olive family, reaching `C = 0.025` at `950`. The `109° → 107°` hue progression preserves the yellow-green character. Dark citron is available for a contrasting button boundary or specialist annotation; it is not a replacement for standard body text.

## D. Semantic tokens: light and dark

Components consume `--sw-<role>`; primitives are `--sw-p-<name>`. Use the semantic role instead of choosing an attractive ramp step inside each component. Each cell below shows the bound primitive and its exact HEX fallback.

### Surfaces, borders and text

| Semantic role (`--sw-…`) | Light mode | Dark mode |
|---|---|---|
| `canvas` | `neutral-50` · `#F9F7F3` | `charcoal-950` · `#0A0A0A` |
| `surface` | `neutral-0` · `#FDFCFA` | `charcoal-900` · `#171717` |
| `surface-elevated` | `neutral-0` · `#FDFCFA` | `charcoal-800` · `#222222` |
| `surface-inset` | `neutral-100` · `#F1EDE6` | `charcoal-950` · `#0A0A0A` |
| `border-subtle` | `neutral-100` · `#F1EDE6` | `charcoal-700` · `#2B2B2B` |
| `border-default` | `neutral-200` · `#E2DDD4` | `charcoal-600` · `#3A3A3A` |
| `border-strong` | `neutral-500` · `#887E74` | `charcoal-500` · `#808080` |
| `border-control` | `neutral-500` · `#887E74` | `charcoal-500` · `#808080` |
| `text-primary` | `neutral-900` · `#2C241E` | `neutral-100` · `#F1EDE6` |
| `text-secondary` | `neutral-700` · `#504740` | `neutral-300` · `#CFC8BD` |
| `text-tertiary` | `neutral-600` · `#625950` | `neutral-400` · `#AFA69B` |
| `text-inverse` | `neutral-50` · `#F9F7F3` | `neutral-950` · `#1F1915` |

`border-subtle` and `border-default` are quiet separators. Use `border-control` when the outline identifies an input or other control. `border-strong` also works for a deliberately important division. Do not rely on a decorative hairline to communicate selection, a required field or an error.

### Actions, links and selection

| Semantic role (`--sw-…`) | Light mode | Dark mode |
|---|---|---|
| `action-primary` | `citron-400` · `#DEDF88` | `citron-500` · `#CBCB66` |
| `action-primary-hover` | `citron-500` · `#CBCB66` | `citron-400` · `#DEDF88` |
| `action-primary-pressed` | `citron-600` · `#A9A745` | `citron-600` · `#A9A745` |
| `action-primary-text` | `neutral-950` · `#1F1915` | `neutral-950` · `#1F1915` |
| `action-primary-border` | `citron-800` · `#595721` | `citron-500` · `#CBCB66` |
| `action-secondary` | `neutral-900` · `#2C241E` | `neutral-100` · `#F1EDE6` |
| `action-secondary-hover` | `neutral-800` · `#3C332D` | `neutral-50` · `#F9F7F3` |
| `action-secondary-pressed` | `neutral-950` · `#1F1915` | `neutral-200` · `#E2DDD4` |
| `action-secondary-text` | `neutral-50` · `#F9F7F3` | `neutral-950` · `#1F1915` |
| `action-secondary-border` | `neutral-900` · `#2C241E` | `neutral-100` · `#F1EDE6` |
| `action-focus` | `cyan-700` · `#12606D` | `cyan-300` · `#93CEDD` |
| `action-focus-gap` | `neutral-0` · `#FDFCFA` | `charcoal-900` · `#171717` |
| `action-disabled-bg` | `neutral-100` · `#F1EDE6` | `charcoal-800` · `#222222` |
| `action-disabled-text` | `neutral-600` · `#625950` | `neutral-400` · `#AFA69B` |
| `action-disabled-border` | `neutral-200` · `#E2DDD4` | `charcoal-600` · `#3A3A3A` |
| `link` | `cyan-700` · `#12606D` | `cyan-300` · `#93CEDD` |
| `link-hover` | `cyan-800` · `#15444D` | `cyan-200` · `#BAE1EC` |
| `selection-bg` | `cyan-100` · `#D8F0F7` | `cyan-900` · `#152E33` |
| `selection-border` | `cyan-600` · `#1E7F92` | `cyan-500` · `#389FB4` |
| `selection-text` | `cyan-800` · `#15444D` | `cyan-200` · `#BAE1EC` |
| `hover-bg` | `neutral-50` · `#F9F7F3` | `charcoal-800` · `#222222` |
| `pressed-bg` | `neutral-100` · `#F1EDE6` | `charcoal-700` · `#2B2B2B` |

Keep Citron button labels dark in every state. In light mode the olive `action-primary-border` defines the pale button against Chalk. A primary action and a selected record are different states: Citron asks the user to act; cyan shows what is selected or being inspected. Hover and pressed values provide feedback without adding another hue.

Use an offset focus ring: the supplied CSS uses a **2px outline with a 3px offset**. Keep the offset area the same colour as the actual surrounding surface; override `action-focus-gap` for nested surfaces when needed. Do not replace focus with a faint shadow. The contrast report tests ring colour against the supported surfaces, not a complete keyboard-focus implementation.

### Inputs and status

| Semantic role (`--sw-…`) | Light mode | Dark mode |
|---|---|---|
| `input-bg` | `neutral-0` · `#FDFCFA` | `charcoal-950` · `#0A0A0A` |
| `input-text` | `neutral-900` · `#2C241E` | `neutral-100` · `#F1EDE6` |
| `input-placeholder` | `neutral-600` · `#625950` | `neutral-400` · `#AFA69B` |

| Semantic role (`--sw-…`) | Light mode | Dark mode |
|---|---|---|
| `info-bg` | `cyan-50` · `#EEF9FC` | `cyan-900` · `#152E33` |
| `info-border` | `cyan-600` · `#1E7F92` | `cyan-500` · `#389FB4` |
| `info-text` | `cyan-800` · `#15444D` | `cyan-200` · `#BAE1EC` |
| `info-icon` | `cyan-700` · `#12606D` | `cyan-300` · `#93CEDD` |
| `success-bg` | `success-light-bg` · `#EBF9EF` | `success-dark-bg` · `#1F3126` |
| `success-border` | `success-light-border` · `#427D59` | `success-dark-border` · `#5DA076` |
| `success-text` | `success-light-text` · `#28593B` | `success-dark-text` · `#A6D7B6` |
| `success-icon` | `success-light-icon` · `#2D7149` | `success-dark-icon` · `#7EC798` |
| `warning-bg` | `warning-light-bg` · `#FFF3E0` | `warning-dark-bg` · `#392B1D` |
| `warning-border` | `warning-light-border` · `#9B641A` | `warning-dark-border` · `#CC943C` |
| `warning-text` | `warning-light-text` · `#6E4117` | `warning-dark-text` · `#F4D29B` |
| `warning-icon` | `warning-light-icon` · `#90561A` | `warning-dark-icon` · `#EBB553` |
| `error-bg` | `error-light-bg` · `#FFEFED` | `error-dark-bg` · `#3B2523` |
| `error-border` | `error-light-border` · `#B54B46` | `error-dark-border` · `#DD756E` |
| `error-text` | `error-light-text` · `#882F2D` | `error-dark-text` · `#EFC1BC` |
| `error-icon` | `error-light-icon` · `#AE3534` | `error-dark-icon` · `#F29B93` |
| `danger-bg` | `error-light-bg` · `#FFEFED` | `error-dark-bg` · `#3B2523` |
| `danger-border` | `error-light-border` · `#B54B46` | `error-dark-border` · `#DD756E` |
| `danger-text` | `error-light-text` · `#882F2D` | `error-dark-text` · `#EFC1BC` |
| `danger-icon` | `error-light-icon` · `#AE3534` | `error-dark-icon` · `#F29B93` |

| Meaning | Treatment | SiteWise examples |
|---|---|---|
| Information | Cyan + information/evidence icon + label | Source located; service selected; investigation context |
| Success | Green + check + label | Decision approved; package completed |
| Warning | Amber + warning triangle + label | Unresolved allowance; missing information; constraint requiring a decision |
| Error / danger | Red + error or destructive icon + label | Failed action; blocking error; deletion warning |
| Draft / unverified | Neutral base + explicit label; amber only where attention is needed | Draft consultant brief; illustrative utility route |

`danger-*` deliberately aliases the error family. These are semantic notification values, not a claim that every destructive action should become a filled red button. Keep the action label explicit. A draft is not successful merely because it exists; “ready to start” is not a warning merely because it awaits a click.

Status cannot be conveyed through hue alone. Retain visible labels, icons and relevant differences in shape or line treatment. A screen reader label does not replace the visible alternative needed by someone who cannot distinguish the colours. [W3C: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)

## E. Application recipes and limits

**Primary workflow:** Chalk canvas, slightly whiter document/card surface, Basalt text, Petrol links and one Citron primary action. A selected row receives cyan fill, a stronger cyan edge and a persistent selected marker. An unresolved item within that row retains its amber status badge: selection and risk can coexist.

**Dense tables:** use neutral alternating surfaces only where they improve scanning. Column headings, totals and negative amounts must remain understandable through wording, position and number formatting. Use red for an error or adverse status, not automatically for every negative numeric value. Keep chart category colours out of ordinary table chrome.

**Inputs:** use the input tokens with `border-control`; keep placeholder copy at full token colour. A disabled input uses explicit disabled tokens and native disabled semantics. Do not lower opacity on an entire container: it can wash out readable labels and create new, untested colour pairs.

**Links:** Petrol in light mode, Air in dark mode, with a visible underline in prose. Use the separate `link-hover` role, not the Citron button hover colour. Selected navigation remains cyan rather than becoming a status signal.

**Errors and confirmations:** pair the matching status surface, border, icon and text. Success green appears after the approved/completed state is real. Amber remains the unresolved-risk language in the product and the animation. Citron denotes action; it does not mean “risk resolved” or “compliant”.

## F. Data visualisation

Eight series are available for cost, programme and comparison views. Assign categories in a stable order within a project; retain the category-to-series mapping across filters and related charts. These hues are chart encodings, not discipline colours or workflow statuses. Use a status chart's semantic status palette when the categories themselves are approved/warning/failed.

| Semantic role (`--sw-…`) | Light mode | Dark mode |
|---|---|---|
| `chart-surface` | `neutral-0` · `#FDFCFA` | `charcoal-900` · `#171717` |
| `chart-grid` | `neutral-100` · `#F1EDE6` | `charcoal-700` · `#2B2B2B` |
| `chart-label` | `neutral-600` · `#625950` | `neutral-400` · `#AFA69B` |
| `chart-separator` | `neutral-0` · `#FDFCFA` | `charcoal-900` · `#171717` |

| Series / name | Light HEX · OKLCH | Dark HEX · OKLCH | Marker | Dash |
|---|---|---|---|---|
| 1 · Petrol | `#3C9EB3` · `oklch(0.6500 0.094600 215)` | `#B2EDFB` · `oklch(0.9100 0.062050 215)` | circle | `none` |
| 2 · Ochre | `#8B5D00` · `oklch(0.5150 0.108536 75)` | `#D89F49` · `oklch(0.7400 0.122100 75)` | square | `8 3` |
| 3 · Denim | `#004182` · `oklch(0.3800 0.125009 255)` | `#6B9CDB` · `oklch(0.6850 0.107000 255)` | triangle | `2 3` |
| 4 · Terracotta | `#771A00` · `oklch(0.3750 0.131418 35)` | `#B85B45` · `oklch(0.5800 0.125400 35)` | diamond | `10 3 2 3` |
| 5 · Evergreen | `#548465` · `oklch(0.5700 0.072250 155)` | `#93CEA7` · `oklch(0.8000 0.082450 155)` | plus | `5 3` |
| 6 · Mulberry | `#55274C` · `oklch(0.3500 0.086700 335)` | `#986D8E` · `oklch(0.5900 0.072250 335)` | cross | `12 4` |
| 7 · Olive | `#959643` · `oklch(0.6550 0.106700 110)` | `#E5E896` · `oklch(0.9100 0.103400 110)` | triangle-down | `2 2 8 2` |
| 8 · Graphite | `#5D554D` · `oklch(0.4550 0.016000 70)` | `#A29A90` · `oklch(0.6900 0.017000 70)` | hexagon | `12 3 3 3` |

Every series also has a distinct marker and dash pattern. The dash strings are SVG `stroke-dasharray` values in a common scale; `none` is solid. Preserve those differences in legends, tooltips and exports. Prefer direct labels at line ends. Bars can use category labels and patterns; stacked segments need a neutral separator. Chart marks use the data colours, while labels use `chart-label`: a colour that clears 3:1 as a mark is not automatically a 4.5:1 text colour.

### Colour-vision screening

The generator screens the final sRGB series with severity-100 protan, deutan and tritan simulation matrices, then measures the nearest pair in Oklab. This is an engineering diagnostic, not a certification that all users can distinguish eight colours. Colorspacious documents the simulation model and publishes the matrix implementation used as the reference here. [Colorspacious simulation guide](https://colorspacious.readthedocs.io/en/latest/tutorial.html#simulating-colorblindness), [reference matrices](https://github.com/njsmith/colorspacious/blob/master/colorspacious/cvd.py)

| Mode | Normal minimum ΔEOK | Protan minimum ΔEOK | Deutan minimum ΔEOK | Tritan minimum ΔEOK |
|---|---:|---:|---:|---:|
| light | 0.1102 (series 2/8) | 0.0938 (series 2/8) | 0.0942 (series 2/5) | 0.0984 (series 4/6) |
| dark | 0.1089 (series 4/6) | 0.1046 (series 5/7) | 0.1049 (series 2/5) | 0.1042 (series 4/6) |

`ΔEOK` is shown on the Oklab 0–1 coordinate scale, not multiplied by 100. There is no universal accessibility pass threshold applied here. The closest pairs vary with simulated vision; this is why shapes, dashes, direct labels and neutral separation remain required. The JSON records the three closest pairs for each mode and simulation, plus the simulated HEX values. Review actual charts in grayscale and at their intended size as well.

## G. Landing page, cadastral map and 3D

| Semantic role (`--sw-…`) | Light mode | Dark mode |
|---|---|---|
| `scene-ground` | `cyan-300` · `#93CEDD` | `cyan-900` · `#152E33` |
| `scene-building` | `neutral-50` · `#F9F7F3` | `neutral-100` · `#F1EDE6` |
| `scene-building-edge` | `neutral-500` · `#887E74` | `neutral-400` · `#AFA69B` |
| `scene-service-active` | `cyan-700` · `#12606D` | `cyan-700` · `#12606D` |
| `scene-service-inactive` | `neutral-400` · `#AFA69B` | `neutral-400` · `#AFA69B` |
| `scene-decision` | `warning-light-icon` · `#90561A` | `warning-light-icon` · `#90561A` |
| `map-line-decorative` | `neutral-300` · `#CFC8BD` | `charcoal-600` · `#3A3A3A` |
| `map-line-interactive` | `cyan-700` · `#12606D` | `cyan-300` · `#93CEDD` |
| `map-lot-selected` | `cyan-100` · `#D8F0F7` | `cyan-900` · `#152E33` |

The opening composition places the chalk development on an Air site field, with the adjoining copy area on Chalk. The dark tablet uses `canvas` (`#0A0A0A`) for its workspace and `surface` (`#171717`) for navigation, repository and console panels. Its frame uses achromatic charcoal with light highlights. The plan map and isometric map share the same lot geometry and selection. Quiet decorative boundaries can recede; interactive parcels and meaningful setbacks need the stronger map role, a label and a visible line convention.

Keep assembled walls, slabs, columns, roofs and fixtures recognisable. In a close-up, reveal the selected service through controlled translucency and restrained architectural edges. **The active service remains Petrol in both UI modes because it is seen against chalk building surfaces.** Dark-mode links and interactive map strokes become Air because their immediate backing is dark; that is a different adjacency. Do not globally invert the building's material palette when the application theme changes.

Amber decision markers remain distinct from Citron calls to action. The scene's dark amber is designed against the light building. If a marker moves onto a dark site field, give it a small opaque Chalk backing or use an appropriately tested dark-mode status treatment. A path on a dark field likewise needs a light local stroke or backing; the Petrol service token is intended for the architectural reveal, not every possible background.

Use the selected colour for whichever system is being inspected, rather than assigning an unrelated permanent colour to every trade. Distinguish an indicative route from an approved route with labels and line conventions; do not let a smooth animation imply verified design or compliance. Concrete and architectural materials stay neutral. Interior lighting may be softly warm, but should not tint the entire model yellow.

### One permitted atmospheric gradient

Use this gradient only in the marketing site's broad 3D/cadastral field. The angle, interpolation space and stops are fixed:

```css
background: linear-gradient(
  118deg in oklab,
  oklch(0.9760 0.006000 85) 0%,
  oklch(0.9400 0.027000 215) 54%,
  oklch(0.8160 0.064000 215) 100%
);
```

The stops are Chalk `#F9F7F3` → pale cyan `#D8F0F7` → Air `#93CEDD`. Use a solid Chalk fallback if the interpolation syntax is unavailable. Do not introduce a second gradient family. Dense application panels, forms, tables, status badges and buttons remain opaque. Keep readable copy on a neutral backing rather than relying on a convenient point in the gradient.

Use the same master colours for Blender and the browser, but respect the renderer's colour-space handling. Material values, illumination, exposure, transparency and tone mapping all affect rendered pixels. Check a lit close-up and a wide shot against the UI before finalising the film; the palette alone does not establish contrast in a shaded render.

## H. Contrast evidence and exceptions

**All 116 prescribed pair checks pass in both the rounded HEX export and the actual OKLCH master values.** This includes two disabled-text checks imposed as a house policy. The checks cover each theme's text/surface pairs, button states, control boundaries, offset focus colours, links, status treatments, selection, placeholders and eight chart series. They are token-pair checks, not a claim that the entire application meets WCAG AA.

The house minimum is **4.5:1 for normal text**, including links, button labels and placeholders. WCAG permits 3:1 for qualifying large text and exempts inactive components; this specification does not use the large-text relaxation for these checked text roles. [W3C: Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

Meaningful control outlines, state indicators and chart marks are checked at **3:1 against their specified adjacent surface**. That does not establish contrast between every pair of coloured chart series. Keep the provided separators and non-colour encodings where needed. [W3C: Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)

| Pair | HEX ratio | OKLCH ratio | Threshold |
|---|---:|---:|---:|
| light: `text-primary` / `canvas` | 14.24:1 | 14.24:1 | 4.5:1 |
| dark: `text-primary` / `canvas` | 16.97:1 | 17.00:1 | 4.5:1 |
| light: `text-tertiary` / `surface-inset` | 5.87:1 | 5.88:1 | 4.5:1 |
| dark: `text-tertiary` / `surface-elevated` | 6.63:1 | 6.68:1 | 4.5:1 |
| light: `action-primary-text` / `action-primary` | 12.43:1 | 12.37:1 | 4.5:1 |
| dark: `action-primary-text` / `action-primary` | 10.16:1 | 10.16:1 | 4.5:1 |
| light: `action-primary-text` / `action-primary-pressed` | 6.87:1 | 6.84:1 | 4.5:1 |
| light: `link` / `canvas` | 6.72:1 | 6.74:1 | 4.5:1 |
| dark: `link` / `surface-elevated` | 9.18:1 | 9.22:1 | 4.5:1 |
| light: `border-control` / `surface-inset` | 3.41:1 | 3.40:1 | 3:1 |
| dark: `border-control` / `surface-elevated` | 4.03:1 | 4.05:1 | 3:1 |
| light: `action-focus` / `surface-inset` | 6.16:1 | 6.21:1 | 3:1 |
| dark: `action-focus` / `surface-elevated` | 9.18:1 | 9.22:1 | 3:1 |
| light: `warning-text` / `warning-bg` | 7.88:1 | 7.89:1 | 4.5:1 |
| dark: `warning-text` / `warning-bg` | 9.46:1 | 9.51:1 | 4.5:1 |
| light: `action-disabled-text` / `action-disabled-bg` | 5.87:1 | 5.88:1 | 4.5:1 (house policy) |
| dark: `action-disabled-text` / `action-disabled-bg` | 6.63:1 | 6.68:1 | 4.5:1 (house policy) |
| light: weakest chart mark (`data-1` / `chart-surface`) | 3.04:1 | 3.06:1 | 3:1 |
| dark: weakest chart mark (`data-4` / `chart-surface`) | 3.94:1 | 3.96:1 | 3:1 |

Ratios above are displayed to two decimals; pass/fail uses unrounded numbers. [CONTRAST.md](<D:/AI Projects/clerk/Landing/design/colour-system/CONTRAST.md>) lists every checked HEX pair; JSON additionally records `ratioOKLCH`, the exact threshold and the result. Contrast is computed from linearised sRGB relative luminance, not directly from OKLCH lightness.

Intentional limits:

- `border-subtle`, `border-default`, chart grid lines and decorative cadastral lines may be below 3:1 because they are not the sole means of conveying necessary information. Upgrade to a functional border/line role when their information matters.
- Pale cyan and Citron are unsuitable as text on white or Chalk. Use Petrol, Basalt or the designated dark foreground instead. Citron controls need the specified dark label and, in light mode, their boundary treatment.
- Disabled controls are exempt under the relevant WCAG criteria, but the chosen disabled text still clears 4.5:1. Disabled borders are intentionally quiet; state also comes from the native control and its behaviour.
- Transparency, overlays, photographs, gradients, thin strokes and new combinations require a rendered review. Existing token results do not transfer automatically to arbitrary compositing.

## I. Implementation handoff

### Files and usage

| Deliverable | Purpose |
|---|---|
| [sitewise-colours.json](<D:/AI Projects/clerk/Landing/design/colour-system/sitewise-colours.json>) | Primitive masters, brand bindings, both themes, series markers/dashes, gradient, contrast and colour-vision diagnostics |
| [sitewise-colours.css](<D:/AI Projects/clerk/Landing/design/colour-system/sitewise-colours.css>) | HEX fallback, OKLCH feature override and semantic custom properties |
| [CONTRAST.md](<D:/AI Projects/clerk/Landing/design/colour-system/CONTRAST.md>) | Full human-readable HEX contrast ledger |
| [build_colour_system.py](<D:/AI Projects/clerk/Landing/design/colour-system/build_colour_system.py>) | Reproducible master-to-export generator and checks |

Illustrative component use after deliberate theme integration:

```css
.project-primary-action {
  background: var(--sw-action-primary);
  color: var(--sw-action-primary-text);
  border: 1px solid var(--sw-action-primary-border);
}
.project-primary-action:hover { background: var(--sw-action-primary-hover); }
.project-primary-action:active { background: var(--sw-action-primary-pressed); }
.project-primary-action:focus-visible {
  outline: 2px solid var(--sw-action-focus);
  outline-offset: 3px;
}
.project-primary-action:disabled {
  background: var(--sw-action-disabled-bg);
  color: var(--sw-action-disabled-text);
  border-color: var(--sw-action-disabled-border);
}
```

The export defaults to light and supplies `[data-theme="dark"]` overrides. The application retains its stored preference and dark default through its pre-paint bootstrap. The landing page has a light outer canvas and an independently switchable tablet. Application components consume the shared palette through the existing theme bridge; nested theme boundaries bind their own local aliases.

### Existing application integration

The integration seam is [frontend/src/index.css](<D:/AI Projects/clerk/frontend/src/index.css:10>): its cockpit roles feed product and shadcn components. The interface is preserved while actions, information, selection and status use separate semantic roles.

| Current contract | New semantic destination / action |
|---|---|
| `--cockpit-app-canvas`, workspace/card/nav surfaces | Map to canvas/surface/inset/elevated roles; keep meaningful elevation |
| `--text-primary`, muted/faint and `--cockpit-text-*` | Map to the three text levels; preserve dark-mode overrides |
| `--brand`, `--primary`, `--text-on-brand` | Map the complete primary action family, including dark label and border |
| `--brand-text`, `--info-*` | Keep links/information on cyan roles; do not inherit Citron action fills |
| `--cockpit-selected-*`, `--bg-active` | Map to cyan selection; maintain the indicator and label |
| `--brand-ring`, `--ring`, `--cockpit-focus` | Map to the focus role and actual surrounding surface |
| `--ok-*`, `--warn-*`, `--alert-*` | Map to green success, amber warning and red error families |
| `--decision-evidenced-*`, `--decision-assumed-*` | Keep evidence cyan; make assumptions explicit, using amber only when unresolved attention is intended |
| `--wf-ready-*` and workflow status helpers | Separate readiness from warning; stop presenting every draft as a successful result |

`--sw-facet-blue` and `--sw-beam` now resolve to the cyan link family for existing information consumers. Primary actions use the dedicated Citron action tokens. Keep this distinction when adding new components.

The shared public style-guide export, application theme bridge, landing themes and browser metadata now derive from the approved masters. Registered legacy colour defaults and conflicting light overrides were removed. Functional component literals and action/selection assumptions were migrated. The current S logo silhouette is preserved through CSS masking of the existing image assets; source images are unchanged. Historical logo experiments retain their own recorded palettes.

The implementation record distinguishes automated token checks, regression tests and browser checks. Continue reviewing actual composited output when adding screens, charts or transparency. The chalk/Petrol service reveal still needs its Blender lighting and material review; token contrast results alone cannot verify a shaded 3D render.
