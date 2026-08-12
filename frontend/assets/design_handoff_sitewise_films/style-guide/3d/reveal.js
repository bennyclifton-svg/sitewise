/* <sitewise-reveal> — the mark, revealed by light rather than by motion graphics.
   The cube is present from frame zero. What changes is where the light is: a
   single point source travels around the open corner, so each plane takes its
   turn, the glazing transmits blue onto the floor, and the form only resolves
   into the logo lock once the camera has climbed to the isometric.

   Attributes: duration (s, default 5.4) · loop · key-color · idle ("drift"|"off")
   Methods:    play() — restart the sequence.                                  */
import * as THREE from 'https://unpkg.com/three@0.184.0/build/three.module.js';
import { buildCube, studioEnv } from './cube-geometry.js';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
// progress through a window of the timeline, 0 before it, 1 after
const seg = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

class SitewiseReveal extends HTMLElement {
  static get observedAttributes() { return ['duration', 'loop', 'key-color', 'keycolor', 'idle']; }

  connectedCallback() {
    if (this._built) return;
    this._built = true;
    const root = this.attachShadow({ mode: 'open' });
    root.innerHTML = '<style>:host{display:block;position:relative;width:100%;height:100%}' +
      'canvas{display:block;width:100%;height:100%}</style>';
    this._build(root);
  }

  attributeChangedCallback(name, _old, val) {
    if (!this._built) return;
    if ((name === 'key-color' || name === 'keycolor') && val) this.aperture.color.set(val);
    if (name === 'duration') this.duration = parseFloat(val) || 5.4;
  }

  get duration() { return this._dur || parseFloat(this.getAttribute('duration')) || 5.4; }
  set duration(v) { this._dur = v; }

  play() { this.t = 0; this._done = false; }

  _build(root) {
    const canvas = document.createElement('canvas');
    root.appendChild(canvas);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.0;
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    scene.environment = studioEnv(renderer);
    scene.environmentIntensity = 0;

    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);

    /* ---- lights ---------------------------------------------------------- */
    // Fill and rim stay near zero until the form has already been read; the
    // point source below is the only thing lighting the first two seconds.
    const hemi = new THREE.HemisphereLight(0xdce6f2, 0x0a0b0e, 0);
    scene.add(hemi);

    const fill = new THREE.DirectionalLight(0xdfe8f5, 0);
    fill.position.set(4.5, 3.2, 1.2);
    fill.castShadow = true;
    fill.shadow.mapSize.set(2048, 2048);
    fill.shadow.bias = -0.0004;
    fill.shadow.normalBias = 0.02;
    Object.assign(fill.shadow.camera, { left: -2, right: 2, top: 2, bottom: -2 });
    fill.shadow.camera.updateProjectionMatrix();
    scene.add(fill);

    const rim = new THREE.DirectionalLight(0x9fc4ee, 0);
    rim.position.set(-3, 1.4, -3.2);
    scene.add(rim);

    // The key. Close enough that inverse-square falloff varies measurably across
    // a single plane, so a flat face is never one flat tone.
    const aperture = new THREE.PointLight(0xf2f6fb, 0, 8, 2);
    scene.add(aperture);
    this.aperture = aperture;
    const kc = this.getAttribute('key-color') || this.getAttribute('keycolor');
    if (kc) aperture.color.set(kc);

    const interior = new THREE.PointLight(0xdce6f2, 0, 2.6, 2);
    interior.position.set(0.05, 0, -0.05);
    scene.add(interior);

    /* ---- the cube: real slabs, real chamfers (shared with the film) ---- */
    const { group } = buildCube();
    scene.add(group);

    /* ---- camera path: hero three-quarter → isometric logo lock ----------- */
    const A = { dir: new THREE.Vector3(2.2, 0.32, 2.6).normalize(), dist: 3.15, fov: 34 };
    const B = { dir: new THREE.Vector3(1, 1, 1).normalize(),        dist: 22,   fov: 9 };
    const dir = new THREE.Vector3();

    const resize = () => {
      const w = this.clientWidth || 1, ht = this.clientHeight || 1;
      renderer.setSize(w, ht, false);
      camera.aspect = w / ht;
      camera.updateProjectionMatrix();
    };
    new ResizeObserver(resize).observe(this);
    resize();

    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.t = reduced ? 99 : 0;
    let last = performance.now();

    const frame = (now) => {
      this._raf = requestAnimationFrame(frame);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const D = this.duration;
      this.t += dt;
      const t = this.t / D * 5.4; // author the timeline in seconds at D = 5.4

      /* the light arrives before anything else is visible */
      const sweep = easeInOut(seg(t, 0.25, 3.0));
      const theta = lerp(-2.72, -0.62, sweep);          // radians, around the open corner
      const radius = lerp(2.35, 1.55, sweep);
      aperture.position.set(
        Math.cos(theta) * radius,
        lerp(0.12, 1.15, easeOut(seg(t, 0.4, 3.2))),
        Math.sin(theta) * radius
      );
      aperture.intensity = lerp(0, 17, easeOut(seg(t, 0.25, 1.5))) *
                           lerp(1, 0.92, seg(t, 3.0, 4.4));

      /* the enclosure fills in only once the outside has been read */
      interior.intensity = lerp(0, 1.6, easeOut(seg(t, 1.9, 3.6)));
      hemi.intensity = lerp(0, 0.10, seg(t, 2.2, 4.2));
      fill.intensity = lerp(0, 0.28, easeOut(seg(t, 2.4, 4.4)));
      rim.intensity = lerp(0, 0.22, easeOut(seg(t, 2.8, 4.6)));
      scene.environmentIntensity = lerp(0, 1, easeOut(seg(t, 1.4, 4.2)));
      renderer.toneMappingExposure = lerp(0.35, 1.25, easeOut(seg(t, 0.3, 3.6)));

      /* the form resolves last: the camera climbs to the isometric */
      const c = easeInOut(seg(t, 0.9, 3.9));
      dir.copy(A.dir).lerp(B.dir, c).normalize();
      camera.position.copy(dir).multiplyScalar(lerp(A.dist, B.dist, c));
      camera.fov = lerp(A.fov, B.fov, c);
      camera.lookAt(0, 0, 0);
      camera.updateProjectionMatrix();
      group.rotation.y = lerp(-0.30, 0, easeInOut(seg(t, 0.9, 4.1)));

      /* settled: the sun keeps drifting, so the lock-up is never a still */
      if (t > 4.4 && this.getAttribute('idle') !== 'off') {
        const drift = Math.sin((t - 4.4) * 0.32) * 0.10;
        aperture.position.x = Math.cos(theta + drift) * radius;
        aperture.position.z = Math.sin(theta + drift) * radius;
      }

      if (t > 5.4 && !this._done) {
        this._done = true;
        this.dispatchEvent(new CustomEvent('revealed'));
      }
      if (this.hasAttribute('loop') && t > 8.4) this.play();

      renderer.render(scene, camera);
    };
    this._raf = requestAnimationFrame(frame);
  }

  disconnectedCallback() { cancelAnimationFrame(this._raf); }

}

customElements.define('sitewise-reveal', SitewiseReveal);
