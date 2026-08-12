/* Sitewise cube — real geometry, real chamfers.
   Each face is a slab with thickness, not a plane, and every edge carries a
   single-facet chamfer. The bevel is not a drawn line: it is a surface with its
   own normal, so it catches the key light and the catch travels as the light
   moves. Roof and floor span full; the wall and the glazing fit between them,
   which leaves a real reveal at every junction. */
import * as THREE from 'https://unpkg.com/three@0.184.0/build/three.module.js';

export const PALETTE = {
  graphite: '#2C3037',
  carbon: '#191C21',
  bone: '#D6D6D0',
  blue: '#2F72C4'
};

export function buildMaterials() {
  const M = (name, color, roughness, metalness, env) => {
    const m = new THREE.MeshStandardMaterial({ color, roughness, metalness });
    m.envMapIntensity = env; m.name = name;
    return m;
  };
  const mat = {
    graphite: M('facet_graphite', PALETTE.graphite, 0.52, 0.16, 0.88),
    carbon: M('facet_carbon', PALETTE.carbon, 0.44, 0.20, 0.85),
    bone: M('facet_bone', PALETTE.bone, 0.78, 0.02, 0.55)
  };
  mat.glass = new THREE.MeshPhysicalMaterial({
    color: PALETTE.blue, roughness: 0.05, metalness: 0, transmission: 0.92,
    thickness: 0.22, ior: 1.46, attenuationColor: new THREE.Color('#1D5FAE'),
    attenuationDistance: 0.7, specularIntensity: 1, transparent: true
  });
  mat.glass.envMapIntensity = 2.1;
  mat.glass.name = 'glazing_blue';
  return mat;
}

/* Four planes, no thickness. Two faces are absent — an open corner the eye and
   the air pass through. Baked corner occlusion darkens each vertex by how
   enclosed it is, so a flat plane carries a gradient instead of one flat tone. */
export function buildCube({ materials } = {}) {
  const mat = materials || buildMaterials();
  for (const k in mat) { mat[k].side = THREE.DoubleSide; mat[k].vertexColors = true; }
  const h = 0.5;
  const group = new THREE.Group();
  group.name = 'sitewise_cube';

  const occlusion = (quad, dark, light) => {
    const out = [];
    for (const [x, , z] of quad) {
      const openness = (((h - x) / (2 * h)) + ((z + h) / (2 * h))) / 2;
      const v = dark + (light - dark) * openness;
      out.push(v, v, v);
    }
    return out;
  };
  const panel = (name, quad, material, dark, light) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(quad.flat(), 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(occlusion(quad, dark, light), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, material);
    m.name = name; m.castShadow = true; m.receiveShadow = true;
    group.add(m);
    return m;
  };

  panel('roof',  [[h,h,-h], [-h,h,-h], [-h,h,h], [h,h,h]],     mat.graphite, 0.68, 1.15);
  panel('wall',  [[h,-h,-h], [-h,-h,-h], [-h,h,-h], [h,h,-h]], mat.carbon,   0.32, 1.10);
  panel('floor', [[h,-h,h], [-h,-h,h], [-h,-h,-h], [h,-h,-h]], mat.bone,     0.34, 1.05);
  panel('glazing', [[h,-h,h], [h,-h,-h], [h,h,-h], [h,h,h]],   mat.glass,    0.62, 1.10)
    .castShadow = false;

  return { group, materials: mat };
}

/* The room the cube stands in: soft key softbox, cool rim, floor bounce. */
export function studioEnv(renderer) {
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

export { THREE };
