/**
 * Sitewise mark — 3D master.
 *
 * Geometry, materials, lighting rig and camera presets for the mark.
 * Pass in your own THREE namespace so this module stays version-agnostic.
 * Verified against three.js r184.
 *
 *   import { buildMark, applyLighting, CAMERA_PRESETS } from './mark.js';
 *
 *   const mark = buildMark(THREE);
 *   applyLighting(THREE, scene, renderer);
 *   scene.add(mark);
 *
 * The object is modelled in metres, y-up, centred on the origin, 1m to a
 * side. Every mesh and material is named — those names become the o /
 * usemtl entries in an OBJ export and the node names in a GLB, which is
 * what keeps the download usable in Blender or C4D.
 */

const H = 0.5;

/* Four planes. Two faces (+Z and −X) are deliberately absent: an open
   corner the eye and the air pass through. */
const FACES = [
  { name: 'roof',    material: 'graphite', quad: [[H,H,-H], [-H,H,-H], [-H,H,H], [H,H,H]],     ao: [0.68, 1.15] },
  { name: 'wall',    material: 'carbon',   quad: [[H,-H,-H], [-H,-H,-H], [-H,H,-H], [H,H,-H]], ao: [0.32, 1.10] },
  { name: 'floor',   material: 'bone',     quad: [[H,-H,H], [-H,-H,H], [-H,-H,-H], [H,-H,-H]], ao: [0.34, 1.05] },
  { name: 'glazing', material: 'glass',    quad: [[H,-H,H], [H,-H,-H], [H,H,-H], [H,H,H]],     ao: [0.62, 1.10] }
];

export const MATERIALS = {
  graphite: { color: '#2C3037', roughness: 0.52, metalness: 0.16, envMapIntensity: 0.88 },
  carbon:   { color: '#191C21', roughness: 0.44, metalness: 0.20, envMapIntensity: 0.85 },
  bone:     { color: '#D6D6D0', roughness: 0.78, metalness: 0.02, envMapIntensity: 0.55 },
  glass:    {
    color: '#2F72C4', roughness: 0.05, metalness: 0,
    transmission: 0.92, thickness: 0.22, ior: 1.46,
    attenuationColor: '#1D5FAE', attenuationDistance: 0.7,
    specularIntensity: 1, envMapIntensity: 2.1
  }
};

/**
 * Baked corner occlusion.
 *
 * The enclosure is deepest along the edge where the glazing meets the
 * wall (x=+H, z=−H) and most open at the missing corner (x=−H, z=+H).
 * Each vertex is darkened by how enclosed it is, so a flat plane carries
 * a gradient instead of one uniform tone. Written into a vertex colour
 * attribute, which survives GLB export.
 */
function occlusion(quad, dark, light) {
  const out = [];
  for (const [x, , z] of quad) {
    const openness = (((H - x) / (2 * H)) + ((z + H) / (2 * H))) / 2;
    const v = dark + (light - dark) * openness;
    out.push(v, v, v);
  }
  return out;
}

export function buildMark(THREE) {
  const group = new THREE.Group();
  group.name = 'sitewise_mark';

  const made = {};
  const material = (key) => {
    if (made[key]) return made[key];
    const spec = { ...MATERIALS[key] };
    const Ctor = key === 'glass' ? THREE.MeshPhysicalMaterial : THREE.MeshStandardMaterial;
    if (spec.attenuationColor) spec.attenuationColor = new THREE.Color(spec.attenuationColor);
    if (key === 'glass') spec.transparent = true;
    const env = spec.envMapIntensity;
    delete spec.envMapIntensity;
    const m = new Ctor({ ...spec, side: THREE.DoubleSide, vertexColors: true });
    m.envMapIntensity = env;
    m.name = key === 'glass' ? 'glazing_blue' : 'facet_' + key;
    made[key] = m;
    return m;
  };

  for (const face of FACES) {
    const [v0, v1, v2, v3] = face.quad;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([...v0, ...v1, ...v2, ...v3], 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(occlusion(face.quad, ...face.ao), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    g.computeVertexNormals();
    const mesh = new THREE.Mesh(g, material(face.material));
    mesh.name = face.name;
    mesh.castShadow = face.name !== 'glazing';
    mesh.receiveShadow = true;
    group.add(mesh);
  }

  return group;
}

/**
 * Procedural studio environment: a key softbox upper-left, a cool rim
 * right, floor bounce below. Pre-filtered so the glazing and the roof
 * get real specular falloff rather than a flat wash.
 */
export function studioEnvironment(THREE, renderer) {
  const c = document.createElement('canvas');
  c.width = 1024;
  c.height = 512;
  const x = c.getContext('2d');

  const bg = x.createLinearGradient(0, 0, 0, 512);
  bg.addColorStop(0, '#1a1e26');
  bg.addColorStop(0.48, '#0b0d11');
  bg.addColorStop(0.52, '#15171c');
  bg.addColorStop(1, '#2a2d33');
  x.fillStyle = bg;
  x.fillRect(0, 0, 1024, 512);

  const blob = (cx, cy, rx, ry, col, a) => {
    const g = x.createRadialGradient(cx, cy, 0, cx, cy, Math.max(rx, ry));
    g.addColorStop(0, col);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    x.save();
    x.globalAlpha = a;
    x.translate(cx, cy);
    x.scale(rx / Math.max(rx, ry), ry / Math.max(rx, ry));
    x.translate(-cx, -cy);
    x.fillStyle = g;
    x.fillRect(0, 0, 1024, 512);
    x.restore();
  };
  blob(300, 110, 300, 190, '#ffffff', 1);     // key softbox
  blob(760, 170, 190, 150, '#9fc4ee', 0.55);  // cool rim
  blob(520, 470, 460, 130, '#c9d4e2', 0.28);  // floor bounce

  const tex = new THREE.CanvasTexture(c);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromEquirectangular(tex).texture;
  pmrem.dispose();
  tex.dispose();
  return env;
}

/**
 * The lighting rig.
 *
 * The one rule worth carrying into any other scene: directional and
 * hemisphere light both deliver constant irradiance across a flat face,
 * so no amount of either can stop a plane reading as one flat tone. The
 * key here is a POINT source with inverse-square falloff, sitting just
 * outside the open corner — light enters the enclosure the way it would
 * through a real opening. Directionals are demoted to fill.
 *
 * A physically-lit scene of this brightness clips without tone mapping;
 * ACES rolls the highlights off so the bone floor keeps its gradient.
 */
export function applyLighting(THREE, scene, renderer, opts = {}) {
  const exposure = opts.exposure ?? 1.25;

  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = exposure;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  scene.environment = studioEnvironment(THREE, renderer);

  const lights = {};

  lights.ambient = new THREE.HemisphereLight(0xdfe6f2, 0x0a0b0d, 0.10);
  scene.add(lights.ambient);

  lights.key = new THREE.DirectionalLight(0xffffff, 0.34);
  lights.key.position.set(-2.6, 3.4, 2.2);
  lights.key.castShadow = true;
  lights.key.shadow.mapSize.set(2048, 2048);
  lights.key.shadow.bias = -0.0002;
  lights.key.shadow.normalBias = 0.025;
  scene.add(lights.key);

  lights.rim = new THREE.DirectionalLight(0x9fc4ee, 0.22);
  lights.rim.position.set(-3, 1.4, -3.2);
  scene.add(lights.rim);

  lights.raking = new THREE.DirectionalLight(0xdfe8f5, 0.28);
  lights.raking.position.set(4.5, 3.2, 1.2);
  lights.raking.castShadow = true;
  lights.raking.shadow.mapSize.set(2048, 2048);
  lights.raking.shadow.bias = -0.0004;
  lights.raking.shadow.normalBias = 0.02;
  Object.assign(lights.raking.shadow.camera, { left: -2, right: 2, top: 2, bottom: -2 });
  lights.raking.shadow.camera.updateProjectionMatrix();
  scene.add(lights.raking);

  // The key. Close enough that falloff varies measurably across each plane.
  lights.aperture = new THREE.PointLight(0xf2f6fb, 17, 7, 2);
  lights.aperture.position.set(-0.8, 1.15, 0.9);
  scene.add(lights.aperture);

  // Picks out the wall and floor interiors.
  lights.interior = new THREE.PointLight(0xdce6f2, 1.6, 2.6, 2);
  lights.interior.position.set(0.05, 0, -0.05);
  scene.add(lights.interior);

  return lights;
}

/** Approved camera positions. `dir` is normalised before use. */
export const CAMERA_PRESETS = {
  logo:  { dir: [1, 1, 1],         fov: 9,  dist: 22,  note: 'Near-orthographic. The render master — reproduces the flat artwork exactly.' },
  three: { dir: [1.6, 0.9, 2.1],   fov: 30, dist: 4.4, note: 'Reads as a habitable frame.' },
  edge:  { dir: [1, 0.14, 1],      fov: 26, dist: 5.2, note: 'Near eye level, for architectural context.' },
  plan:  { dir: [0.001, 1, 0.001], fov: 12, dist: 16,  note: 'Plan view.' }
};

export function frameCamera(THREE, camera, controls, preset) {
  const v = CAMERA_PRESETS[preset];
  camera.fov = v.fov;
  camera.position.copy(new THREE.Vector3(...v.dir).normalize().multiplyScalar(v.dist));
  camera.updateProjectionMatrix();
  if (controls) {
    controls.target.set(0, 0, 0);
    controls.update();
  }
}
