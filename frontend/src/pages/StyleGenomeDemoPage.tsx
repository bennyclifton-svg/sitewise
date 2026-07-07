import { ArrowLeft, Shuffle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import * as THREE from "three";

import { Button } from "@/components/ui/button";
import { buildFromGenome } from "@/lib/style-genome/generator";
import { genomeLibrary } from "@/lib/style-genome/genomeLibrary";
import {
  animateBuildingInteractions,
  applyPointerParallax,
  createPointerState,
  damp,
  normalizedPageScroll,
  pickHoveredBuilding,
  resetPointer,
  updatePointerFromEvent,
} from "@/lib/style-genome/interactions";
import { createLightingRig, updateLightingRig } from "@/lib/style-genome/lightingRig";
import type { BuildingUserData, GenomeEntry, GenomeFamily } from "@/lib/style-genome/types";
import { cn } from "@/lib/utils";

const families: GenomeFamily[] = ["historical", "modern", "regional", "invented"];

export function StyleGenomeDemoPage() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [family, setFamily] = useState<GenomeFamily>("invented");
  const [seed, setSeed] = useState(47);
  const entries = useMemo(() => genomeLibrary[family], [family]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    return mountStyleGenomeScene(canvas, entries, family, seed);
  }, [entries, family, seed]);

  return (
    <main className="min-h-[230vh] bg-[radial-gradient(circle_at_50%_35%,oklch(0.98_0.01_92),var(--bg-canvas)_62%)] text-foreground">
      <section className="sticky top-0 h-screen overflow-hidden">
        <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-label="Style genome architecture demo" />
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-start justify-between gap-4 p-4 md:p-6">
          <Button asChild variant="outline" size="icon" className="pointer-events-auto bg-background/80 backdrop-blur" aria-label="Back">
            <Link to="/">
              <ArrowLeft />
            </Link>
          </Button>
          <div className="pointer-events-auto flex max-w-[min(720px,calc(100vw-96px))] flex-wrap justify-end gap-2">
            <div className="flex flex-wrap gap-1 rounded-md border border-border bg-background/82 p-1 shadow-sm backdrop-blur">
              {families.map((item) => (
                <Button
                  key={item}
                  type="button"
                  variant={item === family ? "default" : "ghost"}
                  size="sm"
                  className="capitalize"
                  onClick={() => setFamily(item)}
                >
                  {item}
                </Button>
              ))}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="bg-background/82 backdrop-blur"
              onClick={() => setSeed((current) => current + 11)}
            >
              <Shuffle />
              {seed}
            </Button>
          </div>
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 p-4 md:p-6">
          <div className="flex flex-wrap gap-2">
            {entries.map((entry) => (
              <span
                key={entry.id}
                className={cn(
                  "rounded-md border border-border bg-background/76 px-2 py-1 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur",
                  family === "invented" && "border-primary/25 text-foreground",
                )}
              >
                {entry.label}
              </span>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function mountStyleGenomeScene(canvas: HTMLCanvasElement, entries: GenomeEntry[], family: GenomeFamily, seed: number): () => void {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.shadowMap.autoUpdate = false;

  const scene = new THREE.Scene();
  const cameraRig = new THREE.Group();
  scene.add(cameraRig);

  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 120);
  cameraRig.add(camera);

  const stage = new THREE.Group();
  stage.name = "style-genome-stage";
  scene.add(stage);

  const buildings = entries.map((entry, index) => {
    const building = buildFromGenome(entry.genome, seed + index * 17, { family });
    const data = building.userData as BuildingUserData;
    building.position.x = (index - (entries.length - 1) / 2) * 4.4;
    building.scale.setScalar(getFamilyScale(family));
    data.baseY = building.position.y;
    stage.add(building);
    return building;
  });

  const bounds = new THREE.Box3().setFromObject(stage);
  const rig = createLightingRig(scene);
  const raycaster = new THREE.Raycaster();
  const pointer = createPointerState();
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const materialSet = collectMaterials(buildings);

  let visible = true;
  let disposed = false;
  let frameHandle = 0;
  let hovered: THREE.Group | null = null;
  let needsPick = false;
  let lastPick = 0;
  let previousTime = performance.now();
  let scrollValue = normalizedPageScroll();

  const observer = new IntersectionObserver(([entry]) => {
    visible = entry?.isIntersecting ?? true;
  });
  observer.observe(canvas);

  const resizeObserver = new ResizeObserver(() => {
    resizeRenderer(renderer, camera, canvas);
    fitCamera(camera, bounds);
  });
  resizeObserver.observe(canvas);
  resizeRenderer(renderer, camera, canvas);
  fitCamera(camera, bounds);

  const onPointerMove = (event: PointerEvent) => {
    updatePointerFromEvent(event, canvas, pointer);
    needsPick = true;
  };
  const onPointerLeave = () => {
    resetPointer(pointer);
    hovered = null;
  };
  canvas.addEventListener("pointermove", onPointerMove, { passive: true });
  canvas.addEventListener("pointerleave", onPointerLeave);

  const animate = (time: number) => {
    if (disposed) return;
    const deltaSeconds = Math.min(0.05, (time - previousTime) / 1000);
    previousTime = time;

    if (visible) {
      scrollValue = damp(scrollValue, normalizedPageScroll(), 5, deltaSeconds);
      if (needsPick || time - lastPick > 80) {
        hovered = pickHoveredBuilding(raycaster, camera, pointer, buildings);
        needsPick = false;
        lastPick = time;
      }

      const hoverBoost = animateBuildingInteractions(buildings, hovered, deltaSeconds, reducedMotion);
      applyPointerParallax(cameraRig, pointer, deltaSeconds, reducedMotion);
      const shadowDirty = updateLightingRig(rig, {
        scrollProgress: scrollValue,
        bounds,
        windowMaterials: materialSet.windowMaterials,
        rimMaterials: materialSet.rimMaterials,
        hoverBoost,
        reducedMotion,
      });
      renderer.shadowMap.needsUpdate = shadowDirty;
      renderer.render(scene, camera);
    }

    frameHandle = window.requestAnimationFrame(animate);
  };
  frameHandle = window.requestAnimationFrame(animate);

  return () => {
    disposed = true;
    window.cancelAnimationFrame(frameHandle);
    observer.disconnect();
    resizeObserver.disconnect();
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerleave", onPointerLeave);
    disposeScene(scene);
    renderer.dispose();
  };
}

function fitCamera(camera: THREE.PerspectiveCamera, bounds: THREE.Box3) {
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
  const distanceForHeight = size.y / (2 * Math.tan(verticalFov / 2));
  const distanceForWidth = size.x / (2 * Math.tan(horizontalFov / 2));
  const distance = Math.max(distanceForHeight, distanceForWidth, 10) * 1.28 + size.z * 0.32;
  camera.position.set(center.x, center.y * 0.55 + size.y * 0.18, center.z + distance);
  camera.lookAt(center.x, center.y * 0.42, center.z);
  camera.near = Math.max(0.1, distance / 80);
  camera.far = distance + size.z + size.y + 40;
  camera.updateProjectionMatrix();
}

function resizeRenderer(renderer: THREE.WebGLRenderer, camera: THREE.PerspectiveCamera, canvas: HTMLCanvasElement) {
  const width = Math.max(1, canvas.clientWidth);
  const height = Math.max(1, canvas.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function collectMaterials(buildings: THREE.Group[]): Pick<BuildingUserData, "windowMaterials" | "rimMaterials"> {
  const windowMaterials: THREE.MeshStandardMaterial[] = [];
  const rimMaterials: THREE.MeshStandardMaterial[] = [];
  for (const building of buildings) {
    const data = building.userData as BuildingUserData;
    windowMaterials.push(...data.windowMaterials);
    rimMaterials.push(...data.rimMaterials);
  }
  return { windowMaterials, rimMaterials };
}

function getFamilyScale(family: GenomeFamily): number {
  if (family === "invented") return 0.58;
  if (family === "modern") return 0.62;
  if (family === "historical") return 0.66;
  return 0.72;
}

function disposeScene(scene: THREE.Scene) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  scene.traverse((object: THREE.Object3D) => {
    if (object instanceof THREE.Mesh || object instanceof THREE.InstancedMesh) {
      geometries.add(object.geometry);
      const materialList = Array.isArray(object.material) ? object.material : [object.material];
      for (const material of materialList) {
        materials.add(material);
      }
    }
  });
  for (const geometry of geometries) geometry.dispose();
  for (const material of materials) material.dispose();
}
