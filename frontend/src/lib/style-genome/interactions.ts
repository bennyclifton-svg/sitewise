import * as THREE from "three";

import type { BuildingUserData } from "@/lib/style-genome/types";

export type PointerState = {
  ndc: THREE.Vector2;
  tilt: THREE.Vector2;
  active: boolean;
};

export function createPointerState(): PointerState {
  return {
    ndc: new THREE.Vector2(0, 0),
    tilt: new THREE.Vector2(0, 0),
    active: false,
  };
}

export function updatePointerFromEvent(event: PointerEvent, element: HTMLElement, state: PointerState) {
  const rect = element.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width;
  const y = (event.clientY - rect.top) / rect.height;
  state.ndc.set(x * 2 - 1, -(y * 2 - 1));
  state.tilt.set((x - 0.5) * 2, (y - 0.5) * 2);
  state.active = true;
}

export function resetPointer(state: PointerState) {
  state.ndc.set(0, 0);
  state.tilt.set(0, 0);
  state.active = false;
}

export function normalizedPageScroll(): number {
  const scrollRange = document.documentElement.scrollHeight - window.innerHeight;
  if (scrollRange <= 0) return 0.5;
  return clamp01(window.scrollY / scrollRange);
}

export function pickHoveredBuilding(
  raycaster: THREE.Raycaster,
  camera: THREE.Camera,
  pointer: PointerState,
  buildings: THREE.Group[],
): THREE.Group | null {
  if (!pointer.active) return null;
  raycaster.setFromCamera(pointer.ndc, camera);
  const hits = raycaster.intersectObjects(buildings, true);
  const hit = hits.find((candidate) => findBuildingRoot(candidate.object, buildings));
  return hit ? findBuildingRoot(hit.object, buildings) : null;
}

export function animateBuildingInteractions(buildings: THREE.Group[], hovered: THREE.Group | null, deltaSeconds: number, reducedMotion: boolean): number {
  let hoverBoost = 0;
  for (const building of buildings) {
    const data = building.userData as BuildingUserData;
    data.hoverTarget = !reducedMotion && building === hovered ? 1 : 0;
    data.hoverValue = damp(data.hoverValue, data.hoverTarget, 12, deltaSeconds);
    building.position.y = data.baseY + data.hoverValue * 0.12;
    hoverBoost = Math.max(hoverBoost, data.hoverValue);
  }
  return hoverBoost;
}

export function applyPointerParallax(cameraRig: THREE.Object3D, pointer: PointerState, deltaSeconds: number, reducedMotion: boolean) {
  const targetX = reducedMotion ? 0 : pointer.tilt.y * -3 * DEG;
  const targetY = reducedMotion ? 0 : pointer.tilt.x * 3 * DEG;
  cameraRig.rotation.x = damp(cameraRig.rotation.x, targetX, 8, deltaSeconds);
  cameraRig.rotation.y = damp(cameraRig.rotation.y, targetY, 8, deltaSeconds);
}

export function damp(current: number, target: number, smoothing: number, deltaSeconds: number): number {
  return THREE.MathUtils.damp(current, target, smoothing, deltaSeconds);
}

function findBuildingRoot(object: THREE.Object3D, buildings: THREE.Group[]): THREE.Group | null {
  let current: THREE.Object3D | null = object;
  while (current) {
    if (buildings.includes(current as THREE.Group)) return current as THREE.Group;
    current = current.parent;
  }
  return null;
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

const DEG = Math.PI / 180;

