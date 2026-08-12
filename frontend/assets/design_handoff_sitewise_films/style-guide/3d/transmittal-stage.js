/* Deterministic render harness for the film. Every visible property is a pure
   function of the authored clock T; drawAt(T) is called synchronously from the
   composition's render, so a seeked frame and an exported frame are the same.

   The faces are the mark's own faces: mark.svg's gradients baked to texture,
   the glazing carried as two tones rather than one, and each seam given the
   treatment it earned in the flat mark — light catch on the convex roof/glazing
   corner, shade only at the concave floor/glazing corner, a symmetric feather
   on the glazing's diagonal (one plane, two tones, not an edge), faint chamfer
   highlights on the two cut edges of the open corner. Real light then plays
   over all of it. */
import { THREE } from './cube-geometry.js';
import { surface, grainOverlay } from './surfaces.js';
import { makeScreen } from './transmittal-screens.js?v=5';
import { makeProfileScreen } from './profile-screens.js?v=20';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const seg = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
const pulse = (t, a, b) => Math.sin(seg(t, a, b) * Math.PI);

const W = 1920, H = 1080;

const canvas = document.createElement('canvas');
canvas.width = W; canvas.height = H;
canvas.style.width = canvas.style.height = '100%';
canvas.style.display = 'block';

const renderer = new THREE.WebGLRenderer({
  canvas, antialias: true, alpha: true, preserveDrawingBuffer: true
});
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.setClearColor(0x000000, 0);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, W / H, 0.1, 200);
const group = new THREE.Group();
group.name = 'sitewise_cube';
scene.add(group);

/* ---- the room the cube stands in --------------------------------------- */
function studioEnv() {
  const c = document.createElement('canvas');
  c.width = 1024; c.height = 512;
  const x = c.getContext('2d');
  const bg = x.createLinearGradient(0, 0, 0, 512);
  bg.addColorStop(0, '#1a1e26'); bg.addColorStop(0.48, '#0b0d11');
  bg.addColorStop(0.52, '#15171c'); bg.addColorStop(1, '#2a2d33');
  x.fillStyle = bg; x.fillRect(0, 0, 1024, 512);
  const blob = (cx, cy, rx, ry, col, a) => {
    const g = x.createRadialGradient(cx, cy, 0, cx, cy, Math.max(rx, ry));
    g.addColorStop(0, col); g.addColorStop(1, 'rgba(0,0,0,0)');
    x.save(); x.globalAlpha = a; x.translate(cx, cy);
    x.scale(rx / Math.max(rx, ry), ry / Math.max(rx, ry));
    x.translate(-cx, -cy); x.fillStyle = g; x.fillRect(0, 0, 1024, 512); x.restore();
  };
  blob(300, 110, 300, 190, '#ffffff', 1);
  blob(760, 170, 190, 150, '#9fc4ee', 0.55);
  blob(520, 470, 460, 130, '#c9d4e2', 0.28);
  const tex = new THREE.CanvasTexture(c);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromEquirectangular(tex).texture;
  pmrem.dispose(); tex.dispose();
  return env;
}
scene.environment = studioEnv();

/* ---- face textures, straight off mark.svg ------------------------------- */
const S = 512;
// edges: {t,r,b,l} → +n light catch, -n contact shade, magnitude = mark.svg alpha
// grain: concrete | timber | metal — laid in under the seam bevels, never over
function faceTex(stops, edges, grain, photo) {
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const x = c.getContext('2d');
  const g = x.createLinearGradient(S * 0.08, 0, S * 0.95, S);
  stops.forEach(([o, col]) => g.addColorStop(o, col));
  x.fillStyle = g; x.fillRect(0, 0, S, S);
  if (grain) grainOverlay(x, S, grain);

  const band = S * 0.020;
  const put = (edge, v) => {
    if (!v) return;
    const lit = v > 0;
    const col = lit ? '255,255,255' : '8,10,14';
    const a = Math.abs(v);
    let gr;
    if (edge === 't') gr = x.createLinearGradient(0, 0, 0, band);
    if (edge === 'b') gr = x.createLinearGradient(0, S, 0, S - band);
    if (edge === 'l') gr = x.createLinearGradient(0, 0, band, 0);
    if (edge === 'r') gr = x.createLinearGradient(S, 0, S - band, 0);
    gr.addColorStop(0, `rgba(${col},${a})`);
    gr.addColorStop(1, `rgba(${col},0)`);
    x.fillStyle = gr;
    if (edge === 't') x.fillRect(0, 0, S, band);
    if (edge === 'b') x.fillRect(0, S - band, S, band);
    if (edge === 'l') x.fillRect(0, 0, band, S);
    if (edge === 'r') x.fillRect(S - band, 0, band, S);
  };
  put('t', edges.t); put('r', edges.r); put('b', edges.b); put('l', edges.l);

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 16;
  if (photo) photo.whenColorReady((img) => {
    x.save();
    x.globalCompositeOperation = 'overlay';
    x.globalAlpha = photo.albedo;
    const s = Math.max(S / img.width, S / img.height);
    x.drawImage(img, (S - img.width * s) / 2, (S - img.height * s) / 2, img.width * s, img.height * s);
    x.restore();
    t.needsUpdate = true;
  });
  return t;
}

const TEX_SRC = 'style-guide/3d/sources/';

const TEX = {
  roof: faceTex([[0, '#454B55'], [0.55, '#2C3037'], [1, '#1B1E23']],
    { t: 0.15, l: 0.15, r: -0.13, b: -0.06 }), // cut edge lit, convex seam shaded
  floor: faceTex([[0, '#EFEFEC'], [1, '#B9B9B3']],
    { t: 0.11, l: 0.11, r: -0.15, b: -0.08 }), // concave corner takes shade only
  glazeUp: faceTex([[0, '#123564'], [1, '#0A1F3E']],
    { t: 0.18, l: 0.18, b: -0.17, r: -0.07 }), // the light catch, at its 0.32 cap
  glazeLo: faceTex([[0, '#3A80D2'], [1, '#1F5DAB']],
    { t: -0.17, l: 0.10, b: -0.11, r: -0.07 }), // feathered against the tone above
  wall: faceTex([[0, '#23272E'], [1, '#141619']],
    { t: 0.10, l: 0.08, r: -0.10, b: -0.07 }) // rear face — the counterintuitive grain
};

/* ---- geometry: four planes, six sectors -------------------------------- */
const h = 0.5, LIFT = 0.006;
const FACE = {
  roof:  { quad: [[h,h,-h], [-h,h,-h], [-h,h,h], [h,h,h]],     n: [0, 1, 0] },
  wall:  { quad: [[h,-h,-h], [-h,-h,-h], [-h,h,-h], [h,h,-h]], n: [0, 0, -1] },
  floor: { quad: [[h,-h,h], [-h,-h,h], [-h,-h,-h], [h,-h,-h]], n: [0, -1, 0] },
  glaze: { quad: [[h,-h,h], [h,-h,-h], [h,h,-h], [h,h,h]],     n: [1, 0, 0] }
};
const UV = [[0, 0], [1, 0], [1, 1], [0, 1]];
// The lock hexagon's diagonals run through the vertex nearest the camera (index 3)
const TRI_A = [1, 2, 3], TRI_B = [1, 3, 0];

function plane(face, tris, lift, uvOrder, material, inset) {
  const { quad, n } = FACE[face];
  const pos = [], uvs = [];
  // shrink toward the face centre, in-plane only, so an overlay panel stops
  // short of where the base cube's soft-cornered edge shading begins
  const s = 1 - (inset || 0);
  const cx = (quad[0][0] + quad[1][0] + quad[2][0] + quad[3][0]) / 4;
  const cy = (quad[0][1] + quad[1][1] + quad[2][1] + quad[3][1]) / 4;
  const cz = (quad[0][2] + quad[1][2] + quad[2][2] + quad[3][2]) / 4;
  for (let i = 0; i < 4; i++) {
    const px = cx + (quad[i][0] - cx) * s, py = cy + (quad[i][1] - cy) * s, pz = cz + (quad[i][2] - cz) * s;
    pos.push(px + n[0] * lift, py + n[1] * lift, pz + n[2] * lift);
    const u = UV[(uvOrder || [0, 1, 2, 3])[i]];
    uvs.push(u[0], u[1]);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  g.setIndex(tris || [0, 1, 2, 0, 2, 3]);
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, material);
  m.castShadow = true; m.receiveShadow = true;
  group.add(m);
  return m;
}

function facetMat(map, rough, metal, env) {
  const m = new THREE.MeshStandardMaterial({
    map, roughness: rough, metalness: metal, side: THREE.DoubleSide,
    transparent: true, opacity: 1
  });
  m.envMapIntensity = env;
  return m;
}

/* Six sectors, listed clockwise from the top of the lock hexagon — the order
   the wipe runs in. */
const SECTOR = [
  { face: 'roof',  tris: TRI_B, mat: facetMat(TEX.roof, 0.52, 0.16, 0.88) },
  { face: 'glaze', tris: TRI_A, mat: facetMat(TEX.glazeUp, 0.18, 0.10, 1.5) },
  { face: 'glaze', tris: TRI_B, mat: facetMat(TEX.glazeLo, 0.14, 0.08, 1.8) },
  { face: 'floor', tris: null,  mat: facetMat(TEX.floor, 0.78, 0.02, 0.55) },
  { face: 'wall',  tris: null,  mat: facetMat(TEX.wall, 0.44, 0.20, 0.85) },
  { face: 'roof',  tris: TRI_A, mat: facetMat(TEX.roof, 0.52, 0.16, 0.88) }
];
SECTOR.forEach((s) => { s.mesh = plane(s.face, s.tris, 0, null, s.mat); });

/* ---- symbolic sources ---------------------------------------------------
   Real scans mapped onto a facet read as a photograph of paper stuck to a
   solid, and a square image cut by a triangle looks like an accident. These are
   drawn instead: schematic artefacts in the brand's own ink, composed to fill
   the wedge they sit in, so the shape is deliberate. Each one stands for a KIND
   of information rather than a particular document. */
const rng = (seed) => { let a = seed >>> 0; return () => {
  a = (a + 0x6D2B79F5) | 0;
  let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}; };

const N = 1024;
function symTex(kind, region, ink, accent, seed) {
  const c = document.createElement('canvas');
  c.width = c.height = N;
  const x = c.getContext('2d');
  const r = rng(seed);
  const pad = N * 0.06;
  // the visible wedge in canvas space, so nothing is ever drawn into a corner
  // that the triangle cuts off
  const tri = region === 'A' ? [[N, N], [N, 0], [0, 0]]
            : region === 'B' ? [[N, N], [0, 0], [0, N]] : null;
  const span = (y) => region === 'A' ? [y + pad, N - pad]
                    : region === 'B' ? [pad, y - pad] : [pad, N - pad];
  const clip = () => {
    if (!tri) return;
    x.beginPath(); x.moveTo(tri[0][0], tri[0][1]);
    x.lineTo(tri[1][0], tri[1][1]); x.lineTo(tri[2][0], tri[2][1]);
    x.closePath(); x.clip();
  };
  const bar = (x0, y0, w, hh, alpha) => {
    x.globalAlpha = alpha; x.fillRect(x0, y0, w, hh); x.globalAlpha = 1;
  };
  x.fillStyle = ink; x.strokeStyle = ink; x.lineCap = 'butt';

  const rows = (fn, step) => {
    for (let y = pad; y < N - pad; y += step) {
      const [x0, x1] = span(y);
      if (x1 - x0 < N * 0.14) continue;
      fn(y, x0, x1 - x0);
    }
  };

  if (kind === 'clauses') {
    let i = 0;
    rows((y, x0, w) => {
      if (i % 5 === 0) {
        x.fillStyle = accent; bar(x0, y, w * (0.30 + r() * 0.16), 9, 0.95);
        x.fillStyle = ink;
      } else {
        bar(x0 + w * 0.055, y, w * (0.40 + r() * 0.55), 5, 0.30 + r() * 0.28);
      }
      i++;
    }, 26);
  }

  if (kind === 'ledger') {
    let i = 0;
    rows((y, x0, w) => {
      bar(x0, y, w * (0.26 + r() * 0.30), 5, 0.34 + r() * 0.24);
      const vw = w * (0.10 + r() * 0.07);
      bar(x0 + w - vw, y, vw, 5, 0.62);
      if (i % 6 === 5) bar(x0, y + 13, w, 1.4, 0.30);
      i++;
    }, 30);
    // the line every cost plan ends on
    const yl = region === 'B' ? N - pad - 46 : pad + 46;
    const [lx, lr] = span(yl);
    x.fillStyle = accent;
    bar(lx + (lr - lx) * 0.62, yl, (lr - lx) * 0.38, 11, 1);
  }

  if (kind === 'schedule') {
    x.save(); clip();
    x.fillStyle = ink;
    for (let g = pad; g < N; g += N * 0.085) bar(g, 0, 1, N, 0.13);
    let i = 0;
    rows((y, x0, w) => {
      const off = r() * w * 0.45;
      const len = w * (0.22 + r() * 0.5);
      x.fillStyle = i % 4 === 1 ? accent : ink;
      bar(x0 + off, y, Math.min(len, w - off), 11, i % 4 === 1 ? 0.95 : 0.30 + r() * 0.3);
      i++;
    }, 34);
    x.restore();
  }

  if (kind === 'plan') {
    x.save(); clip();
    x.fillStyle = ink;
    for (let g = 0; g < N; g += N * 0.05) { bar(g, 0, 1, N, 0.10); bar(0, g, N, 1, 0.10); }
    x.lineWidth = 7; x.globalAlpha = 0.72;
    // orthogonal walls: a plan is rectangles inside rectangles
    const boxes = [[0.10, 0.10, 0.80, 0.72], [0.16, 0.18, 0.34, 0.30],
                   [0.56, 0.18, 0.26, 0.22], [0.16, 0.54, 0.62, 0.22]];
    boxes.forEach(([bx, by, bw, bh]) => x.strokeRect(bx * N, by * N, bw * N, bh * N));
    x.lineWidth = 2.5; x.globalAlpha = 0.42;
    for (let i = 0; i < 26; i++) {           // hatch to one room
      const t = i / 26;
      x.beginPath();
      x.moveTo(0.56 * N + t * 0.26 * N, 0.18 * N);
      x.lineTo(0.56 * N + t * 0.26 * N - 0.05 * N, 0.40 * N);
      x.stroke();
    }
    x.globalAlpha = 0.85; x.lineWidth = 2;   // dimension line with end ticks
    x.beginPath(); x.moveTo(0.10 * N, 0.88 * N); x.lineTo(0.90 * N, 0.88 * N);
    x.moveTo(0.10 * N, 0.855 * N); x.lineTo(0.10 * N, 0.905 * N);
    x.moveTo(0.90 * N, 0.855 * N); x.lineTo(0.90 * N, 0.905 * N); x.stroke();
    x.fillStyle = accent; bar(0.42 * N, 0.855 * N, 0.16 * N, 6, 1);
    x.restore();
  }

  if (kind === 'sketch') {
    x.save(); clip();
    x.strokeStyle = ink; x.lineCap = 'round'; x.lineJoin = 'round';
    const wob = (x0, y0, x1, y1, amp, w, alpha) => {
      x.globalAlpha = alpha; x.lineWidth = w;
      x.beginPath(); x.moveTo(x0, y0);
      for (let t = 0.1; t <= 1.001; t += 0.1) {
        x.lineTo(x0 + (x1 - x0) * t + (r() - 0.5) * amp,
                 y0 + (y1 - y0) * t + (r() - 0.5) * amp);
      }
      x.stroke(); x.globalAlpha = 1;
    };
    const cx = region === 'B' ? 0.36 * N : 0.62 * N;
    const cy = region === 'B' ? 0.66 * N : 0.34 * N;
    wob(cx - 0.26 * N, cy - 0.22 * N, cx + 0.24 * N, cy - 0.24 * N, 14, 5, 0.7);
    wob(cx + 0.24 * N, cy - 0.24 * N, cx + 0.20 * N, cy + 0.20 * N, 14, 5, 0.7);
    wob(cx + 0.20 * N, cy + 0.20 * N, cx - 0.24 * N, cy + 0.22 * N, 14, 5, 0.7);
    wob(cx - 0.24 * N, cy + 0.22 * N, cx - 0.26 * N, cy - 0.22 * N, 14, 5, 0.7);
    wob(cx - 0.16 * N, cy - 0.05 * N, cx + 0.10 * N, cy + 0.02 * N, 10, 3.5, 0.45);
    x.strokeStyle = accent; x.globalAlpha = 0.95; x.lineWidth = 4;
    x.beginPath();                            // the circled note
    for (let t = 0; t <= 1.001; t += 0.04) {
      const th = t * Math.PI * 2;
      const rad = 0.115 * N + (r() - 0.5) * 9;
      const px = cx + 0.13 * N + Math.cos(th) * rad * 1.25;
      const py = cy + 0.10 * N + Math.sin(th) * rad;
      t ? x.lineTo(px, py) : x.moveTo(px, py);
    }
    x.stroke();
    wob(cx + 0.26 * N, cy + 0.20 * N, cx + 0.40 * N, cy + 0.32 * N, 8, 3.5, 0.9);
    x.restore();
  }

  if (kind === 'noise') {
    x.save(); clip();
    for (let i = 0; i < 620; i++) {
      const y = pad + r() * (N - pad * 2);
      const [x0, x1] = span(y);
      if (x1 - x0 < 30) continue;
      const w = (x1 - x0) * (0.03 + Math.pow(r(), 2.2) * 0.42);
      const px = x0 + r() * (x1 - x0 - w);
      x.fillStyle = r() > 0.90 ? accent : ink;
      bar(px, y, w, r() > 0.86 ? 7 : 3.5, 0.14 + r() * 0.5);
    }
    x.restore();
  }

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/* The product on two faces: the assistant on the roof, the workspace on the
   glazing. Both are canvases redrawn from the clock. */
const chatScreen = makeScreen('chat');
const appScreen = makeScreen('app');
function screenMat(map) {
  return new THREE.MeshStandardMaterial({
    map, color: 0xffffff, emissive: 0xffffff, emissiveMap: map,
    emissiveIntensity: 0.9, roughness: 0.9, metalness: 0,
    transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false
  });
}
const PANEL_INSET = 0.055;
const SEG = [
  { m: (() => { const m = plane('roof', null, LIFT, [1, 2, 3, 0], screenMat(chatScreen.tex), PANEL_INSET);
      m.renderOrder = 2; m.castShadow = false; return m; })() },
  { m: (() => { const m = plane('glaze', null, LIFT, null, screenMat(appScreen.tex), PANEL_INSET);
      m.renderOrder = 2; m.castShadow = false; return m; })() }
];

/* The profile sheet lives on the inner surface of the glazing. Seen from the
   open -x side the face is mirrored, so its UVs are flipped horizontally. */
const profScreen = makeProfileScreen(THREE);
const profMat = new THREE.MeshStandardMaterial({
  map: profScreen.tex, color: 0xffffff, emissive: 0xffffff, emissiveMap: profScreen.tex,
  emissiveIntensity: 1.05, roughness: 0.9, metalness: 0, side: THREE.DoubleSide,
  transparent: true, opacity: 0, depthWrite: false
});
const profMesh = plane('glaze', null, -LIFT * 2.2, [1, 0, 3, 2], profMat, PANEL_INSET);
profMesh.renderOrder = 3;
profMesh.castShadow = false;
profMesh.visible = false;

/* ---- lights ------------------------------------------------------------- */
const hemi = new THREE.HemisphereLight(0xdce6f2, 0x0a0b0e, 0);
scene.add(hemi);

const fill = new THREE.DirectionalLight(0xdfe8f5, 0);
fill.position.set(4.5, 3.2, 1.2);
fill.castShadow = true;
fill.shadow.mapSize.set(2048, 2048);
fill.shadow.bias = -0.0004;
fill.shadow.normalBias = 0.02;
Object.assign(fill.shadow.camera, { left: -1.6, right: 1.6, top: 1.6, bottom: -1.6 });
fill.shadow.camera.updateProjectionMatrix();
scene.add(fill);

// lifts the two screen faces just enough to read; aimed along the demo view
const front = new THREE.DirectionalLight(0xeaf0f8, 0);
front.position.set(2.0, 1.5, 1.0);
scene.add(front);

// aimed along the perpendicular interior view, for the profile act
const probe = new THREE.DirectionalLight(0xeaf0f8, 0);
probe.position.set(-2.6, 0.9, 0.5);
scene.add(probe);

const rim = new THREE.DirectionalLight(0x9fc4ee, 0);
rim.position.set(-3, 1.4, -3.2);
scene.add(rim);

const aperture = new THREE.PointLight(0xf2f6fb, 0, 8, 2);
aperture.castShadow = true;
aperture.shadow.mapSize.set(1024, 1024);
aperture.shadow.bias = -0.001;
scene.add(aperture);

const interior = new THREE.PointLight(0xdce6f2, 0, 2.6, 2);
interior.position.set(0.05, 0, -0.05);
scene.add(interior);

/* ---- camera ------------------------------------------------------------- */
const V = {
  open: { dir: new THREE.Vector3(2.2, 0.32, 2.6), dist: 3.5, fov: 34 },
  lock: { dir: new THREE.Vector3(1, 1, 1), dist: 12.4, fov: 9 },
  demo: { dir: new THREE.Vector3(1.60, 1.08, 0.58), dist: 3.34, fov: 30 },
  // down onto the roof, where the assistant is — near square to that face
  roof: { dir: new THREE.Vector3(1.15, 1.85, 0.33), dist: 3.5, fov: 27 },
  // square-on to the glazing from outside, for the opened draft
  face: { dir: new THREE.Vector3(1.35, 0.30, 0.22), dist: 3.6, fov: 27 },
  // square to the glazing, framed on the face rather than the cube's centre.
  // Held back to roughly the lock-in size so the left column stays clear.
  prof: { dir: new THREE.Vector3(-1, 0, 0), dist: 4.5, fov: 22, target: new THREE.Vector3(0.5, 0, 0) }
};
for (const k in V) V[k].dir.normalize();

/* The profile act is read, not just watched: the camera moves in on the sheet,
   drifts down with the fields as they populate, and pulls back for the summary
   and again at the end. */
const profView = { dir: V.prof.dir, fov: 22, dist: 4.9, target: new THREE.Vector3(0.5, 0, 0) };
function profFrame() {
  // the cube itself holds still through the act — the move happens inside the
  // face, in the sheet's own zoom and scroll
  profView.dist = 4.9;
  profView.fov = 22;
  profView.target.set(0.5, 0, 0);
  return -380;
}

const dirTmp = new THREE.Vector3(), tgtTmp = new THREE.Vector3();
const ORIGIN = new THREE.Vector3();
/* Directions are slerped, not lerped: the profile view sits opposite the roof and
   the face, and a straight lerp between near-opposite unit vectors passes through
   the origin — the camera flips through arbitrary angles on the way round. */
function slerpDir(a, b, p, out) {
  const d = clamp(a.dot(b), -1, 1);
  const om = Math.acos(d);
  if (om < 1e-3) return out.copy(b);
  const so = Math.sin(om);
  return out.copy(a).multiplyScalar(Math.sin((1 - p) * om) / so)
    .addScaledVector(b, Math.sin(p * om) / so).normalize();
}
function place(a, b, p, panX, panY) {
  tgtTmp.copy(a.target || ORIGIN).lerp(b.target || ORIGIN, p);
  slerpDir(a.dir, b.dir, p, dirTmp);
  camera.position.copy(dirTmp).multiplyScalar(lerp(a.dist, b.dist, p)).add(tgtTmp);
  camera.fov = lerp(a.fov, b.fov, p);
  camera.lookAt(tgtTmp);
  camera.setViewOffset(W, H, panX, panY || 0, W, H);
  camera.updateProjectionMatrix();
}

/* One beat. The light finds the mark, the mark opens, the work happens on two
   faces for thirty-eight seconds, then it closes back to the opening frame. */
const DEMO0 = 6.6, DEMO_LEN = 30;
const OFF = DEMO0 + DEMO_LEN;          // 36.6 — screens clear
const REG_IN = 6.0, TO_ROOF = 13.4, TO_FACE = 19.6;   // act-local camera moves
// The second act: the cube swings right round and the camera settles square to
// the inside of the glazing, where the project profile is set up twice over.
const TO_PROF = 36.4, PROF0 = 39.4, PROF_LEN = 53.6;
const PROF_END = PROF0 + PROF_LEN;     // 93.0
const SOURCES = ['Register searched', '19 basement drawings selected', 'Transmittal drafted'];

/* The act can be played out of order: the film runs the profile before the
   transmittal. Both passes are entered from, and handed back to, the parked roof
   frame the transmittal opens on (V.roof / panDemo / 24, B-local 7.6), so the
   joins are state matches rather than cuts.
     C.act = 'transmittal'  — transmittal only; closes back to the opening frame.
     C.enterAt              — absolute time to arrive from the roof frame.
     C.closeTo = 'roof'     — hand the frame back to the roof instead of closing. */
function drawAt(T, C) {
  const P = C.reveal, END = C.total;
  const panDoc = -250, panDemo = -320, panProf = -370;
  const soloT = C.act === 'transmittal';
  const ent = C.enterAt != null ? easeInOut(seg(T, C.enterAt, C.enterAt + 2.0)) : 1;
  const hand = C.closeTo === 'roof';
  const hb = hand ? easeInOut(seg(T, P + PROF_END, END - 0.1)) : 0;

  /* ---- camera ----------------------------------------------------------
     The act follows the work: down on the assistant while it is being asked,
     round to the register while it searches, back for the answer, then square
     to the glazing for the opened draft. */
  const D0 = P + DEMO0;
  const profPan = profFrame(T - (P + PROF0));
  if (ent < 1) {
    place(V.roof, profView, ent, lerp(panDemo, profPan, ent), lerp(24, 0, ent));
  } else if (soloT && T >= P + TO_PROF) {
    const e = easeInOut(seg(T, P + TO_PROF + 1.2, END - 0.1));
    place(V.face, V.open, e, lerp(panDemo, 0, e), lerp(24, 0, e));
  } else if (!soloT && T >= P + PROF_END) {
    if (hand) place(profView, V.roof, hb, lerp(profPan, panDemo, hb), lerp(0, 24, hb));
    else {
      const e = easeInOut(seg(T, P + PROF_END, END - 0.1));
      place(profView, V.open, e, lerp(profPan, 0, e));
    }
  } else if (!soloT && T >= P + TO_PROF) {
    const d = easeInOut(seg(T, P + TO_PROF, P + PROF0));
    place(V.face, profView, d, lerp(panDemo, profPan, d), lerp(24, 0, d));
  } else if (T >= D0 + TO_FACE) {
    place(V.roof, V.face, easeInOut(seg(T, D0 + TO_FACE, D0 + TO_FACE + 1.2)), panDemo, 24);
  } else if (T >= D0 + TO_ROOF) {
    place(V.demo, V.roof, easeInOut(seg(T, D0 + TO_ROOF, D0 + TO_ROOF + 1.1)), panDemo, 24);
  } else if (T >= D0 + REG_IN) {
    place(V.roof, V.demo, easeInOut(seg(T, D0 + REG_IN, D0 + REG_IN + 1.0)), panDemo, 24);
  } else {
    const a = easeInOut(seg(T, P + 0.7, P + 2.6));
    const g = easeInOut(seg(T, P + 5.9, P + 7.0));
    if (g > 0) place(V.lock, V.roof, g, lerp(panDoc, panDemo, g), lerp(0, 24, g));
    else place(V.open, V.lock, a, lerp(0, panDoc, a));
  }

  /* ---- attitude: settle to lock and stay there -------------------------- */
  const settle = easeInOut(seg(T, P + 0.7, P + 2.6));
  const spin = soloT ? 0
    : Math.sin(seg(T, P + TO_PROF, P + PROF0) * Math.PI) * -0.52
      + Math.sin(seg(T, P + PROF_END, END - 0.4) * Math.PI) * -0.34;
  group.quaternion.setFromEuler(new THREE.Euler(0, lerp(-0.30, 0, settle) + spin, 0));

  /* ---- the clock wipe --------------------------------------------------- */
  const OUT0 = P + 4.5, BACK0 = P + 5.7, STEP = 0.12;
  SECTOR.forEach((s, i) => {
    const gone = seg(T, OUT0 + i * STEP, OUT0 + i * STEP + 0.22);
    const back = seg(T, BACK0 + i * STEP, BACK0 + i * STEP + 0.24);
    s.mat.opacity = 1 - gone * (1 - back);
    s.mesh.visible = s.mat.opacity > 0.004;
  });

  /* ---- the screens ------------------------------------------------------ */
  // on the profile pass the composer is held on the transmittal's opening frame,
  // so the hand-back lands on exactly the state the next pass starts from
  const td = hand ? 1.0 : clamp(T - (P + DEMO0), 0, DEMO_LEN);
  chatScreen.draw(td);
  appScreen.draw(td);
  // the register face stays dark until the instruction is sent
  SEG.forEach((sc, i) => {
    const on = i === 0 ? P + DEMO0 - 0.5 : P + DEMO0 + REG_IN + 0.4;
    let o = easeOut(seg(T, on, on + 0.7))
      * (1 - easeInOut(seg(T, P + OFF, P + OFF + 0.9)));
    // the composer only appears once the camera is square to the roof — the
    // screen is DoubleSide, so any earlier and it reads through the face reversed
    if (hand && i === 0) o = Math.max(o, seg(T, END - 0.6, END - 0.1));
    sc.m.material.opacity = o;
    sc.m.visible = o > 0.002;
  });

  /* ---- the profile sheet ------------------------------------------------ */
  const tp = clamp(T - (P + PROF0), 0, PROF_LEN);
  // on the hand-back the sheet is held into the arc, so the swing round is not an
  // empty shell
  const profA = easeOut(seg(T, P + PROF0 - 1.6, P + PROF0 + 0.4))
    * (1 - easeInOut(hand ? seg(T, P + PROF_END + 0.2, P + PROF_END + 1.2)
      : seg(T, P + PROF_END - 1.2, P + PROF_END + 0.4)));
  profMesh.visible = !soloT && profA > 0.004;
  if (profMesh.visible) { profScreen.draw(tp); profMat.opacity = profA; }

  /* ---- light ------------------------------------------------------------ */
  const sweep = easeInOut(seg(T, P + 0.25, P + 1.9));
  const theta = lerp(-2.72, -0.62, sweep);
  const radius = lerp(2.35, 1.55, sweep);
  const ay = lerp(0.12, 1.15, easeOut(seg(T, P + 0.4, P + 2.0)));
  const out = hand ? 0 : easeInOut(seg(T, END - 2.4, END - 0.1));
  let demoDim = clamp(easeInOut(seg(T, P + 5.6, P + 7.2))
    - easeInOut(seg(T, P + OFF - 0.6, P + OFF + 0.6)), 0, 1);

  let profDim = soloT ? 0 : clamp(easeInOut(seg(T, P + OFF, P + PROF0))
    - easeInOut(seg(T, P + PROF_END - 1.0, P + PROF_END + 1.0)), 0, 1);

  // arrive from, and leave on, the roof frame's lighting
  if (ent < 1) { demoDim = lerp(1, demoDim, ent); profDim *= ent; }
  if (hand) demoDim = lerp(demoDim, 1, hb);

  aperture.position.set(Math.cos(theta) * radius, ay, Math.sin(theta) * radius);
  aperture.intensity = lerp(0, 17, easeOut(seg(T, P + 0.25, P + 1.3))) * (1 - out);
  // a brief flare at each camera move — the punch a snap-cut earns
  const turnPunch = Math.max(
    pulse(T, D0 + REG_IN - 0.2, D0 + REG_IN + 0.3), pulse(T, D0 + TO_ROOF - 0.2, D0 + TO_ROOF + 0.3),
    pulse(T, D0 + TO_FACE - 0.2, D0 + TO_FACE + 0.3));
  aperture.intensity *= 1 + turnPunch * 0.4;
  // square behind a lit screen it burns straight through, so it steps back
  interior.intensity = lerp(0, 1.6, easeOut(seg(T, P + 1.4, P + 2.4)))
    * (1 - 0.75 * demoDim) * (1 - 0.99 * profDim) * (1 - out);
  hemi.intensity = lerp(0, 0.10, seg(T, P + 1.7, P + 2.8)) * (1 - out);
  fill.intensity = lerp(0, 0.30, easeOut(seg(T, P + 1.9, P + 3.0))) * (1 - out);
  rim.intensity = lerp(0, 0.22, easeOut(seg(T, P + 2.2, P + 3.2))) * (1 - out);
  front.intensity = 0.55 * demoDim * (1 - profDim) * (1 - out);
  probe.intensity = 0.78 * profDim * (1 - out);
  scene.environmentIntensity = lerp(0, 1, easeOut(seg(T, P + 1.0, P + 2.8))) * (1 - out);

  renderer.toneMappingExposure = lerp(1, 0.84, demoDim) * lerp(1, 0.86, profDim)
    * lerp(0.35, 1.25, easeOut(seg(T, P + 0.3, P + 2.2))) * lerp(1, 0.28, out);

  renderer.render(scene, camera);
}

window.SitewiseTransmittalCube = { canvas, drawAt, sources: SOURCES };
