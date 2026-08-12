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
import { makeScreen } from './screens.js?v=3';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const seg = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
const easeOutBack = (p) => { const c = 1.70158, c3 = c + 1; return 1 + c3 * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
const easeInOutQuint = (p) => (p < 0.5 ? 16 * Math.pow(p, 5) : 1 - Math.pow(-2 * p + 2, 5) / 2);
// quintic body — slow start, fast middle — with a whisper of overshoot folded
// into the last stretch so the landing still has a touch of "spring" to it
const easeTumble = (p) => { const q = easeInOutQuint(p), w = clamp((p - 0.82) / 0.18, 0, 1); return lerp(q, easeOutBack(p), w * 0.55); };
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

function facetMat(map, rough, metal, env, grain, opts) {
  // opts.clearcoat: perspex-like sheen — a thin glossy layer that catches the
  // light on top of the base colour, no thickness geometry needed.
  // opts.opacityCap: caps this facet's max opacity below 1 for a subtle see-through read.
  const physical = opts && opts.clearcoat;
  const M = physical ? THREE.MeshPhysicalMaterial : THREE.MeshStandardMaterial;
  const m = new M({
    map, roughness: rough, metalness: metal, side: THREE.DoubleSide,
    transparent: true, opacity: 1,
    ...(physical ? { clearcoat: opts.clearcoat, clearcoatRoughness: opts.clearcoatRoughness ?? 0.1, ior: opts.ior ?? 1.49 } : {})
  });
  m.envMapIntensity = env;
  if (opts && opts.opacityCap != null) m.userData.opacityCap = opts.opacityCap;
  return m;
}

/* Six sectors, listed clockwise from the top of the lock hexagon — the order
   the wipe runs in. */
const SECTOR = [
  { face: 'roof',  tris: TRI_B, mat: facetMat(TEX.roof, 0.52, 0.16, 0.88) },
  { face: 'glaze', tris: TRI_A, mat: facetMat(TEX.glazeUp, 0.18, 0.10, 1.5, null, { clearcoat: 0.7, clearcoatRoughness: 0.12, opacityCap: 0.9 }) },
  { face: 'glaze', tris: TRI_B, mat: facetMat(TEX.glazeLo, 0.14, 0.08, 1.8, null, { clearcoat: 0.75, clearcoatRoughness: 0.08, opacityCap: 0.88 }) },
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

const loader = new THREE.TextureLoader();
const SRC = 'style-guide/3d/sources/';
function photo(file) {
  const t = loader.load(SRC + file, (tt) => {
    const a = tt.image.width / tt.image.height;   // cover-fit a square face
    if (a > 1) { tt.repeat.x = 1 / a; tt.offset.x = (1 - 1 / a) / 2; }
    else { tt.repeat.y = a; tt.offset.y = (1 - a) / 2; }
    tt.needsUpdate = true;
  });
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const T_TRUSS = photo('photo-truss.jpg');
const T_ATRIUM = photo('photo-atrium.jpg');

const BONE = '#D6D6D0', CARBON = '#191C21', BLUE = '#2F72C4', SKY = '#7FB0E4';

function sheetMat(map, raster) {
  return new THREE.MeshStandardMaterial({
    map, color: raster ? 0x808890 : 0xffffff, emissive: 0xffffff, emissiveMap: map,
    emissiveIntensity: raster ? 0.26 : 0.5, roughness: 0.66, metalness: 0.02,
    transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false
  });
}
function sheet(face, map, tris, lift, uvOrder, raster, inset) {
  const m = plane(face, tris, lift, uvOrder, sheetMat(map, raster), inset);
  m.renderOrder = 2;
  m.castShadow = false;
  return m;
}

/* The product itself, on two faces of the mark: the assistant on the roof,
   the workspace on the glazing. Both are canvases redrawn from the clock, so a
   seeked frame is still a deterministic frame. */
const chatScreen = makeScreen('chat');
const appScreen = makeScreen('app');
function screenMat(map) {
  return new THREE.MeshStandardMaterial({
    map, color: 0xffffff, emissive: 0xffffff, emissiveMap: map, transparent: true,
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
const SOURCES = ['Invoices read from the repository',
                 'Register mapped to cost items',
                 'Cost plan reconciled'];

/* Beat 2 turns on the vertical axis alone, so every sheet stays upright. Four
   quarter-stops: into the opening, the glazing from inside, the wall from
   outside, the glazing from outside. Photography holds the two wall stops;
   the glazing carries whole schematic sheets. */
const MIRROR = [1, 0, 3, 2];
const FULL = [
  { m: sheet('wall', T_TRUSS, null, -LIFT * 2, MIRROR, true, PANEL_INSET), raster: true },
  { m: sheet('glaze', symTex('plan', 'full', BONE, SKY, 101), null, -LIFT * 2, MIRROR, false, PANEL_INSET) },
  { m: sheet('wall', T_ATRIUM, null, LIFT * 2, null, true, PANEL_INSET), raster: true },
  { m: sheet('glaze', symTex('clauses', 'full', BONE, SKY, 113), null, LIFT * 2, null, false, PANEL_INSET) }
];

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

const front = new THREE.DirectionalLight(0xeaf0f8, 0);
front.position.set(0.6, 0.8, 3);
scene.add(front);

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

const EXTRA = [
  { col: 0xd8e4f4, theta: 1.25, y: 1.35, r: 2.0, peak: 3.4 },
  { col: 0xf4e8d4, theta: 2.55, y: -0.85, r: 2.2, peak: 2.9 },
  { col: 0xc9dcf6, theta: -1.95, y: 1.75, r: 2.4, peak: 3.1 },
  { col: 0xe6ecf6, theta: 0.35, y: -1.45, r: 1.9, peak: 2.5 }
];
const extras = EXTRA.map((e) => {
  const l = new THREE.PointLight(e.col, 0, 7, 2);
  l.position.set(Math.cos(e.theta) * e.r, e.y, Math.sin(e.theta) * e.r);
  scene.add(l);
  return l;
});

/* ---- camera ------------------------------------------------------------- */
const V = {
  open:  { dir: new THREE.Vector3(2.2, 0.32, 2.6), dist: 3.5, fov: 34 },
  lock:  { dir: new THREE.Vector3(1, 1, 1),        dist: 12.4, fov: 9 },
  front: { dir: new THREE.Vector3(0, 0, 1),        dist: 4.15, fov: 26 },
  // low enough for the key to rake, high enough that roof, floor and glazing
  // all still read — at y=0.2 the roof went edge-on and the mark stopped being
  // the mark for the whole payoff hold
  rake:  { dir: new THREE.Vector3(1.85, 0.62, 1.45), dist: 4.1, fov: 28 },
  // close enough for a screen on a face to be read, angled to favour both
  demo:  { dir: new THREE.Vector3(1.60, 1.08, 0.58), dist: 3.20, fov: 30 },
  // near square to the roof, where the composer sits, for the message exchange to read cleanly
  roof:  { dir: new THREE.Vector3(1.15, 1.85, 0.33), dist: 3.5, fov: 27 },
  // square-on to the glazing, where the workspace populates the register
  face:  { dir: new THREE.Vector3(1.35, 0.30, 0.22), dist: 3.6, fov: 27 }
};
for (const k in V) V[k].dir.normalize();

const dirTmp = new THREE.Vector3();
function place(a, b, p, panX, panY) {
  dirTmp.copy(a.dir).lerp(b.dir, p).normalize();
  camera.position.copy(dirTmp).multiplyScalar(lerp(a.dist, b.dist, p));
  camera.fov = lerp(a.fov, b.fov, p);
  camera.lookAt(0, 0, 0);
  camera.setViewOffset(W, H, panX, panY || 0, W, H);
  camera.updateProjectionMatrix();
}

const HALF = Math.PI / 2;
const WINDUP = 0.14, WINDUP_AMT = 0.12, TUMBLE = 0.8;
// one turn per loop takes the long way — an extra full revolution en route —
// purely for texture; +2π lands on the exact same face as a plain quarter-turn
const EXTRA_SPIN = { 3: Math.PI * 2 };
function yawAt(T, I) {
  // four stops. Each turn winds up opposite its direction first (a quick coil),
  // then tumbles through on a quintic-with-overshoot curve; the rest held
  const stops = [I + 0.2, I + 7.0, I + 13.8, I + 20.6, I + 26.6];
  let y = 0;
  for (let i = 1; i < stops.length; i++) {
    const target = HALF + (EXTRA_SPIN[i] || 0);
    const t1 = stops[i], t0 = t1 - WINDUP, t2 = t1 + TUMBLE;
    if (T < t0) continue;
    if (T < t1) y += -WINDUP_AMT * easeOut(seg(T, t0, t1));
    else y += lerp(-WINDUP_AMT, target, easeTumble(seg(T, t1, t2)));
  }
  return y;
}

function drawAt(T, C) {
  // Solo mode: the reveal and the invoice act only. Iteration and payoff are cut,
  // so their cues are pushed out of reach and the act ends by lifting back to the
  // roof, where the transmittal stage picks the frame up unchanged.
  const solo = !C.iteration;
  const FAR = 1e6;
  const P = C.promise;
  const I = solo ? FAR : C.iteration, Y = solo ? FAR : C.payoff, END = solo ? FAR : C.total;
  const panDoc = -250, panDemo = -320, panSide = -450;

  /* ---- camera ---------------------------------------------------------- */
  if (T < P + 31) {
    const a = easeInOut(seg(T, P + 0.7, P + 2.6));
    const g = easeInOut(seg(T, P + 5.9, P + 7.0));
    const h = easeInOut(seg(T, P + 14, P + 14.7));
    if (h > 0) place(V.roof, V.demo, h, panDemo, 24);
    else if (g > 0) place(V.lock, V.roof, g, lerp(panDoc, panDemo, g), lerp(0, 24, g));
    else place(V.open, V.lock, a, lerp(0, panDoc, a));
  } else if (solo) {
    place(V.demo, V.roof, easeInOut(seg(T, P + 38.45, P + 39.3)), panDemo, 24);
  } else if (T < I + 0.2) {
    const b = easeInOut(seg(T, P + 37.7, P + 38.8));
    place(V.demo, V.front, b, lerp(panDemo, panSide, b), lerp(24, 0, b));
  } else if (T < Y + 20) {
    const c = easeInOut(seg(T, Y - 1.5, Y + 0.8));
    const d = easeInOut(seg(T, Y + 14, Y + 17.5));
    if (d > 0) place(V.lock, V.rake, d, panSide);
    else place(V.front, V.lock, c, panSide);
  } else {
    const e = easeInOut(seg(T, END - 3.5, END));
    place(V.rake, V.open, e, lerp(panSide, 0, e));
  }

  /* ---- attitude: lock, then the vertical axis alone --------------------- */
  const settle = easeInOut(seg(T, P + 0.7, P + 2.6));
  let yaw, tilt = 0, roll = 0;
  if (T < I - 0.6) {
    yaw = lerp(-0.30, 0, settle);
  } else {
    yaw = yawAt(T, I) - 0.02 * (1 - seg(T, I - 0.6, I + 0.2));
    yaw += (2 * Math.PI - yaw) * 0;   // beat 3 arrives at a whole turn, i.e. lock
  }
  group.quaternion.setFromEuler(new THREE.Euler(tilt, yaw, roll));

  /* ---- beat 1: the clock wipe ------------------------------------------ */
  // All six sectors go, clockwise, leaving the void; then each returns in the
  // same order carrying its source. Dropping things onto a solid read as
  // stickers; taking the solid apart and rebuilding it does not.
  const OUT0 = P + 4.5, STEP_OUT = 0.12, GONE = 0.22;
  const BACK0 = P + 5.7, STEP_IN = 0.12, COMEBACK = 0.24;
  SECTOR.forEach((s, i) => {
    const gone = seg(T, OUT0 + i * STEP_OUT, OUT0 + i * STEP_OUT + GONE);
    const back = seg(T, BACK0 + i * STEP_IN, BACK0 + i * STEP_IN + COMEBACK);
    s.mat.opacity = (1 - gone * (1 - back)) * (s.mat.userData.opacityCap ?? 1);
    s.mesh.visible = s.mat.opacity > 0.004;
  });

  /* ---- the screens ------------------------------------------------------ */
  const DEMO0 = P + 6.6, DEMO_LEN = 32;
  const td = clamp(T - DEMO0, 0, DEMO_LEN);
  chatScreen.draw(T < Y ? td : DEMO_LEN);
  appScreen.draw(T < Y ? td : DEMO_LEN);
  SEG.forEach((sc, i) => {
    let o = easeOut(seg(T, DEMO0 - 0.5 + i * 0.25, DEMO0 + 0.2 + i * 0.25))
      * (1 - easeInOut(seg(T, P + 39.0, P + 39.9)));
    o = Math.max(o, pulse(T, Y + 3.0 + i * 3.4, Y + 9.5 + i * 3.4) * 0.95);
    sc.m.material.opacity = o;
    sc.m.visible = o > 0.002;
  });

  /* ---- light ----------------------------------------------------------- */
  const sweep = easeInOut(seg(T, P + 0.25, P + 1.9));
  let theta = lerp(-2.72, -0.62, sweep);
  let radius = lerp(2.35, 1.55, sweep);
  let ay = lerp(0.12, 1.15, easeOut(seg(T, P + 0.4, P + 2.0)));

  // the last six seconds hand the rig back to the opening frame, so it loops
  const back = easeInOut(seg(T, END - 4.5, END - 0.15));
  // the film opens unlit, so it has to close unlit or the loop jump-cuts. This
  // runs after the copy has cleared, which is what the earlier fade did not.
  const out = easeInOut(seg(T, END - 2.4, END - 0.1));
  const hard = easeInOut(seg(T, Y + 14, Y + 16)) * (1 - back);
  theta = lerp(theta, -1.15, hard);
  radius = lerp(radius, 3.4, hard);
  ay = lerp(ay, 2.6, hard);
  aperture.position.set(Math.cos(theta) * radius, ay, Math.sin(theta) * radius);
  aperture.distance = lerp(8, 22, hard);
  aperture.intensity = lerp(0, 17, easeOut(seg(T, P + 0.25, P + 1.3))) * lerp(1, 4.6, hard) * (1 - out);
  // a brief flare on each quarter-turn — the punch a snap-turn earns
  const turnPunch = solo ? 0 : Math.max(
    pulse(T, I + 0.05, I + 0.55), pulse(T, I + 6.85, I + 7.35),
    pulse(T, I + 13.65, I + 14.15), pulse(T, I + 20.45, I + 20.95));
  aperture.intensity *= 1 + turnPunch * 0.4;

  // a soft settle "bloom" right as each turn lands — a separate, quieter accent
  // from the pre-turn flare above, read in the reflections rather than the key light
  const LAND = TUMBLE;
  const settleBloom = solo ? 0 : Math.max(
    pulse(T, I + 7.0 + LAND, I + 7.0 + LAND + 0.18), pulse(T, I + 13.8 + LAND, I + 13.8 + LAND + 0.18),
    pulse(T, I + 20.6 + LAND, I + 20.6 + LAND + 0.18), pulse(T, I + 26.6 + LAND, I + 26.6 + LAND + 0.18));

  // suppressed well before the turn into the first stop — square behind a
  // presented plane it burns straight through it
  const facing = clamp(easeInOut(seg(T, I - 3.0, I - 0.8)) - easeInOut(seg(T, Y - 2, Y + 0.4)), 0, 1);
  interior.intensity = lerp(0, 1.6, easeOut(seg(T, P + 1.4, P + 2.4)))
    * (1 - 0.9 * facing) * (1 - hard) * (1 - out);
  hemi.intensity = lerp(0, 0.10, seg(T, P + 1.7, P + 2.8)) * (1 - out);
  fill.intensity = lerp(0, 0.30, easeOut(seg(T, P + 1.9, P + 3.0))) * (1 - 0.72 * hard) * (1 - out);
  rim.intensity = lerp(0, 0.22, easeOut(seg(T, P + 2.2, P + 3.2))) * (1 - 0.55 * hard) * (1 - out);
  scene.environmentIntensity = lerp(0, 1, easeOut(seg(T, P + 1.0, P + 2.8))) * lerp(1, 0.66, hard) * (1 - out) * (1 + settleBloom * 0.15);

  extras.forEach((l, i) => {
    const on = easeOut(seg(T, I + 4 + i * 6.2, I + 5.8 + i * 6.2));
    const off = easeInOut(seg(T, Y - 1, Y + 2));
    l.intensity = EXTRA[i].peak * on * (1 - off);
  });

  const stops = [I + 0.2, I + 7.0, I + 13.8, I + 20.6];
  const irr = extras.reduce((a, l, i) => a + l.intensity / EXTRA[i].peak, 0) / extras.length;
  FULL.forEach((f, i) => {
    // the first stop arrives as the turn does; a bare lit plane is not a frame
    const on = i === 0 ? stops[0] - 0.5 : stops[i] + 0.9;
    const off = i === FULL.length - 1 ? Y - 0.6 : stops[i] + 5.9;
    const o = easeOut(seg(T, on, on + 0.7)) * (1 - easeInOut(seg(T, off, off + 0.7)));
    f.m.material.opacity = o;
    if (f.raster) {
      f.m.material.emissiveIntensity = lerp(0.26, 0.07, irr);
      f.m.material.color.setScalar(lerp(0.50, 0.17, irr));
    }
    f.m.visible = o > 0.002;
  });
  front.intensity = lerp(1.15, 0.42, irr) * easeInOut(seg(T, I - 0.6, I + 1.2))
    * (1 - easeInOut(seg(T, Y - 2, Y + 0.8)));

  // in solo mode the exposure holds where the transmittal stage holds it, so the
  // hand-off is a light change of nothing at all
  const demoDim = solo ? easeInOut(seg(T, P + 5.6, P + 7.2))
    : clamp(easeInOut(seg(T, P + 5.6, P + 7.2)) - easeInOut(seg(T, P + 39, P + 40)), 0, 1);
  renderer.toneMappingExposure = lerp(1, 0.84, demoDim)
    * lerp(0.35, 1.25, easeOut(seg(T, P + 0.3, P + 2.2)))
    * lerp(1, 1.12, hard) * lerp(1, 0.28, out);

  renderer.render(scene, camera);
}

window.SitewiseFilmCube = { canvas, drawAt, sources: SOURCES };
