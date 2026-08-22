import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

type StreamingIndicatorProps = {
  message?: string | null;
  description?: string | null;
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

const MARK_SIZE = 34;
const DOT_SIZE = 3.2;
const PROJECTION_SCALE = 5.6;
const VIEW_BIAS_X = 0.16;
const VIEW_BIAS_Y = -0.11;

const HOLD_MS_MIN = 80;
const HOLD_MS_MAX = 160;
const WINDUP_MS = 80;
const WINDUP_AMOUNT = 0.1;
const SETTLE_MS = 70;

const TAU = Math.PI * 2;

const CUBE_FACES = [
  { id: 0, quat: quatIdentity() },
  { id: 1, quat: quatFromAxisAngle([0, 1, 0], -Math.PI / 2) },
  { id: 2, quat: quatFromAxisAngle([0, 1, 0], Math.PI / 2) },
  { id: 3, quat: quatFromAxisAngle([1, 0, 0], Math.PI / 2) },
  { id: 4, quat: quatFromAxisAngle([1, 0, 0], -Math.PI / 2) },
  { id: 5, quat: quatFromAxisAngle([1, 0, 0], Math.PI) },
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

function quatDelta(from: Quat, to: Quat): Quat {
  return quatNormalize(quatMul(to, quatConjugate(from)));
}

function quatToAxisAngle(qIn: Quat): { axis: Vec3; angle: number } {
  const q = quatNormalize(qIn);
  const w = Math.min(1, Math.max(-1, q.w));
  const angle = 2 * Math.acos(w);
  const s = Math.sqrt(Math.max(0, 1 - w * w));
  if (s < 1e-6) return { axis: [0, 1, 0], angle: 0 };
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

function easeInOutQuint(t: number): number {
  const x = Math.min(1, Math.max(0, t));
  return x < 0.5 ? 16 * x ** 5 : 1 - (-2 * x + 2) ** 5 / 2;
}

function easeOutCubic(t: number): number {
  const x = 1 - Math.min(1, Math.max(0, t));
  return 1 - x * x * x;
}

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
  angle: number;
  durationMs: number;
};

function planTumble(fromFace: number, toFace: number): TumblePlan {
  const delta = quatDelta(CUBE_FACES[fromFace].quat, CUBE_FACES[toFace].quat);
  let { axis, angle } = quatToAxisAngle(delta);

  if (Math.random() < 0.5 && angle > 1e-4 && angle < Math.PI - 1e-4) {
    axis = [-axis[0], -axis[1], -axis[2]];
    angle = -angle;
  }

  const abs = Math.abs(angle);
  const sign = angle >= 0 ? 1 : -1;
  const roll = Math.random();

  if (abs < 1e-4) {
    axis = [0, 1, 0];
    angle = sign * (Math.PI / 2 + TAU);
    return { axis, angle, durationMs: 1100 };
  }

  if (roll < 0.38 && abs < Math.PI - 0.05) {
    angle = sign * (TAU - abs);
    return { axis, angle, durationMs: lerp(820, 980, Math.min(1, Math.abs(angle) / TAU)) };
  }

  if (roll < 0.58) {
    angle = angle + sign * TAU;
    return {
      axis,
      angle,
      durationMs: lerp(980, 1280, Math.min(1, Math.abs(angle) / (TAU + Math.PI))),
    };
  }

  return {
    axis,
    angle,
    durationMs: abs > Math.PI * 0.75 ? 780 : 640,
  };
}

function orientationAtAngle(base: Quat, axis: Vec3, angle: number): Quat {
  return quatNormalize(quatMul(quatFromAxisAngle(axis, angle), base));
}

function projectPoint(point: Vec3): { x: number; y: number; depth: number } {
  let p = rotY(point, VIEW_BIAS_Y);
  p = rotX(p, VIEW_BIAS_X);
  const perspective = 1 / (1.18 - p[2] * 0.16);
  return {
    x: p[0] * perspective,
    y: p[1] * perspective,
    depth: p[2],
  };
}

function paintCube(dots: HTMLElement[], orientation: Quat, bloom = 1) {
  const half = MARK_SIZE / 2;

  for (let index = 0; index < CUBE_VERTICES.length; index += 1) {
    const dot = dots[index];
    if (!dot) continue;

    const rotated = rotateByQuat(CUBE_VERTICES[index], orientation);
    const point = projectPoint(rotated);
    const depthT = (point.depth + 1.7) / 3.4;
    const opacity = (0.90 + depthT * 0.10) * lerp(0.98, 1, bloom);
    const scale = (0.82 + depthT * 0.4) * bloom;
    const x = half + point.x * PROJECTION_SCALE - DOT_SIZE / 2;
    const y = half - point.y * PROJECTION_SCALE - DOT_SIZE / 2;

    dot.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
    dot.style.opacity = `${opacity}`;
  }
}

type SpinnerPhase =
  | {
      kind: "intro";
      from: Quat;
      axis: Vec3;
      angle: number;
      toFace: number;
      start: number;
      duration: number;
    }
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
      toFace: number;
      base: Quat;
      axis: Vec3;
      angle: number;
      start: number;
      duration: number;
    }
  | { kind: "settle"; face: number; start: number };

function createIntroPhase(now: number): SpinnerPhase {
  const firstFace = 0;
  const introPlan = planTumble(5, firstFace);
  return {
    kind: "intro",
    from: orientationAtAngle(
      CUBE_FACES[firstFace].quat,
      introPlan.axis,
      -introPlan.angle,
    ),
    axis: introPlan.axis,
    angle: introPlan.angle,
    toFace: firstFace,
    start: now,
    duration: 820,
  };
}

function beginWindup(face: number, now: number): SpinnerPhase {
  const toFace = pickNextFace(face);
  const plan = planTumble(face, toFace);
  const windupAngle = -WINDUP_AMOUNT * Math.sign(plan.angle || 1);
  return {
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
}

function stepSpinner(
  phase: SpinnerPhase,
  now: number,
): {
  orientation: Quat;
  bloom: number;
  phase: SpinnerPhase;
} {
  if (phase.kind === "intro") {
    const t = (now - phase.start) / phase.duration;
    if (t >= 1) {
      return {
        orientation: CUBE_FACES[phase.toFace].quat,
        bloom: 1,
        phase: {
          kind: "hold",
          face: phase.toFace,
          until: now + randBetween(HOLD_MS_MIN, HOLD_MS_MAX),
        },
      };
    }
    const eased = easeOutCubic(t);
    return {
      orientation: orientationAtAngle(phase.from, phase.axis, phase.angle * eased),
      bloom: lerp(0.92, 1, eased),
      phase,
    };
  }

  if (phase.kind === "hold") {
    if (now >= phase.until) {
      return {
        orientation: CUBE_FACES[phase.face].quat,
        bloom: 1,
        phase: beginWindup(phase.face, now),
      };
    }
    return {
      orientation: CUBE_FACES[phase.face].quat,
      bloom: 1,
      phase,
    };
  }

  if (phase.kind === "windup") {
    const t = (now - phase.start) / WINDUP_MS;
    if (t >= 1) {
      return {
        orientation: orientationAtAngle(phase.base, phase.axis, phase.windupAngle),
        bloom: 1,
        phase: {
          kind: "tumble",
          toFace: phase.toFace,
          base: orientationAtAngle(phase.base, phase.axis, phase.windupAngle),
          axis: phase.axis,
          angle: phase.tumbleAngle - phase.windupAngle,
          start: now,
          duration: phase.tumbleDuration,
        },
      };
    }
    const eased = easeOutQuad(t);
    return {
      orientation: orientationAtAngle(
        phase.base,
        phase.axis,
        phase.windupAngle * eased,
      ),
      bloom: 1,
      phase,
    };
  }

  if (phase.kind === "tumble") {
    const t = (now - phase.start) / phase.duration;
    if (t >= 1) {
      return {
        orientation: CUBE_FACES[phase.toFace].quat,
        bloom: 1.03,
        phase: {
          kind: "settle",
          face: phase.toFace,
          start: now,
        },
      };
    }
    const eased = easeInOutQuint(t);
    return {
      orientation: orientationAtAngle(phase.base, phase.axis, phase.angle * eased),
      bloom: 1,
      phase,
    };
  }

  const t = (now - phase.start) / SETTLE_MS;
  if (t >= 1) {
    return {
      orientation: CUBE_FACES[phase.face].quat,
      bloom: 1,
      phase: {
        kind: "hold",
        face: phase.face,
        until: now + randBetween(HOLD_MS_MIN, HOLD_MS_MAX),
      },
    };
  }
  return {
    orientation: CUBE_FACES[phase.face].quat,
    bloom: lerp(1.03, 1, easeOutCubic(t)),
    phase,
  };
}

export function CubeTumbleMark() {
  const rootRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const dots = Array.from(
      root.querySelectorAll<HTMLElement>("[data-cube='primary']"),
    );
    const reducedMotion =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    paintCube(dots, CUBE_FACES[0].quat);

    if (reducedMotion) return;

    let phase: SpinnerPhase = createIntroPhase(performance.now());
    let frameId = 0;

    const tick = (now: number) => {
      const stepped = stepSpinner(phase, now);
      phase = stepped.phase;
      paintCube(dots, stepped.orientation, stepped.bloom);
      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frameId);
  }, []);

  return (
    <span
      ref={rootRef}
      className="streaming-cube relative block shrink-0 overflow-visible"
      style={{ width: MARK_SIZE, height: MARK_SIZE }}
      aria-hidden="true"
    >
      {CUBE_VERTICES.map((_, index) => (
        <span
          key={index}
          data-cube="primary"
          data-vertex
          className="streaming-cube__point absolute left-0 top-0 rounded-full bg-[var(--sw-facet-blue-hex,#2f72c4)] will-change-transform"
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

export function StreamingIndicator({
  message,
  description,
  className,
}: StreamingIndicatorProps) {
  const label = message?.trim() || "";
  const detail = description?.trim() || "";

  return (
    <div
      className={cn(
        "flex items-center gap-3 text-sm",
        className ?? "mr-8 max-w-[92%] self-start",
      )}
      role="status"
      aria-live="polite"
      aria-label={label || "Working"}
    >
      <CubeTumbleMark />
      {label || detail ? (
        <div className="streaming-status-copy flex min-h-[34px] min-w-0 flex-col justify-center gap-1">
          {label ? (
            <p
              className={cn(
                "streaming-status-live truncate leading-none",
                detail ? "font-medium" : undefined,
              )}
            >
              {label}
            </p>
          ) : null}
          {detail ? (
            <p className="truncate text-xs leading-none opacity-55">{detail}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
