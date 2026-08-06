# Sitewise design system

Drop-in package for `frontend/public/style-guide`. Everything the brand
needs to be implemented rather than described.

```
style-guide/
├── tokens.css          palette, type ramp, spacing, motion, light values
├── tokens.json         the same values, machine-readable
├── light.css           the light system as a reusable layer
├── motion.css          reveals, transitions, easing application
├── logo/
│   ├── mark.svg        full colour, flat projection of the 3D master
│   ├── mark-mono.svg   one colour, inherits currentColor
│   ├── mark-solid.svg  filled variant for small sizes
│   └── favicon.svg     64px, on the void background
└── 3d/
    ├── mark.js         geometry, materials, lighting rig, camera presets
    └── lighting.json   the rig as data, with its regression figures
```

## Install

```html
<link rel="stylesheet" href="/style-guide/tokens.css">
<link rel="stylesheet" href="/style-guide/light.css">
<link rel="stylesheet" href="/style-guide/motion.css">
<link rel="icon" href="/style-guide/logo/favicon.svg">
```

`tokens.css` must load first — the other two read its custom properties.

Mount the light layers as the first children of your app root, in order:

```html
<div class="sw-light-sun"></div>
<div class="sw-light-key"></div>
<div class="sw-light-vignette"></div>
<div class="sw-grain"></div>
```

Then start the damped pointer loop (the snippet is in `light.css`, in the
comment under the key layer). Without it the key sits at its default
position and never moves — which is a valid static fallback.

## The one rule

Elevation is luminance, never a drop shadow. A raised surface gets a
brighter top edge; the shadow does not grow. Two elevation levels exist.
If you find yourself reaching for a third, the layout is the problem.

The four light behaviours, in the order light actually does them:
falloff (no hard terminator, blur never under 30px), contact (tight and
opaque where surfaces meet), bounce (saturated surfaces bleed their hue
onto neighbours at 8% or less — blue bounces, grey does not), and
specular edge (only the edge facing the key catches highlight).

## Typography

The specified face is **Söhne** with **Söhne Mono**, licensed from Klim
Type Foundry. Neither is in this package; buy the licence and self-host,
then the stack in `tokens.css` picks them up with no other change. Until
then it falls back to Hanken Grotesk and IBM Plex Mono, which are close
but noticeably softer than the wordmark.

The wordmark itself is **not** in this package. It cannot be reproduced
faithfully without the original face — supply the source artwork or the
font and it can be added as a proper lockup.

## The mark

`logo/mark.svg` is the flat projection of the 3D master, not a separate
drawing. Its geometry is exact: the isometric projection of a 1m cube
with two faces removed, so the flat and dimensional versions can never
drift apart.

Five regions, four of them filled. The upper-left triangle is empty by
design — that is the open corner. Do not fill it.

**Clear space** equal to one third of the mark's height on all sides.
**Minimum size** 96px for `mark.svg`; below that the open corner closes
up visually and you should switch to `mark-solid.svg`, which holds down
to 24px. `mark-mono.svg` inherits `currentColor` for single-ink print,
embossing and engraving.

Never rotate, recolour, stretch, or fill the open corner.

## The 3D master

`3d/mark.js` is the source of truth for the object itself. It exports
the geometry, the materials, the lighting rig and the four approved
camera positions, and it takes your `THREE` namespace so it does not pin
a version. Verified against r184.

```js
import { buildMark, applyLighting, frameCamera } from '/style-guide/3d/mark.js';

const mark = buildMark(THREE);
applyLighting(THREE, scene, renderer);
scene.add(mark);
frameCamera(THREE, camera, controls, 'logo');
```

**Logo lock** is the render master — near-orthographic at 9° field of
view, which reproduces the flat artwork exactly. Use it for any still
that stands in for the logo. The other three presets are for context.

One trap worth knowing about, documented in `lighting.json`: directional
and hemisphere light both deliver constant irradiance across a flat
face, so no amount of either can stop a plane reading as one flat tone.
The key is a point source with inverse-square falloff sitting just
outside the open corner. If you re-light this object and the faces go
flat, that is why. `lighting.json` carries the measured luminance
spreads to check a change against.

## What is still missing

- The wordmark, and the licensed font it is set in.
- An icon set built on the mark's 30° geometry.
- A contrast matrix for the palette against WCAG AA.
- Imagery direction — specifiable, but it needs real photography.
