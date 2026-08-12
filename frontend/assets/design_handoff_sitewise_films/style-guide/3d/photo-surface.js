/* Real photographic surfaces (concrete, brushed metal) layered under the
   procedural ones in surfaces.js. Height/roughness feed the same "centred on
   the material's own value" remap those use, so amplitude stays comparable;
   the colour photo is blended over the face's baked gradient once it loads,
   at low alpha — an accent on the palette, not a swap for it. */
import * as THREE from 'https://unpkg.com/three@0.184.0/build/three.module.js';

const R = 1024;
const cache = new Map();

function loadImg(url) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = rej;
    img.src = url;
  });
}

function drawCover(ctx, img, size) {
  const s = Math.max(size / img.width, size / img.height);
  const w = img.width * s, h = img.height * s;
  ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);
}

/* Same shape as surfaces.js#surface(): a bumpMap + roughnessMap pair, centred
   on 0.90 so the material's own roughness value survives on average. Built
   from real height/roughness photos instead of procedural noise. The colour
   photo is exposed via whenColorReady() for the caller to blend into its own
   face texture once it loads. */
export function photoSurface(kind, urls, tune) {
  if (cache.has(kind)) return cache.get(kind);

  const blank = () => { const c = document.createElement('canvas'); c.width = c.height = R; return c; };
  const bumpTex = new THREE.CanvasTexture(blank());
  const roughTex = new THREE.CanvasTexture(blank());
  [bumpTex, roughTex].forEach((t) => { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 16; });

  let resolveColor;
  const colorReady = new Promise((res) => { resolveColor = res; });

  const state = {
    bumpMap: bumpTex, roughnessMap: roughTex, bumpScale: tune.bump,
    albedo: tune.albedo, roughCorrect: 1 / 0.90,
    whenColorReady(fn) { colorReady.then(fn); }
  };

  Promise.all([loadImg(urls.height), loadImg(urls.roughness)]).then(([heightImg, roughImg]) => {
    const hc = blank();
    drawCover(hc.getContext('2d'), heightImg, R);
    bumpTex.image = hc; bumpTex.needsUpdate = true;

    const rc = blank();
    const rx = rc.getContext('2d');
    drawCover(rx, roughImg, R);
    const rd = rx.getImageData(0, 0, R, R);
    const amp = tune.rough;
    for (let i = 0; i < rd.data.length; i += 4) {
      const lum = rd.data[i] / 255;
      const v = Math.max(0, Math.min(1, 0.90 + (lum - 0.5) * 2 * amp));
      const c = (v * 255) | 0;
      rd.data[i] = rd.data[i + 1] = rd.data[i + 2] = c;
    }
    rx.putImageData(rd, 0, 0);
    roughTex.image = rc; roughTex.needsUpdate = true;
  });

  loadImg(urls.color).then(resolveColor);

  cache.set(kind, state);
  return state;
}
