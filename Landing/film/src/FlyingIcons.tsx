import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  random,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

/**
 * Clip 3 — flying icons.
 *
 * Icons arrive oversized and close to the lens, recede into place at their own
 * scales and positions, hold, then rise together and leave the top of frame.
 *
 * Layout is seeded, so it is random-looking but identical on every render —
 * change `seed` to reshuffle, and you get the same result every time after.
 * A central safe zone is kept clear so a headline can sit over the top.
 */

type IconSpec = {
  /** Filename in public/icons, without the .png */
  name: string;
  /**
   * Pin this icon's settle size, as a multiple of baseSize.
   * Omit and it takes a seeded random size between minScale and maxScale.
   */
  scale?: number;
  /**
   * Pin this icon's settle position as a fraction of the frame — 0 is the left
   * or top edge, 1 the right or bottom, 0.5 dead centre. Omit and it takes a
   * seeded slot on the grid. Pinned positions are deliberately NOT clamped, so
   * 0.02 or 1.05 will crop an icon against the frame edge on purpose.
   * You can pin just x, just y, or both.
   */
  x?: number;
  y?: number;
};

/**
 * EDIT THIS TABLE to hand-place or hand-size any icon. Anything you leave off
 * stays seeded-random. Add an icon by dropping a PNG in public/icons and
 * adding a line here. Saving the file hot-reloads the studio instantly.
 */
const ICONS: IconSpec[] = [
  {name: 'adjustments'},
  {name: 'clipboard'},
  {name: 'cube', scale: 0.45},
  {name: 'dollar'},
  {name: 'download', scale: 0.5},
  {name: 'folders'},
  {name: 'globe'},
  {name: 'message-dots'},
  {name: 'messages'},
  {name: 'microphone'},
  {name: 'send'},
];

export type FlyingIconsProps = {
  transparent: boolean;
  /** Change to reshuffle the layout. Any string. */
  seed: string;
  /** Settle size in px, before each icon's own random variation. */
  baseSize: number;
  /** Settle size varies between these multiples of baseSize. */
  minScale: number;
  maxScale: number;
  /**
   * Skews where sizes land inside that range. 1 is an even spread; above 1
   * pushes more icons toward the small end and leaves a few standouts large,
   * which reads as depth rather than as a clump of similar sizes.
   */
  scaleBias: number;
  /** How much larger than its settle size an icon starts. */
  startScaleMin: number;
  startScaleMax: number;
  /** Frames each icon takes to fly in, and the stagger between them. */
  flyInFrames: number;
  stagger: number;
  /** Frame at which the rise begins, and how long it takes. */
  riseStart: number;
  riseFrames: number;
  /** How far up the frame they travel on exit, as a fraction of frame height. */
  riseDistance: number;
  /** Central rectangle kept clear, as fractions of frame width and height. */
  safeWidth: number;
  safeHeight: number;
  /** Peak opacity of a settled icon. */
  opacity: number;
  /** Draw the reference's rounded-square container behind each icon. */
  showTile: boolean;
};

export const flyingIconsDefaults: FlyingIconsProps = {
  transparent: false,
  seed: 'sitewise-01',
  baseSize: 150,
  minScale: 0.34,
  maxScale: 2.05,
  scaleBias: 1.5,
  startScaleMin: 2.8,
  startScaleMax: 5.5,
  flyInFrames: 42,
  stagger: 5,
  // Last icon settles around frame 97, so this leaves ~1.4s fully settled
  // before the rise begins — the beat the whole shot is built around.
  riseStart: 140,
  riseFrames: 46,
  riseDistance: 1.15,
  safeWidth: 0.46,
  safeHeight: 0.24,
  opacity: 0.92,
  showTile: true,
};

type Placed = {
  name: string;
  x: number;
  y: number;
  size: number;
  startScale: number;
  delay: number;
  riseDelay: number;
  tilt: number;
  bobPhase: number;
  bobAmp: number;
};

const clamp = (v: number, lo: number, hi: number) =>
  Math.min(hi, Math.max(lo, v));

/**
 * Jittered grid rather than rejection sampling. One icon per cell guarantees
 * even coverage; the jitter inside each cell keeps it looking scattered. Cells
 * that collide with the central safe zone are dropped before assignment.
 *
 * Rejection sampling was tried first and clustered badly — it has to give up
 * after N attempts, and whatever position it gives up on is kept.
 */
const planLayout = (
  width: number,
  height: number,
  p: FlyingIconsProps
): Placed[] => {
  const cols = 5;
  const rows = 3;
  const cw = width / cols;
  const ch = height / rows;
  const cx = width / 2;
  const cy = height / 2;
  const safeW = (width * p.safeWidth) / 2;
  const safeH = (height * p.safeHeight) / 2;
  const margin = 30;

  const cells: {x: number; y: number}[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const ccx = (c + 0.5) * cw;
      const ccy = (r + 0.5) * ch;
      const hitsSafeZone =
        Math.abs(ccx - cx) < safeW + cw * 0.25 &&
        Math.abs(ccy - cy) < safeH + ch * 0.25;
      if (!hitsSafeZone) {
        cells.push({x: ccx, y: ccy});
      }
    }
  }

  const order = cells
    .map((cell, i) => ({cell, k: random(`${p.seed}-cell-${i}`)}))
    .sort((a, b) => a.k - b.k)
    .map((o) => o.cell);

  // Only icons without a fully pinned position consume a grid slot, so hand
  // placing one does not leave a hole in the distribution of the rest.
  let slot = 0;

  return ICONS.map((spec, i) => {
    const scale =
      spec.scale ??
      p.minScale +
        Math.pow(random(`${p.seed}-s-${i}`), p.scaleBias) *
          (p.maxScale - p.minScale);
    const size = p.baseSize * scale;
    // Half-extent of the tile, not the icon, so nothing clips at the edges.
    const half = (size * 1.45) / 2;

    const pinned = spec.x !== undefined && spec.y !== undefined;
    const cell = order[(pinned ? slot : slot++) % order.length];

    return {
      name: spec.name,
      x:
        spec.x !== undefined
          ? spec.x * width
          : clamp(
              cell.x + (random(`${p.seed}-jx-${i}`) - 0.5) * cw * 0.55,
              half + margin,
              width - half - margin
            ),
      y:
        spec.y !== undefined
          ? spec.y * height
          : clamp(
              cell.y + (random(`${p.seed}-jy-${i}`) - 0.5) * ch * 0.55,
              half + margin,
              height - half - margin
            ),
      size,
      startScale:
        p.startScaleMin +
        random(`${p.seed}-z-${i}`) * (p.startScaleMax - p.startScaleMin),
      delay: Math.round(random(`${p.seed}-d-${i}`) * ICONS.length) * p.stagger,
      riseDelay: Math.round(random(`${p.seed}-r-${i}`) * 10),
      tilt: (random(`${p.seed}-t-${i}`) - 0.5) * 10,
      bobPhase: random(`${p.seed}-b-${i}`) * Math.PI * 2,
      bobAmp: 3 + random(`${p.seed}-a-${i}`) * 7,
    };
  });
};

export const FlyingIcons: React.FC<FlyingIconsProps> = (props) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const items = React.useMemo(
    () => planLayout(width, height, props),
    [width, height, props]
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: props.transparent ? 'transparent' : '#060608',
        transformOrigin: interpolate(frame, [100], ["50% 50%"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp"
        })
      }}
    >
      {items.map((it, i) => {
        // Arrival: fast out, long decelerate, zero overshoot — the film's law.
        const tIn = interpolate(
          frame,
          [it.delay, it.delay + props.flyInFrames],
          [0, 1],
          {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.out(Easing.cubic),
          }
        );

        // Exit accelerates away instead, so they leave rather than drift off.
        const outFrom = props.riseStart + it.riseDelay;
        const tOut = interpolate(
          frame,
          [outFrom, outFrom + props.riseFrames],
          [0, 1],
          {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.in(Easing.cubic),
          }
        );

        const scale = it.startScale + (1 - it.startScale) * tIn;

        // Perspective-correct entry: something closer to the lens sits further
        // from frame centre, so the offset shrinks as the icon recedes.
        const spread = 1 + (scale - 1) * 0.45;
        const cx = width / 2;
        const cy = height / 2;
        const px = cx + (it.x - cx) * spread;
        const py = cy + (it.y - cy) * spread;

        const bob =
          Math.sin(frame / fps + it.bobPhase) * it.bobAmp * tIn * (1 - tOut);
        const rise = -height * props.riseDistance * tOut;

        const opacity =
          props.opacity *
          interpolate(tIn, [0, 0.35], [0, 1], {extrapolateRight: 'clamp'}) *
          (1 - interpolate(tOut, [0.25, 1], [0, 1], {extrapolateLeft: 'clamp'}));

        if (opacity <= 0.002) {
          return null;
        }

        const tileSize = it.size * 1.45;

        return (
          <div
            key={it.name + i}
            style={{
              position: 'absolute',
              left: px - it.size / 2,
              top: py - it.size / 2 + bob + rise,
              width: it.size,
              height: it.size,
              opacity,
              transform: `scale(${scale}) rotate(${it.tilt * (1 - tIn)}deg)`,
              transformOrigin: 'center center',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {props.showTile ? (
              <div
                style={{
                  position: 'absolute',
                  width: tileSize,
                  height: tileSize,
                  left: (it.size - tileSize) / 2,
                  top: (it.size - tileSize) / 2,
                  border: '1.5px solid #2B2D33',
                  borderRadius: tileSize * 0.22,
                  backgroundColor: 'rgba(21, 22, 27, 0.55)',
                }}
              />
            ) : null}
            <Img
  src={staticFile(`icons/${it.name}.png`)}
  style={{width: '100%', height: '100%', position: 'relative'}} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
