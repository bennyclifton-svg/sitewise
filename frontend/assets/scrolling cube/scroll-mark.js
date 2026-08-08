/**
 * Sitewise mark — scroll-driven camera.
 *
 * Mounts the 3D mark into a sticky canvas and flies the camera along the
 * approved presets as the page scrolls past. Nothing else on the page
 * needs to know it exists.
 *
 *   import { mountScrollMark } from '/style-guide/3d/scroll-mark.js';
 *   mountScrollMark(THREE, {
 *     canvas:  document.querySelector('#mark-canvas'),
 *     track:   document.querySelector('#mark-track'),
 *     OrbitControls          // optional, only if you want drag-to-orbit
 *   });
 *
 * `track` is the tall element whose scroll progress drives the camera —
 * typically the section containing the sticky canvas. Progress runs 0 at
 * the moment the track's top hits the viewport top, 1 when its bottom
 * reaches the viewport bottom.
 *
 * The camera is interpolated in SPHERICAL coordinates, not by lerping
 * positions. A straight lerp between two camera positions cuts a chord
 * through the object and briefly puts the camera inside it; an arc keeps
 * a constant orbit around the origin, which is what an architectural
 * flythrough actually does.
 */

import { buildMark, applyLighting, CAMERA_PRESETS } from './mark.js';

/** The scroll path. Each stop is a preset name and where it lands, 0–1. */
export const DEFAULT_PATH = [
  { preset: 'logo',  at: 0.00 },
  { preset: 'three', at: 0.34 },
  { preset: 'plan',  at: 0.67 },
  { preset: 'logo',  at: 1.00 }
];

function toSpherical(dir, dist) {
  const [x, y, z] = dir;
  const len = Math.hypot(x, y, z) || 1;
  const nx = (x / len) * dist, ny = (y / len) * dist, nz = (z / len) * dist;
  return {
    radius: dist,
    theta: Math.atan2(nx, nz),               // azimuth
    phi: Math.acos(Math.max(-1, Math.min(1, ny / dist)))  // polar, 0 = straight up
  };
}

const PRESET_SPHERICAL = Object.fromEntries(
  Object.entries(CAMERA_PRESETS).map(([k, v]) => [k, { ...toSpherical(v.dir, v.dist), fov: v.fov }])
);

const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

/** Shortest-path angular lerp, so the camera never takes the long way round. */
function lerpAngle(a, b, t) {
  let d = b - a;
  while (d > Math.PI) d -= Math.PI * 2;
  while (d < -Math.PI) d += Math.PI * 2;
  return a + d * t;
}

function samplePath(path, p) {
  const clamped = Math.max(0, Math.min(1, p));
  let i = 0;
  while (i < path.length - 2 && clamped > path[i + 1].at) i++;
  const a = path[i], b = path[i + 1];
  const span = b.at - a.at || 1;
  const t = easeInOut(Math.max(0, Math.min(1, (clamped - a.at) / span)));
  const A = PRESET_SPHERICAL[a.preset], B = PRESET_SPHERICAL[b.preset];
  return {
    radius: A.radius + (B.radius - A.radius) * t,
    theta: lerpAngle(A.theta, B.theta, t),
    phi: A.phi + (B.phi - A.phi) * t,
    fov: A.fov + (B.fov - A.fov) * t
  };
}

export function mountScrollMark(THREE, opts) {
  const {
    canvas,
    track,
    path = DEFAULT_PATH,
    background = null,
    damping = 0.075,
    exposure = 1.25,
    spin = 0,             // idle sway amplitude in radians, bounded; 0 to disable
    spinRate = 0.16,      // sway cycles per second
    OrbitControls = null
  } = opts;

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: !background });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  if (background) scene.background = new THREE.Color(background);

  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  applyLighting(THREE, scene, renderer, { exposure });
  scene.add(buildMark(THREE));

  let controls = null;
  if (OrbitControls) {
    controls = new OrbitControls(camera, canvas);
    controls.enableZoom = false;
    controls.enablePan = false;
    controls.enableDamping = true;
  }

  const state = { target: samplePath(path, 0), current: { ...samplePath(path, 0) }, elapsed: 0 };

  function resize() {
    const r = canvas.getBoundingClientRect();
    if (!r.width || !r.height) return;
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / r.height;
    camera.updateProjectionMatrix();
  }

  function progress() {
    const r = track.getBoundingClientRect();
    const total = r.height - innerHeight;
    if (total <= 0) return 0;
    return Math.max(0, Math.min(1, -r.top / total));
  }

  let visible = true;
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { rootMargin: '15%' })
      .observe(canvas);
  }

  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    requestAnimationFrame(frame);
    if (!visible) return;

    state.target = samplePath(path, progress());
    const k = reduced ? 1 : damping;
    const c = state.current, t = state.target;
    c.radius += (t.radius - c.radius) * k;
    c.phi += (t.phi - c.phi) * k;
    c.fov += (t.fov - c.fov) * k;
    c.theta = lerpAngle(c.theta, t.theta, k);

    // Bounded sway, not accumulating drift: every stop still lands on its
    // approved angle, so logo lock stays the render master and two visitors
    // scrolling the same distance see the same view.
    state.elapsed += dt;
    const sway = spin && !reduced ? Math.sin(state.elapsed * spinRate * Math.PI * 2) * spin : 0;

    const th = c.theta + sway;
    camera.position.set(
      c.radius * Math.sin(c.phi) * Math.sin(th),
      c.radius * Math.cos(c.phi),
      c.radius * Math.sin(c.phi) * Math.cos(th)
    );
    camera.fov = c.fov;
    camera.updateProjectionMatrix();
    camera.lookAt(0, 0, 0);
    camera.fov = c.fov;
    if (controls) controls.update();
    renderer.render(scene, camera);
  }

  resize();
  addEventListener('resize', resize, { passive: true });
  requestAnimationFrame(frame);

  return { renderer, scene, camera, resize, setPath: (p) => (opts.path = p) };
}
