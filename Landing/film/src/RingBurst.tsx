import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * Clip 4 — light ring burst.
 *
 * A single shell of light expanding from frame centre, rendered on pure black
 * so it can be Screen-blended over any beat in the film.
 *
 * Colour ramp comes from the SiteWise tokens in landing-story.css: a near-white
 * core bleeding out through the accent blue into the deep electric blue.
 */

const CORE = [0xea, 0xf4, 0xff];
const ACCENT = [0x83, 0xb6, 0xed];
const DEEP = [0x2f, 0x72, 0xc4];

export type RingBurstProps = {
  /** Render on pure black (false) or with a transparent background (true). */
  transparent: boolean;
  /** How far past the frame corners the shell travels. 1.0 = exactly to the corners. */
  overshoot: number;
  /** Ease strength. Higher starts faster and decelerates harder. 1 = linear. */
  ease: number;
  /** Core stroke width in px, at the start of the expansion and at the end. */
  strokeStart: number;
  strokeEnd: number;
  /** Halo width as a multiple of the core stroke. */
  halo: number;
  /** Peak brightness of the halo relative to the core. */
  haloGain: number;
  /** How much the shell dims as it spreads. 0 = never dims. */
  falloff: number;
  /** Overall gain. Above 1 lets the core saturate to white at the peak. */
  brightness: number;
  /** Progress at which the swell finishes and the decay begins. */
  peakIn: number;
  peakOut: number;
  /**
   * Burst mode (null) leaves the frame black once the shell has passed.
   * Set a hex and the inside of the shell fills with it, turning the burst
   * into a wipe — which is what the reference does at 39.5s and 12.8s.
   */
  wipeTo: string | null;
};

export const ringBurstDefaults: RingBurstProps = {
  transparent: false,
  overshoot: 1.25,
  ease: 2.6,
  strokeStart: 8,
  strokeEnd: 150,
  halo: 3.5,
  haloGain: 0.38,
  falloff: 0.9,
  brightness: 1.6,
  peakIn: 0.14,
  peakOut: 0.6,
  wipeTo: null,
};

const hexToRgb = (hex: string): number[] => {
  const h = hex.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
};

const mix = (a: number[], b: number[], t: number) =>
  a.map((v, i) => Math.round(v + (b[i] - v) * t));

const smoothstep = (e0: number, e1: number, x: number) => {
  // A zero-width range is legitimate here — peakOut of 1 means "never decay" —
  // so step rather than divide by zero and poison the colour string.
  if (e0 === e1) {
    return x < e0 ? 0 : 1;
  }
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

/** Colour as a function of distance from the crest, in halo-widths. */
const rampColour = (u: number) =>
  u < 0.35
    ? mix(CORE, ACCENT, smoothstep(0, 0.35, u))
    : mix(ACCENT, DEEP, smoothstep(0.35, 1.2, u));

/** Intensity as a function of signed distance from the crest. */
const profile = (x: number, w: number, hw: number, haloGain: number) =>
  Math.min(1, Math.exp(-((x / w) ** 2)) + haloGain * Math.exp(-((x / hw) ** 2)));

export const drawRingBurst = (
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  progress: number,
  p: RingBurstProps
) => {
  const eased = 1 - Math.pow(1 - progress, p.ease);

  const halfDiag = Math.hypot(width / 2, height / 2);
  const r = halfDiag * p.overshoot * eased;
  const w = p.strokeStart + (p.strokeEnd - p.strokeStart) * eased;
  const hw = w * p.halo;

  // Brightness swells, holds, then decays to nothing so the last frames return
  // to a pure ground. Energy also spreads as the shell grows, which dims it
  // independently of the envelope.
  // peakOut of 1 means "never decay" — the shell is meant to still be alight
  // when it leaves frame, which is what a wipe needs.
  const decay = p.peakOut >= 1 ? 1 : 1 - smoothstep(p.peakOut, 1, progress);
  const gain =
    p.brightness *
    smoothstep(0, p.peakIn, progress) *
    decay *
    (1 / (1 + p.falloff * eased));

  const wipe = p.wipeTo ? hexToRgb(p.wipeTo) : null;

  ctx.clearRect(0, 0, width, height);
  if (!p.transparent) {
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);
  }
  // In wipe mode the fill behind the shell still has to be painted even once
  // the shell itself has gone, or the last frames drop back to black.
  if (gain <= 0.001 && !wipe) {
    return;
  }

  const outer = halfDiag * 1.6;
  const grad = ctx.createRadialGradient(
    width / 2,
    height / 2,
    0,
    width / 2,
    height / 2,
    outer
  );

  // Stops packed tightly around the crest, where all the detail lives — a
  // uniform ramp would be far too coarse while the stroke is still thin.
  const stops: number[] = [0];
  for (let k = -4; k <= 4; k += 0.1) {
    const d = r + k * hw;
    if (d > 0 && d < outer) {
      stops.push(d);
    }
  }
  stops.push(outer);
  stops.sort((a, b) => a - b);

  // In wipe mode the coverage behind the shell rises to opaque, so the burst
  // hands the frame over to a new ground instead of dying away.
  const wipeGain = wipe ? smoothstep(0, p.peakIn, progress) : 0;

  let last = -1;
  for (const d of stops) {
    const off = Math.min(1, Math.max(0, d / outer));
    if (off - last < 0.0004) {
      continue; // addColorStop needs strictly increasing offsets
    }
    last = off;
    const x = d - r;
    const shell = Math.min(1, profile(x, w, hw, p.haloGain) * gain);

    if (wipe && x < 0) {
      // Ramp tight enough that the fill actually closes behind the crest —
      // too wide and the frame corners never reach the target ground.
      const inside = smoothstep(0, -hw * 1.5, x) * wipeGain;
      const [R, G, B] = mix(rampColour(Math.abs(x) / hw), wipe, inside);
      grad.addColorStop(off, `rgba(${R},${G},${B},${Math.max(shell, inside).toFixed(4)})`);
      continue;
    }

    const [R, G, B] = rampColour(Math.abs(x) / hw);
    grad.addColorStop(off, `rgba(${R},${G},${B},${shell.toFixed(4)})`);
  }

  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, width, height);
};

export const RingBurst: React.FC<RingBurstProps> = (props) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();

  useLayoutEffect(() => {
    const ctx = ref.current?.getContext('2d');
    if (!ctx) {
      return;
    }
    const progress =
      durationInFrames <= 1 ? 0 : frame / (durationInFrames - 1);
    drawRingBurst(ctx, width, height, progress, props);
  });

  return (
    <AbsoluteFill
      style={{backgroundColor: props.transparent ? 'transparent' : '#000000'}}
    >
      <canvas ref={ref} width={width} height={height} />
    </AbsoluteFill>
  );
};
