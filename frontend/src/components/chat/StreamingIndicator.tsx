import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

type StreamingIndicatorProps = {
  message?: string | null;
  /** Overrides the chat bubble layout when reused outside the message list. */
  className?: string;
};

type Vec3 = readonly [number, number, number];
type Quat = { x: number; y: number; z: number; w: number };

const CUBE_VERTICES: readonly Vec3[] = [
  [-1, -1, -1],
  [-1, -1, 1],
  [-1, 1, -1],
  [-1, 1, 1],
  [1, -1, -1],
  [1, -1, 1],
  [1, 1, -1],
  [1, 1, 1],
] as const;

/** Inline mark size — stays next to the status label. */
const MARK_SIZE = 16;
const DOT_SIZE = 2.35;
const PROJECTION_SCALE = 3.85;
/** Tiny view bias so face-on poses do not stack front/back corners. */
const VIEW_BIAS_X = 0.16;
const VIEW_BIAS_Y = -0.11;

const HOLD_MS_MIN = 640;
const HOLD_MS_MAX = 980;
const WINDUP_MS = 140;
/** Radians of anticipation opposite the tumble direction. */
const WINDUP_AMOUNT = 0.12;
const SETTLE_MS = 180;

const TAU = Math.PI * 2;

const CUBE_FACES = [
  { id: 0, quat: quatIdentity() }, // +Z toward camera
  { id: 1, quat: quatFromAxisAngle([0, 1, 0], -Math.PI / 2) }, // +X
  { id: 2, quat: quatFromAxisAngle([0, 1, 0], Math.PI / 2) }, // -X
  { id: 3, quat: quatFromAxisAngle([1, 0, 0], Math.PI / 2) }, // +Y
  { id: 4, quat: quatFromAxisAngle([1, 0, 0], -Math.PI / 2) }, // -Y
  { id: 5, quat: quatFromAxisAngle([1, 0, 0], Math.PI) }, // -Z
] as const;

const ADJACENT: readonly (readonly number[])[] = [
  [1, 2, 3, 4],
  [0, 3, 4, 5],
  [0, 3, 4, 5],
  [0, 1, 2, 5],
  [0, 1, 2, 5],
  [1, 2, 3, 4],
];

function quatIdentity(): Quat {
  return { x: 0, y: 0, z: 0, w: 1 };
}

function quatFromAxisAngle(axis: Vec3, angle: number): Quat {
  const [ax, ay, az] = normalize(axis);
  const half = angle * 0.5;
  const s = Math.sin(half);
  return { x: ax * s, y: ay * s, z: az * s, w: Math.cos(half) };
}

function quatMul(a: Quat, b: Quat): Quat {
  return {
    x: a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
    y: a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
    z: a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
    w: a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
  };
}

function quatConjugate(q: Quat): Quat {
  return { x: -q.x, y: -q.y, z: -q.z, w: q.w };
}

function quatNormalize(q: Quat): Quat {
  const len = Math.hypot(q.x, q.y, q.z, q.w) || 1;
  return { x: q.x / len, y: q.y / len, z: q.z / len, w: q.w / len };
}

function rotateByQuat(v: Vec3, q: Quat): Vec3 {
  const p: Quat = { x: v[0], y: v[1], z: v[2], w: 0 };
  const r = quatMul(quatMul(q, p), quatConjugate(q));
  return [r.x, r.y, r.z];
}

function normalize(v: Vec3): Vec3 {
  const len = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / len, v[1] / len, v[2] / len];
}

/** Relative rotation that takes `from` into `to` (shortest arc). */
function quatDelta(from: Quat, to: Quat): Quat {
  return quatNormalize(quatMul(to, quatConjugate(from)));
}

function quatToAxisAngle(qIn: Quat): { axis: Vec3; angle: number } {
  const q = quatNormalize(qIn);
  const w = Math.min(1, Math.max(-1, q.w));
  const angle = 2 * Math.acos(w);
  const s = Math.sqrt(Math.max(0, 1 - w * w));
  if (s < 1e-6) {
    return { axis: [0, 1, 0], angle: 0 };
  }
  return { axis: [q.x / s, q.y / s, q.z / s], angle };
}

function rotX([x, y, z]: Vec3, angle: number): Vec3 {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return [x, y * c - z * s, y * s + z * c];
}

function rotY([x, y, z]: Vec3, angle: number): Vec3 {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return [x * c + z * s, y, -x * s + z * c];
}

/** Quintic in-out: slow start, quick middle, soft landing. */
function easeInOutQuint(t: number): number {
  const x = Math.min(1, Math.max(0, t));
  return x < 0.5 ? 16 * x ** 5 : 1 - (-2 * x + 2) ** 5 / 2;
}

/** Soft landing only — used for the intro catch. */
function easeOutCubic(t: number): number {
  const x = 1 - Math.min(1, Math.max(0, t));
  return 1 - x * x * x;
}

/** Anticipation ease — ease into the wind-up. */
function easeOutQuad(t: number): number {
  const x = 1 - Math.min(1, Math.max(0, t));
  return 1 - x * x;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function randBetween(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function pickNextFace(current: number): number {
  if (Math.random() < 0.72) {
    const options = ADJACENT[current];
    return options[Math.floor(Math.random() * options.length)] ?? (current + 1) % 6;
  }
  let next = Math.floor(Math.random() * 6);
  if (next === current) next = (next + 1) % 6;
  return next;
}

type TumblePlan = {
  axis: Vec3;
  /** Signed radians; may be ±90/180/270/450-class. */
  angle: number;
  durationMs: number;
};

/**
 * Plan a tumble from one face pose to another.
 * Regime mixes short edge turns, long-way 270s, and occasional full-extra revolutions.
 */
function planTumble(fromFace: number, toFace: number): TumblePlan {
  const delta = quatDelta(CUBE_FACES[fromFace].quat, CUBE_FACES[toFace].quat);
  let { axis, angle } = quatToAxisAngle(delta);

  // Keep a stable signed turn; acos path is [0, π].
  if (Math.random() < 0.5 && angle > 1e-4 && angle < Math.PI - 1e-4) {
    axis = [-axis[0], -axis[1], -axis[2]];
    angle = -angle;
  }

  const abs = Math.abs(angle);
  const sign = angle >= 0 ? 1 : -1;
  const roll = Math.random();

  if (abs < 1e-4) {
    // Same orientation edge case — force a scenic spin onto a cardinal axis.
    axis = [0, 1, 0];
    angle = sign * (Math.PI / 2 + TAU);
    return { axis, angle, durationMs: 1400 };
  }

  if (roll < 0.38 && abs < Math.PI - 0.05) {
    // Long way around the same axis (e.g. 90° → 270°).
    angle = sign * (TAU - abs);
    return { axis, angle, durationMs: lerp(980, 1180, Math.min(1, Math.abs(angle) / TAU)) };
  }

  if (roll < 0.58) {
    // Extra full revolution then settle on the target face.
    angle = angle + sign * TAU;
    return { axis, angle, durationMs: lerp(1200, 1550, Math.min(1, Math.abs(angle) / (TAU + Math.PI))) };
  }

  // Ordinary shortest tumble (often 90° / 180°).
  return {
    axis,
    angle,
    durationMs: abs > Math.PI * 0.75 ? 920 : 760,
  };
}

function projectVertex(
  vertex: Vec3,
  orientation: Quat,
): { x: number; y: number; depth: number } {
  let p = rotateByQuat(vertex, orientation);
  p = rotY(p, VIEW_BIAS_Y);
  p = rotX(p, VIEW_BIAS_X);
  const perspective = 1 / (1.18 - p[2] * 0.16);
  return {
    x: p[0] * perspective,
    y: p[1] * perspective,
    depth: p[2],
  };
}

function paintVertices(dots: HTMLElement[], orientation: Quat, bloom = 1) {
  const half = MARK_SIZE / 2;

  for (let index = 0; index < CUBE_VERTICES.length; index += 1) {
    const dot = dots[index];
    if (!dot) continue;

    const point = projectVertex(CUBE_VERTICES[index], orientation);
    const depthT = (point.depth + 1.7) / 3.4;
    const opacity = (0.2 + depthT * 0.68) * lerp(0.85, 1, bloom);
    const scale = (0.76 + depthT * 0.36) * bloom;
    const x = half + point.x * PROJECTION_SCALE - DOT_SIZE / 2;
    const y = half - point.y * PROJECTION_SCALE - DOT_SIZE / 2;

    // Single transform avoids left/top + scale fighting and reduces jitter.
    dot.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
    dot.style.opacity = `${opacity}`;
  }
}

type Phase =
  | { kind: "intro"; from: Quat; axis: Vec3; angle: number; toFace: number; start: number; duration: number }
  | { kind: "hold"; face: number; until: number }
  | {
      kind: "windup";
      face: number;
      base: Quat;
      axis: Vec3;
      windupAngle: number;
      tumbleAngle: number;
      tumbleDuration: number;
      toFace: number;
      start: number;
    }
  | {
      kind: "tumble";
      fromFace: number;
      toFace: number;
      base: Quat;
      axis: Vec3;
      angle: number;
      start: number;
      duration: number;
    }
  | { kind: "settle"; face: number; start: number };

function orientationAtAngle(base: Quat, axis: Vec3, angle: number): Quat {
  return quatNormalize(quatMul(quatFromAxisAngle(axis, angle), base));
}

function CubeTumbleMark() {
  const rootRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const dots = Array.from(root.querySelectorAll<HTMLElement>("[data-vertex]"));
    const reducedMotion =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const firstFace = 0;
    paintVertices(dots, CUBE_FACES[firstFace].quat, 1);

    if (reducedMotion) return;

    // Intro: catch out of a long spin and land on the first face.
    const introPlan = planTumble(5, firstFace);
    let phase: Phase = {
      kind: "intro",
      from: orientationAtAngle(
        CUBE_FACES[firstFace].quat,
        introPlan.axis,
        -introPlan.angle,
      ),
      axis: introPlan.axis,
      angle: introPlan.angle,
      toFace: firstFace,
      start: performance.now(),
      duration: 1100,
    };

    let frameId = 0;

    const beginWindup = (face: number, now: number) => {
      const toFace = pickNextFace(face);
      const plan = planTumble(face, toFace);
      const windupAngle = -WINDUP_AMOUNT * Math.sign(plan.angle || 1);
      phase = {
        kind: "windup",
        face,
        base: CUBE_FACES[face].quat,
        axis: plan.axis,
        windupAngle,
        tumbleAngle: plan.angle,
        tumbleDuration: plan.durationMs,
        toFace,
        start: now,
      };
    };

    const tick = (now: number) => {
      if (phase.kind === "intro") {
        const t = (now - phase.start) / phase.duration;
        if (t >= 1) {
          paintVertices(dots, CUBE_FACES[phase.toFace].quat, 1);
          phase = {
            kind: "hold",
            face: phase.toFace,
            until: now + randBetween(HOLD_MS_MIN, HOLD_MS_MAX),
          };
        } else {
          const eased = easeOutCubic(t);
          const q = orientationAtAngle(phase.from, phase.axis, phase.angle * eased);
          // Soft bloom as it arrives.
          const bloom = lerp(0.92, 1, eased);
          paintVertices(dots, q, bloom);
        }
      } else if (phase.kind === "hold") {
        paintVertices(dots, CUBE_FACES[phase.face].quat, 1);
        if (now >= phase.until) {
          beginWindup(phase.face, now);
        }
      } else if (phase.kind === "windup") {
        const t = (now - phase.start) / WINDUP_MS;
        if (t >= 1) {
          phase = {
            kind: "tumble",
            fromFace: phase.face,
            toFace: phase.toFace,
            base: orientationAtAngle(phase.base, phase.axis, phase.windupAngle),
            axis: phase.axis,
            // Include the wind-up offset so we still finish on the target face.
            angle: phase.tumbleAngle - phase.windupAngle,
            start: now,
            duration: phase.tumbleDuration,
          };
        } else {
          const eased = easeOutQuad(t);
          const q = orientationAtAngle(
            phase.base,
            phase.axis,
            phase.windupAngle * eased,
          );
          paintVertices(dots, q, 1);
        }
      } else if (phase.kind === "tumble") {
        const t = (now - phase.start) / phase.duration;
        if (t >= 1) {
          paintVertices(dots, CUBE_FACES[phase.toFace].quat, 1.04);
          phase = { kind: "settle", face: phase.toFace, start: now };
        } else {
          const eased = easeInOutQuint(t);
          const q = orientationAtAngle(phase.base, phase.axis, phase.angle * eased);
          paintVertices(dots, q, 1);
        }
      } else {
        // settle — brief bloom down to rest after impact
        const t = (now - phase.start) / SETTLE_MS;
        if (t >= 1) {
          paintVertices(dots, CUBE_FACES[phase.face].quat, 1);
          phase = {
            kind: "hold",
            face: phase.face,
            until: now + randBetween(HOLD_MS_MIN, HOLD_MS_MAX),
          };
        } else {
          const bloom = lerp(1.04, 1, easeOutCubic(t));
          paintVertices(dots, CUBE_FACES[phase.face].quat, bloom);
        }
      }

      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frameId);
  }, []);

  return (
    <span
      ref={rootRef}
      className="streaming-cube relative inline-block shrink-0"
      style={{ width: MARK_SIZE, height: MARK_SIZE }}
      aria-hidden="true"
    >
      {CUBE_VERTICES.map((_, index) => (
        <span
          key={index}
          data-vertex
          className="streaming-cube__point absolute left-0 top-0 rounded-full bg-muted-foreground will-change-transform"
          style={{
            width: DOT_SIZE,
            height: DOT_SIZE,
            transformOrigin: "center",
          }}
        />
      ))}
    </span>
  );
}

export function StreamingIndicator({ message, className }: StreamingIndicatorProps) {
  const label = message?.trim() ? message : "Pi is writing…";

  return (
    <div
      className={cn(
        "flex items-center gap-2.5 text-sm text-muted-foreground",
        className ?? "mr-8 max-w-[92%] self-start",
      )}
      role="status"
      aria-live="polite"
    >
      <CubeTumbleMark />
      <span>{label}</span>
    </div>
  );
}
