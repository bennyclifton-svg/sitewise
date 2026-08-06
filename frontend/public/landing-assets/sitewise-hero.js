/**
 * SiteWise landing hero — mounts the 3D mark with the logo camera preset.
 * Falls back to the flat SVG when WebGL is unavailable or motion is reduced.
 */
import * as THREE from "three";
import {
  applyLighting,
  buildMark,
  frameCamera,
} from "/style-guide/3d/mark.js";

const canvas = document.getElementById("sw-mark-canvas");
const fallback = document.getElementById("sw-mark-fallback");

function showFallback() {
  if (canvas) canvas.hidden = true;
  if (fallback) fallback.hidden = false;
}

function webglOk() {
  try {
    const probe = document.createElement("canvas");
    return Boolean(
      probe.getContext("webgl2") ||
        probe.getContext("webgl") ||
        probe.getContext("experimental-webgl"),
    );
  } catch {
    return false;
  }
}

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!canvas || !webglOk() || reduced) {
  showFallback();
} else {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(9, 1, 0.1, 100);
  applyLighting(THREE, scene, renderer, { exposure: 1.2 });
  const mark = buildMark(THREE);
  scene.add(mark);
  frameCamera(THREE, camera, null, "logo");

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.floor(rect.width));
    const h = Math.max(1, Math.floor(rect.height));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  resize();
  addEventListener("resize", resize, { passive: true });

  let frame = 0;
  const tick = () => {
    mark.rotation.y = Math.sin(performance.now() * 0.00018) * 0.08;
    renderer.render(scene, camera);
    frame = requestAnimationFrame(tick);
  };
  tick();

  addEventListener("pagehide", () => cancelAnimationFrame(frame), { once: true });
}
