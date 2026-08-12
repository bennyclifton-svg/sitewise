/* Procedural surfaces for the cube's faces — concrete, timber veneer, brushed
   metal. Generated rather than photographed: they tile seamlessly, cost nothing
   to ship, and are tuned by number rather than by hunting for a scan.

   Each returns a roughness map and a bump map, so the texture is read by the
   moving key light rather than painted into the colour. The albedo overlay is
   deliberately weak — at these amplitudes the material only shows when light
   rakes across it, which is the point. */
import * as THREE from 'https://unpkg.com/three@0.184.0/build/three.module.js';

const R = 1024;

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* Value-noise fbm on wrapped grids, so every octave tiles. */
function makeFbm(seed, baseG, octaves, persistence) {
  const rnd = mulberry32(seed);
  const grids = [];
  for (let o = 0; o < octaves; o++) {
    const G = baseG << o;
    const a = new Float32Array(G * G);
    for (let i = 0; i < a.length; i++) a[i] = rnd();
    grids.push({ G, a });
  }
  const at = (a, G, x, y) => a[(((y % G) + G) % G) * G + (((x % G) + G) % G)];
  return (u, v) => {
    let sum = 0, amp = 1, norm = 0;
    for (const { G, a } of grids) {
      const x = u * G, y = v * G;
      const x0 = Math.floor(x), y0 = Math.floor(y);
      let fx = x - x0, fy = y - y0;
      fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
      const a00 = at(a, G, x0, y0), a10 = at(a, G, x0 + 1, y0);
      const a01 = at(a, G, x0, y0 + 1), a11 = at(a, G, x0 + 1, y0 + 1);
      sum += amp * ((a00 + (a10 - a00) * fx) + ((a01 + (a11 - a01) * fx) - (a00 + (a10 - a00) * fx)) * fy);
      norm += amp; amp *= persistence;
    }
    return sum / norm;
  };
}

/* height(u,v) → 0..1, per material ------------------------------------------ */
const FIELD = {
  // Concrete-hatch: a staggered lattice of soft-edged dots, the aggregate
  // symbol from a material section drawing rather than a scanned surface.
  concrete() {
    const cols = 11, rows = 11, r = 0.30;
    return (u, v) => {
      let fx = u * cols, fy = v * rows;
      fx += (Math.floor(fy) % 2) ? 0.5 : 0;
      const cu = (fx % 1) - 0.5, cv = (fy % 1) - 0.5;
      const d = Math.sqrt(cu * cu + cv * cv);
      return d < r ? 1 - (d / r) * 0.65 : 0.5;
    };
  },
  // Timber-hatch: clean flowing grain lines, gently warped by a smooth sine
  // rather than noise — drafted grain, not a photograph of it.
  timber() {
    const freq = 13;
    return (u, v) => {
      const warp = Math.sin(v * Math.PI * 3.4) * 0.04 + Math.sin(u * 9) * 0.015;
      const ring = 0.5 + 0.5 * Math.sin(2 * Math.PI * (freq * v + warp * freq));
      const grain = Math.pow(ring, 3.2);
      return 0.5 + (grain - 0.5) * 0.9;
    };
  },
  // Metal-hatch: evenly spaced 45° lines, the standard steel section symbol.
  metal() {
    const freq = 30, halfWidth = 0.06;
    return (u, v) => {
      const f = ((u + v) * freq) % 1;
      const distToCenter = Math.min(f, 1 - f);
      const line = distToCenter < halfWidth ? 1 - distToCenter / halfWidth : 0;
      return 0.5 + line * 0.6;
    };
  }
};

/* metal wants its noise smeared along the brush direction; sampling v at a high
   integer multiple and u at a low one does that while staying tileable */
const STRETCH = { concrete: [1, 1], timber: [1, 1], metal: [1, 1] };

const TUNE = {
  concrete: { rough: 0.24, bump: 0.0075, albedo: 0.34 },
  timber:   { rough: 0.16, bump: 0.0038, albedo: 0.26 },
  metal:    { rough: 0.28, bump: 0.0042, albedo: 0.30 }
};

const cache = new Map();

export function surface(kind) {
  if (cache.has(kind)) return cache.get(kind);

  const height = FIELD[kind]();
  const [su, sv] = STRETCH[kind];

  const hc = document.createElement('canvas');
  hc.width = hc.height = R;
  const hx = hc.getContext('2d');
  const img = hx.createImageData(R, R);
  const d = img.data;
  const raw = new Float32Array(R * R);

  for (let y = 0; y < R; y++) {
    for (let x = 0; x < R; x++) {
      const i = y * R + x;
      const u = (x / R) * su % 1, v = (y / R) * sv % 1;
      let h = height(u, v, i);
      h = Math.max(0, Math.min(1, h));
      raw[i] = h;
      const c = (h * 255) | 0;
      d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = c;
      d[i * 4 + 3] = 255;
    }
  }
  hx.putImageData(img, 0, 0);

  // roughness: centred on 0.90 so the material's own value is preserved on
  // average, with the texture pulling it either side
  const rc = document.createElement('canvas');
  rc.width = rc.height = R;
  const rxc = rc.getContext('2d');
  const rimg = rxc.createImageData(R, R);
  const rd = rimg.data;
  const amp = TUNE[kind].rough;
  for (let i = 0; i < raw.length; i++) {
    const val = Math.max(0, Math.min(1, 0.90 + (raw[i] - 0.5) * 2 * amp));
    const c = (val * 255) | 0;
    rd[i * 4] = rd[i * 4 + 1] = rd[i * 4 + 2] = c;
    rd[i * 4 + 3] = 255;
  }
  rxc.putImageData(rimg, 0, 0);

  const mk = (canvas, srgb) => {
    const t = new THREE.CanvasTexture(canvas);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 16;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    return t;
  };

  const out = {
    heightCanvas: hc,
    bumpMap: mk(hc, false),
    roughnessMap: mk(rc, false),
    bumpScale: TUNE[kind].bump,
    albedo: TUNE[kind].albedo,
    // material.roughness is divided by the map's mean so the average is unchanged
    roughCorrect: 1 / 0.90
  };
  cache.set(kind, out);
  return out;
}

/* Paint the grain into a face's colour texture — overlay blend, weak alpha, so
   the palette value is untouched and only the fine structure carries. */
export function grainOverlay(ctx, size, kind) {
  const s = surface(kind);
  ctx.save();
  ctx.globalCompositeOperation = 'overlay';
  ctx.globalAlpha = s.albedo;
  ctx.drawImage(s.heightCanvas, 0, 0, size, size);
  ctx.restore();
}
