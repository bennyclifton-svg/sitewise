# SiteWise film — procedural clips

Remotion compositions for the parts of the launch film that are better computed
than generated. Currently: **clip 4, the light ring burst.**

Everything here renders deterministically, so you can re-render at any length,
resolution or colour without spending a generation.

## Setup

```bash
npm install
```

## Preview and tune

```bash
npm run studio
```

Opens the Remotion Studio at **`localhost:3999`**. The port is pinned because
Remotion defaults to 3000, which the `bidwright-launcher-web-1` Docker container
already owns on this machine — leaving it unpinned means Remotion silently
picks a different port each time and you end up looking at Bidwright instead.

Scrub the timeline,
and edit the props in the right-hand panel to retune the burst live — every
value in `ringBurstDefaults` is exposed:

| Prop | Does what |
|---|---|
| `overshoot` | How far past the frame corners the shell travels. `1.0` stops exactly at the corners. |
| `ease` | Deceleration strength. `1` is linear; higher starts faster and slows harder. `2.6` matches the reference. |
| `strokeStart` / `strokeEnd` | Core stroke width in px at the start and end of the expansion. |
| `halo` | Halo width as a multiple of the core stroke. |
| `haloGain` | Halo brightness relative to the core. |
| `falloff` | How much the shell dims as it spreads. `0` never dims. |

Changes in the studio are preview-only. To make one permanent, edit
`ringBurstDefaults` in `src/RingBurst.tsx`.

## Render

```bash
npm run render          # out/ring-burst.mp4       — pure black, for Screen blend
npm run render:wipe     # out/ring-wipe-bone.mp4   — the 1.6s wipe to bone
npm run render:alpha    # out/ring-burst-alpha.mov — ProRes 4444 with real alpha
npm run still           # out/ring-burst.png       — single frame, for checking
```

## Clip 3 — flying icons

`FlyingIcons`, 7s. Icons arrive oversized and close to the lens, recede into
place at their own scales and positions, hold for ~1.4s, then rise together and
leave the top of frame.

Source icons live in `public/icons/` (240×240 RGBA, stroked `#98C3EF`). Add a
PNG there and add its name to the `ICONS` array in `src/FlyingIcons.tsx`.

Layout is **seeded** — random-looking but identical on every render. Change
`seed` to any other string to reshuffle, then it stays put. Placement uses a
jittered 5×3 grid rather than random scatter, so coverage stays even, and cells
overlapping the central safe zone are dropped so a headline can sit over the
top. Set `safeWidth`/`safeHeight` to `0` to fill the whole frame.

### Tuning it yourself

Two places, depending on what you want to change.

**In the studio** — the right-hand props panel, for anything affecting all
icons at once. Changes preview instantly; "Update default props" writes them
back into the code.

| Prop | Does what |
|---|---|
| `baseSize` | Overall size. Everything scales from this. |
| `minScale` / `maxScale` | The size range, as multiples of `baseSize`. |
| `scaleBias` | Where sizes land in that range. `1` is even; above `1` puts more icons at the small end and leaves a few large, which reads as depth. |
| `startScaleMin` / `startScaleMax` | How oversized they arrive. |
| `flyInFrames` / `stagger` | Arrival speed, and the gap between icons. |
| `riseStart` / `riseFrames` / `riseDistance` | When the exit begins, how long, how far. |
| `safeWidth` / `safeHeight` | The central clear zone. Set both to `0` to fill the frame. |
| `showTile` | The rounded-square container behind each icon. |
| `seed` | Any other string reshuffles every position and size at once. |

**In `src/FlyingIcons.tsx`** — the `ICONS` table at the top, for one specific
icon. Saving hot-reloads the studio, so the loop is just as fast.

```ts
{name: 'cube'}                          // seeded size and position
{name: 'cube', scale: 0.45}             // pin the size only
{name: 'cube', x: 0.12, y: 0.8}         // pin the position only
{name: 'cube', scale: 1.9, x: 0.5}      // pin size and horizontal, seed the rest
```

`scale` is a multiple of `baseSize`. `x` and `y` are fractions of the frame —
`0` is the left or top edge, `1` the right or bottom, `0.5` dead centre.

Pinned positions are **not** clamped to the frame, so `x: 0.02` or `x: 1.05`
will crop an icon against the edge deliberately, the way the reference does.
Pinning an icon also frees its grid slot, so the others still spread evenly.

## Profile page populating

`ProfilePopulate`, 9s. The identity fields (name, address, client, state,
budget, scale) are simply **present** — they are not animated. Only the
decisions animate, because the point of the shot is that the agent is choosing,
not typing.

**1. The three selections.** For CLASS, WORK TYPE and SUBCLASS the highlight
races through *every* option twice before settling, so the viewer sees the size
of the choice being made. Each then lifts off at 2.6x, hovers, and is thrown
out of frame in its own direction — class up-left, work type up, subclass
up-right — reaching 6.5x as it goes.

**2. Complexity.** Each of the ten dropdowns riffles through three real
alternatives and lands on its answer, ringed in blue while it decides. No
lift-off here: ten fields flying at once was the clutter.

The option lists are the real ones from
`data/taxonomy/complexity-dimensions.json` — Planning has 4, Procurement route
6, Bushfire exposure 7, and so on. Edit `COMPLEXITY` in
`src/ProfilePopulate.tsx` to change which option each lands on (`pick` is an
index into that dimension's own `options`).

**3. Scope.** 39 blue ticks fly in from off-axis and land in their boxes —
7 panel headers plus the 32 selected items. Positions were found by clustering
the screenshot's blue pixels, so each lands exactly on its box.

Then a hold, and the page rushes past the lens.

### Source and the two kinds of hiding

`public/profile-full.png` is "1.1 Profile A" and "B" stitched into one
1311x1106 page, aligned by correlation at **dx=7, dy=406** and joined at the gap
below the SUBCLASS/SCALE/COMPLEXITY row.

Values are hidden by covering them in their own field's background colour, and
there are two cases — mixing them up is the easy mistake:

- **Absent data** — the cover clears on cue, revealing what the capture holds.
- **Wrong data** — the capture still reads "Not stated" across the complexity
  column, so those covers **never clear** and the values are drawn as live text
  on top. Let such a cover fade and the stale text shows through underneath.

Selection states are a third case: "unselected" is a different look rather than
an absence, so the chips and the radio are drawn unselected on top and revealed
when the race lands.

Props: `heroHoverScale`, `heroFlyScale`, `heroHoverFrames`, `complexityStart`,
`complexityStagger`, `scopeStart`, `scopeStagger`, `flyStart`, `flyScale`,
`transparent`.

## Compositions

Five are registered:

| Id | What it is | How you use it |
|---|---|---|
| `RingBurst` | 5s shell that swells and dies away, on pure black | Screen-blend over any beat |
| `RingWipeToBone` | 1.6s shell that fills bone behind itself | A hard cut point — the frame is fully `#FEFCF5` by frame 30 |
| `RingBurstAlpha` | `RingBurst` with a real alpha channel | Only if your CapCut build reads ProRes 4444 |
| `FlyingIcons` | 7s icon arrival, settle and rise, on `#060608` | Screen-blend, or use as a base layer |
| `FlyingIconsAlpha` | The same with a real alpha channel | For compositing over a light ground |
| `ProfilePopulate` | 6s form filling itself, then rushing past the lens | Use whole; it is a self-contained beat |
| `ProfilePopulateAlpha` | The same with a real alpha channel | To put your own ground behind it |

`RingWipeToBone` is the transition the reference actually uses at 12.8s and
39.5s, where the burst hands the frame over to the light ground rather than
fading out. To wipe the other way, change `wipeTo` to `#060608`.

Override duration or size without editing anything:

```bash
npx remotion render RingBurst out/ring-burst-3s.mp4 --frames=0-89
```

## Using it in CapCut

Import `ring-burst.mp4`, drop it on a track **above** the beat it transitions,
and set that clip's blend mode to **Screen**. Pure black is transparent under
Screen, so only the light survives. Nothing else is needed — no masking, no
keying, no alpha.

### Alpha renders

Use **MOV + ProRes 4444 + pixel format `yuva444p10le` + image format PNG**.
All four are needed; ProRes 4444 without the pixel format silently encodes
opaque, which is easy to miss.

WebM does **not** work in this Remotion build — VP8 and VP9 both ignore
`--pixel-format=yuva420p` and encode `yuv420p`. Verified by probing the output,
so don't reach for WebM expecting transparency.

Whether CapCut on Windows honours ProRes alpha is a separate question from
whether the file has it. If it flattens to black, fall back to the opaque MP4
with a **Screen** blend — for light artwork on a dark ground the result is
identical, and for glows it composites better than alpha does anyway.

## Why this clip is computed, not generated

A ring burst is pure maths: one radius, one easing curve, one colour ramp.
Seedance would give you a single unrepeatable take with an unpredictable number
of rings. This gives an exact, re-renderable result for free, and the black is
genuinely `#000000` rather than nearly black — which is what makes the Screen
blend clean.
