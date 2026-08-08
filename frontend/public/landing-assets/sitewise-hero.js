/**
 * SiteWise landing — scroll the Mark 3 camera, then open the mark into its
 * six-sector deterministic tool geometry. The DOM owns all readable content;
 * WebGL is used only for the spatial transition.
 */
import * as THREE from "three";
import {
  applyLighting,
  buildMark,
  CAMERA_PRESETS,
} from "/style-guide/3d/mark.js";

const story = document.querySelector(".sw-mark-story");
const stage = document.querySelector(".sw-mark-stage");
const canvas = document.getElementById("sw-mark-canvas");
const fallback = document.getElementById("sw-mark-fallback");
const engine = document.querySelector(".sw-facet-engine");
const caption = document.querySelector("[data-mark-caption]");
const detail = document.querySelector("[data-mark-detail]");
const railSteps = [...document.querySelectorAll("[data-story-step]")];
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const compact = matchMedia("(max-width: 900px)").matches;

const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const smoothstep = (from, to, value) => {
  const t = clamp((value - from) / (to - from));
  return t * t * (3 - 2 * t);
};

function storyProgress() {
  if (!story || compact || reduced) return reduced ? 1 : 0;
  const rect = story.getBoundingClientRect();
  const distance = rect.height - innerHeight;
  return distance > 0 ? clamp(-rect.top / distance) : 0;
}

function phaseFor(progress) {
  if (progress < 0.18) return "source";
  if (progress < 0.48) return "mark";
  if (progress < 0.8) return "tools";
  return "issue";
}

const tokenStops = [
  { at: 0.42, x: 0, y: 0, caption: "Interpret the instruction", detail: "The model judges language, intent and document type." },
  { at: 0.52, x: -0.18, y: -0.2, caption: "Recognise and parse", detail: "Software reads pages, text and tables into known structures." },
  { at: 0.6, x: 0.18, y: -0.2, caption: "Retrieve the right evidence", detail: "Every fact remains attached to its project source." },
  { at: 0.67, x: 0.31, y: 0, caption: "Filter revisions and scope", detail: "The current project record controls what can be used." },
  { at: 0.73, x: 0.17, y: 0.22, caption: "Calculate with code", detail: "Totals, deltas and comparables never come from the model." },
  { at: 0.79, x: -0.17, y: 0.22, caption: "Validate and assemble", detail: "Completeness, consistency and issue rules are repeatable." },
  { at: 0.88, x: -0.32, y: 0, caption: "Issue through the open facet", detail: "The result remains reviewable, editable and exportable." },
];

function sampleToken(progress) {
  let index = 0;
  while (index < tokenStops.length - 2 && progress > tokenStops[index + 1].at) index += 1;
  const from = tokenStops[index];
  const to = tokenStops[index + 1];
  const t = smoothstep(from.at, to.at, progress);
  return {
    x: from.x + (to.x - from.x) * t,
    y: from.y + (to.y - from.y) * t,
    copy: t < 0.52 ? from : to,
  };
}

function updateStory(progress) {
  if (!stage) return;
  const phase = phaseFor(progress);
  const sourceOpacity = 1 - smoothstep(0.08, 0.29, progress);
  const markOpacity = smoothstep(0.12, 0.25, progress) * (1 - smoothstep(0.48, 0.64, progress));
  const engineIn = smoothstep(0.42, 0.59, progress);
  const engineOpacity = engineIn * (1 - smoothstep(0.8, 0.96, progress) * 0.72);
  const issueOpacity = smoothstep(0.78, 0.94, progress);

  stage.dataset.phase = phase;
  stage.style.setProperty("--story-progress", progress.toFixed(4));
  stage.style.setProperty("--story-progress-pct", `${(progress * 100).toFixed(2)}%`);
  stage.style.setProperty("--source-opacity", sourceOpacity.toFixed(4));
  stage.style.setProperty("--mark-opacity", markOpacity.toFixed(4));
  stage.style.setProperty("--engine-opacity", engineOpacity.toFixed(4));
  stage.style.setProperty("--issue-opacity", issueOpacity.toFixed(4));

  const token = sampleToken(progress);
  if (engine) {
    engine.style.setProperty("--token-x", `${(token.x * engine.clientWidth).toFixed(1)}px`);
    engine.style.setProperty("--token-y", `${(token.y * engine.clientHeight).toFixed(1)}px`);
  }
  if (caption) caption.textContent = progress < 0.42 ? "Read the project record" : token.copy.caption;
  if (detail) detail.textContent = progress < 0.42
    ? "Five fixed tool facets. One moving judgement facet."
    : token.copy.detail;

  railSteps.forEach((item) => {
    const active = item.dataset.storyStep === phase;
    item.classList.toggle("is-active", active);
    if (active) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
}

let requested = false;
let targetProgress = storyProgress();
let currentProgress = targetProgress;

function requestStoryUpdate() {
  targetProgress = storyProgress();
  if (requested) return;
  requested = true;
  requestAnimationFrame(() => {
    requested = false;
    currentProgress = targetProgress;
    updateStory(currentProgress);
  });
}

updateStory(currentProgress);
addEventListener("scroll", requestStoryUpdate, { passive: true });
addEventListener("resize", requestStoryUpdate, { passive: true });

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

const cameraPath = [
  { preset: "logo", at: 0 },
  { preset: "three", at: 0.38 },
  { preset: "plan", at: 0.72 },
  { preset: "logo", at: 1 },
];

function toSpherical(direction, distance) {
  const [x, y, z] = direction;
  const length = Math.hypot(x, y, z) || 1;
  const nx = (x / length) * distance;
  const ny = (y / length) * distance;
  const nz = (z / length) * distance;
  return {
    radius: distance,
    theta: Math.atan2(nx, nz),
    phi: Math.acos(clamp(ny / distance, -1, 1)),
  };
}

const sphericalPresets = Object.fromEntries(
  Object.entries(CAMERA_PRESETS).map(([name, value]) => [
    name,
    { ...toSpherical(value.dir, value.dist), fov: value.fov },
  ]),
);

function lerpAngle(from, to, amount) {
  let delta = to - from;
  while (delta > Math.PI) delta -= Math.PI * 2;
  while (delta < -Math.PI) delta += Math.PI * 2;
  return from + delta * amount;
}

function sampleCamera(progress) {
  const pathProgress = clamp((progress - 0.1) / 0.58);
  let index = 0;
  while (index < cameraPath.length - 2 && pathProgress > cameraPath[index + 1].at) index += 1;
  const fromStop = cameraPath[index];
  const toStop = cameraPath[index + 1];
  const amount = smoothstep(fromStop.at, toStop.at, pathProgress);
  const from = sphericalPresets[fromStop.preset];
  const to = sphericalPresets[toStop.preset];
  return {
    radius: from.radius + (to.radius - from.radius) * amount,
    theta: lerpAngle(from.theta, to.theta, amount),
    phi: from.phi + (to.phi - from.phi) * amount,
    fov: from.fov + (to.fov - from.fov) * amount,
  };
}

if (!canvas || !webglOk() || reduced || compact) {
  showFallback();
} else {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(12, 1, 0.1, 100);
  applyLighting(THREE, scene, renderer, { exposure: 1.2 });
  const mark = buildMark(THREE);
  mark.scale.setScalar(0.62);
  scene.add(mark);

  function resizeRenderer() {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    renderer.setSize(rect.width, rect.height, false);
    camera.aspect = rect.width / rect.height;
    camera.updateProjectionMatrix();
  }

  let visible = true;
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
    }, { rootMargin: "15%" }).observe(story);
  }

  const cameraState = { ...sampleCamera(currentProgress) };
  let frame = 0;
  function renderFrame() {
    frame = requestAnimationFrame(renderFrame);
    if (!visible) return;

    const target = sampleCamera(targetProgress);
    const damping = 0.085;
    cameraState.radius += (target.radius - cameraState.radius) * damping;
    cameraState.phi += (target.phi - cameraState.phi) * damping;
    cameraState.fov += (target.fov - cameraState.fov) * damping;
    cameraState.theta = lerpAngle(cameraState.theta, target.theta, damping);

    camera.position.set(
      cameraState.radius * Math.sin(cameraState.phi) * Math.sin(cameraState.theta),
      cameraState.radius * Math.cos(cameraState.phi),
      cameraState.radius * Math.sin(cameraState.phi) * Math.cos(cameraState.theta),
    );
    camera.fov = cameraState.fov;
    camera.updateProjectionMatrix();
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
  }

  resizeRenderer();
  addEventListener("resize", resizeRenderer, { passive: true });
  frame = requestAnimationFrame(renderFrame);
  addEventListener("pagehide", () => cancelAnimationFrame(frame), { once: true });
}
