import * as THREE from "three";

import { createRimMaterial } from "@/lib/style-genome/lightingRig";
import type { BuildingUserData, GenomeFamily, StyleGenome } from "@/lib/style-genome/types";

type BuildOptions = {
  family?: GenomeFamily;
};

type Rng = () => number;

type Dimensions = {
  width: number;
  height: number;
  depth: number;
};

type Materials = {
  body: THREE.MeshStandardMaterial;
  roof: THREE.MeshStandardMaterial;
  accent: THREE.MeshStandardMaterial;
  dark: THREE.MeshStandardMaterial;
  window: THREE.MeshStandardMaterial;
  foliage: THREE.MeshStandardMaterial;
  glass: THREE.MeshStandardMaterial;
};

type MotifContext = {
  group: THREE.Group;
  genome: StyleGenome;
  rng: Rng;
  dimensions: Dimensions;
  floors: number;
  materials: Materials;
  rimMaterials: THREE.MeshStandardMaterial[];
  windowMaterials: THREE.MeshStandardMaterial[];
};

type MotifFn = (context: MotifContext) => void;

type InstanceSpec = {
  position: THREE.Vector3;
  scale: THREE.Vector3;
  rotation?: THREE.Euler;
};

const DRAW_CALL_BUDGET = 8;
const TRIANGLE_BUDGET = 6000;
const DEG = Math.PI / 180;

// Buildings must fit the hero panel: every silhouette is capped to this cube edge.
const CUBE_EDGE = 3.4;
// Rounded "plastic toy" corner treatment shared by all massing volumes.
const CORNER_RADIUS_RATIO = 0.16;
const MAX_CORNER_RADIUS = 0.42;

export function buildFromGenome(genome: StyleGenome, seed: number, options: BuildOptions = {}): THREE.Group {
  const rng = mulberry32(hashSeed(`${genome.period}:${seed}`));
  const group = new THREE.Group();
  group.name = `style-genome:${genome.period}:${seed}`;

  const dimensions = createDimensions(genome, rng);
  const materials = createMaterials(genome);
  const rimMaterials = [materials.body, materials.roof, materials.accent, materials.dark, materials.glass];
  const windowMaterials = [materials.window];

  const bodyGeometry = mergeGeometries(createMassingGeometries(genome, dimensions, rng));
  const body = new THREE.Mesh(bodyGeometry, materials.body);
  body.name = "silhouette";
  body.castShadow = true;
  body.receiveShadow = true;
  group.add(body);

  const roofGeometry = mergeGeometries(createRoofGeometries(genome, dimensions, rng));
  const roof = new THREE.Mesh(roofGeometry, materials.roof);
  roof.name = "roof";
  roof.castShadow = true;
  roof.receiveShadow = true;
  group.add(roof);

  const floors = getFloorCount(genome, dimensions);
  const windows = createWindowInstances(genome, dimensions, floors, rng, materials.window);
  group.add(windows);

  const context: MotifContext = {
    group,
    genome,
    rng,
    dimensions,
    floors,
    materials,
    rimMaterials,
    windowMaterials,
  };

  for (const motif of genome.ornament.motifs.slice(0, 3)) {
    if (!motif) continue;
    const motifFn = motifRegistry[motif];
    if (!motifFn) {
      throw new Error(`Unsupported style-genome motif: ${motif}`);
    }
    motifFn(context);
  }

  const userData: BuildingUserData = {
    period: genome.period,
    family: options.family,
    seed,
    triangleCount: countTriangles(group),
    drawCallBudget: DRAW_CALL_BUDGET,
    windowMaterials,
    rimMaterials,
    hoverTarget: 0,
    hoverValue: 0,
    baseY: 0,
  };
  group.userData = userData;

  if (userData.triangleCount > TRIANGLE_BUDGET) {
    group.userData.triangleWarning = `Triangle budget exceeded: ${userData.triangleCount}`;
  }

  return group;
}

function createDimensions(genome: StyleGenome, rng: Rng): Dimensions {
  const [aspectX, aspectY, aspectZ] = genome.massing.aspect;
  const familyScale = 1 + (rng() - 0.5) * 0.08;
  const heightBias = genome.rhythm.verticality * 0.35;
  return {
    width: Math.min(CUBE_EDGE, 3.2 * aspectX * familyScale),
    height: Math.min(CUBE_EDGE, 3.1 * aspectY * (0.9 + heightBias) * familyScale),
    depth: Math.min(CUBE_EDGE, 2.9 * aspectZ * (0.96 + rng() * 0.08)),
  };
}

function createMaterials(genome: StyleGenome): Materials {
  const base = new THREE.Color(genome.material.base);
  const roof = base.clone().offsetHSL(0, -0.02, -0.08);
  const accent = base.clone().offsetHSL(0.015, 0.02, 0.13);
  const dark = base.clone().offsetHSL(0, -0.02, -0.2);

  const body = createRimMaterial(base, genome.material.roughness);
  const roofMaterial = createRimMaterial(roof, Math.min(1, genome.material.roughness + 0.04));
  const accentMaterial = createRimMaterial(accent, Math.max(0.45, genome.material.roughness - 0.08));
  const darkMaterial = createRimMaterial(dark, genome.material.roughness);
  const glassMaterial = createRimMaterial(new THREE.Color("#bfd9dc"), 0.35);

  const window = new THREE.MeshStandardMaterial({
    color: new THREE.Color("#111719"),
    emissive: new THREE.Color(genome.material.windowEmissive),
    emissiveIntensity: 0.16,
    metalness: 0,
    roughness: 0.38,
  });

  const foliage = new THREE.MeshStandardMaterial({
    color: new THREE.Color("#5c7f5d"),
    roughness: 0.92,
    metalness: 0,
  });

  return {
    body,
    roof: roofMaterial,
    accent: accentMaterial,
    dark: darkMaterial,
    window,
    foliage,
    glass: glassMaterial,
  };
}

function createMassingGeometries(genome: StyleGenome, dimensions: Dimensions, rng: Rng): THREE.BufferGeometry[] {
  const { width, height, depth } = dimensions;
  const geometries: THREE.BufferGeometry[] = [];

  if (genome.massing.footprint === "rectangle") {
    geometries.push(boxGeometry(width, height, depth, 0, height / 2, 0));
  }

  if (genome.massing.footprint === "L") {
    geometries.push(boxGeometry(width, height * 0.92, depth * 0.66, 0, height * 0.46, -depth * 0.12));
    geometries.push(boxGeometry(width * 0.48, height * 0.78, depth, -width * 0.26, height * 0.39, 0));
  }

  if (genome.massing.footprint === "stepped") {
    const tiers = 3 + Math.round(rng());
    let y = 0;
    for (let index = 0; index < tiers; index += 1) {
      const t = index / Math.max(1, tiers - 1);
      const tierHeight = height * (0.38 - t * 0.08);
      const tierWidth = width * (1 - t * 0.22);
      const tierDepth = depth * (1 - t * 0.18);
      const xOffset = genome.massing.symmetry === "asymmetric" ? (rng() - 0.5) * width * 0.16 * t : 0;
      geometries.push(boxGeometry(tierWidth, tierHeight, tierDepth, xOffset, y + tierHeight / 2, 0));
      y += tierHeight * 0.78;
    }
  }

  if (genome.massing.footprint === "cruciform") {
    geometries.push(boxGeometry(width * 0.62, height * 0.88, depth, 0, height * 0.44, 0));
    geometries.push(boxGeometry(width, height * 0.7, depth * 0.44, 0, height * 0.35, 0));
    geometries.push(boxGeometry(width * 0.34, height, depth * 0.34, 0, height * 0.5, 0));
  }

  if (genome.massing.footprint === "fractured") {
    const pieces = genome.massing.symmetry === "radial" ? 4 : 3;
    for (let index = 0; index < pieces; index += 1) {
      const t = index / pieces;
      const angle = genome.massing.symmetry === "radial" ? t * Math.PI * 2 : (rng() - 0.5) * 0.5;
      const pieceWidth = width * (0.55 + rng() * 0.16);
      const pieceDepth = depth * (0.5 + rng() * 0.18);
      const pieceHeight = height * (0.62 + rng() * 0.32);
      const radius = genome.massing.symmetry === "radial" ? width * 0.15 : width * (rng() - 0.5) * 0.28;
      geometries.push(
        boxGeometry(
          pieceWidth,
          pieceHeight,
          pieceDepth,
          Math.cos(angle) * radius,
          pieceHeight / 2,
          Math.sin(angle) * radius * 0.75,
          new THREE.Euler(0, angle + (rng() - 0.5) * 0.22, (rng() - 0.5) * 0.1),
        ),
      );
    }
  }

  return geometries;
}

function createRoofGeometries(genome: StyleGenome, dimensions: Dimensions, rng: Rng): THREE.BufferGeometry[] {
  const { width, height, depth } = dimensions;
  const roofGeometries: THREE.BufferGeometry[] = [];
  const roofHeight = Math.max(0.28, height * (0.12 + genome.rhythm.verticality * 0.06));

  if (genome.massing.roof === "flat") {
    roofGeometries.push(boxGeometry(width * 1.05, height * 0.035, depth * 1.05, 0, height + height * 0.018, 0));
  }

  if (genome.massing.roof === "gable") {
    roofGeometries.push(extrudedProfileGeometry([[-width * 0.58, 0], [width * 0.58, 0], [0, roofHeight]], depth * 1.08, 0, height, 0));
  }

  if (genome.massing.roof === "hipped") {
    roofGeometries.push(hippedRoofGeometry(width * 1.08, depth * 1.08, roofHeight, height));
  }

  if (genome.massing.roof === "shed") {
    roofGeometries.push(
      extrudedProfileGeometry(
        [[-width * 0.56, 0], [width * 0.56, roofHeight * 0.35], [width * 0.56, roofHeight], [-width * 0.56, roofHeight * 0.55]],
        depth * 1.08,
        0,
        height,
        0,
      ),
    );
  }

  if (genome.massing.roof === "spire") {
    const spires = genome.massing.footprint === "cruciform" ? [-0.34, 0, 0.34] : [0];
    for (const x of spires) {
      const spire = new THREE.ConeGeometry(width * 0.12, height * 0.38, 4, 1);
      spire.translate(width * x, height + height * 0.19, 0);
      roofGeometries.push(spire);
    }
  }

  if (genome.massing.roof === "ziggurat") {
    for (let index = 0; index < 4; index += 1) {
      const t = index / 4;
      roofGeometries.push(
        boxGeometry(width * (0.68 - t * 0.11), height * 0.06, depth * (0.68 - t * 0.1), 0, height + height * (0.035 + index * 0.055), 0),
      );
    }
  }

  if (genome.massing.roof === "curved") {
    roofGeometries.push(curvedRoofGeometry(width * 0.92, depth * 0.92, roofHeight, height));
  }

  if (genome.massing.roof === "faceted") {
    const points = [[-width * 0.55, 0], [-width * 0.12, roofHeight * (0.55 + rng() * 0.25)], [width * 0.52, roofHeight * 0.2], [width * 0.18, roofHeight]];
    roofGeometries.push(extrudedProfileGeometry(points, depth * 1.04, 0, height, 0));
  }

  return roofGeometries.length > 0 ? roofGeometries : [boxGeometry(width, height * 0.035, depth, 0, height, 0)];
}

function getFloorCount(genome: StyleGenome, dimensions: Dimensions): number {
  const raw = Math.round(1 + dimensions.height / 1.3 + genome.rhythm.verticality);
  return clamp(raw, 2, 5);
}

function createWindowInstances(
  genome: StyleGenome,
  dimensions: Dimensions,
  floors: number,
  rng: Rng,
  material: THREE.MeshStandardMaterial,
): THREE.InstancedMesh {
  const geometry = createWindowGeometry(genome.rhythm.windowShape);
  const instances: InstanceSpec[] = [];
  const { width, height, depth } = dimensions;
  const bays = clamp(Math.round(genome.rhythm.bays + (rng() - 0.5) * 1.2), 2, 11);
  const floorGap = height / (floors + 0.7);
  const bayGap = width / (bays + 1);
  const windowHeight = floorGap * lerp(0.42, 0.72, genome.rhythm.verticality);
  const windowWidth = bayGap * lerp(0.4, 0.78, genome.rhythm.windowToWallRatio);

  if (genome.rhythm.windowShape === "ribbon") {
    for (let floor = 0; floor < floors; floor += 1) {
      const y = floorGap * (floor + 0.82);
      instances.push(facadeInstance(0, y, depth / 2 + 0.036, width * 0.78, windowHeight * 0.42, 0));
      instances.push(facadeInstance(0, y, -depth / 2 - 0.036, width * 0.62, windowHeight * 0.36, Math.PI));
    }
  } else {
    for (let floor = 0; floor < floors; floor += 1) {
      const y = floorGap * (floor + 0.82);
      for (let bay = 0; bay < bays; bay += 1) {
        const asymmetry = genome.massing.symmetry === "asymmetric" ? (rng() - 0.5) * bayGap * 0.1 : 0;
        const x = -width / 2 + bayGap * (bay + 1) + asymmetry;
        const localWidth = genome.rhythm.windowShape === "slot" ? windowWidth * 0.38 : windowWidth;
        instances.push(facadeInstance(x, y, depth / 2 + 0.036, localWidth, windowHeight, 0));
      }
    }
  }

  const sideBays = Math.max(2, Math.round(bays * 0.45));
  for (let floor = 0; floor < Math.min(floors, 7); floor += 1) {
    const y = floorGap * (floor + 0.82);
    for (let bay = 0; bay < sideBays; bay += 1) {
      const z = -depth / 2 + (depth / (sideBays + 1)) * (bay + 1);
      instances.push(facadeInstance(width / 2 + 0.036, y, z, windowWidth * 0.75, windowHeight * 0.86, Math.PI / 2));
    }
  }

  const mesh = new THREE.InstancedMesh(geometry, material, instances.length);
  mesh.name = "rhythm-windows";
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  writeInstances(mesh, instances);
  return mesh;
}

function facadeInstance(x: number, y: number, z: number, width: number, height: number, rotationY: number): InstanceSpec {
  return {
    position: new THREE.Vector3(x, y, z),
    scale: new THREE.Vector3(width, height, 0.14),
    rotation: new THREE.Euler(0, rotationY, 0),
  };
}

const motifRegistry: Record<string, MotifFn> = {
  pediment: addPediment,
  fluted_columns: addColumns,
  entablature: addCornice,
  lancet_arch: addArchFrames,
  rose_window: addRoundWindow,
  flying_buttress: addFlyingButtress,
  fanlight_door: addPortal,
  dentil_cornice: addDentils,
  sash_panes: addFacadeGrid,
  bay_window: addBayWindows,
  steep_gable: addPediment,
  bargeboard_trim: addEdgeTrim,
  fluting: addVerticalFins,
  sunburst_crown: addSunburst,
  setbacks: addSetbackBands,
  ribbon_glazing: addFacadeGrid,
  corner_window: addCornerGlass,
  flat_roof_slab: addRoofPlate,
  curtain_wall_grid: addFacadeGrid,
  pilotis: addPilotis,
  thin_roof_plate: addRoofPlate,
  external_bracing: addBracing,
  service_spine: addServiceSpine,
  exposed_frame: addFrame,
  exposed_grid: addFrame,
  deep_window_reveals: addWindowReveals,
  monolith_stair_core: addServiceSpine,
  diagrid_skin: addBracing,
  flowing_fins: addVerticalFins,
  cellular_apertures: addCellularDots,
  deep_eaves: addRoofPlate,
  shoji_grid: addFacadeGrid,
  raised_plinth: addPlinth,
  arched_loggia: addArchFrames,
  terracotta_roof: addRoofPlate,
  stucco_cornice: addCornice,
  timber_battens: addVerticalFins,
  recessed_entry: addPortal,
  wide_verandah: addVerandah,
  slatted_screens: addVerticalFins,
  stilted_base: addPilotis,
  luminous_fluting: addVerticalFins,
  stepped_crown: addSetbackBands,
  chevron_spandrels: addChevronSpandrels,
  green_roof: addGreenRoof,
  solar_canopy: addSolarCanopy,
  timber_fins: addVerticalFins,
  podium_stacks: addPodiumStacks,
  sky_bridges: addSkyBridges,
  mega_frame: addFrame,
  faceted_planes: addFacetedPlanes,
  prismatic_crown: addSunburst,
  diagonal_mullions: addBracing,
  cantilevered_slabs: addCantileveredSlabs,
  hanging_gardens: addHangingGardens,
  open_cores: addPortal,
  planted_balconies: addHangingGardens,
  sky_gardens: addGreenRoof,
  irregular_terraces: addCantileveredSlabs,
};

function addPediment(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = extrudedProfileGeometry([[-width * 0.38, 0], [width * 0.38, 0], [0, height * 0.14]], depth * 0.08, 0, height * 0.78, depth / 2 + 0.12);
  addMesh(context, geometry, context.materials.accent, "motif-pediment");
}

function addColumns(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(context.genome.rhythm.bays + 1, 4, 10);
  const geometry = new THREE.CylinderGeometry(0.045, 0.052, 1, 8);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    const x = -width * 0.42 + (width * 0.84 * index) / (count - 1);
    instances.push({
      position: new THREE.Vector3(x, height * 0.34, depth / 2 + 0.16),
      scale: new THREE.Vector3(1, height * 0.62, 1),
    });
  }
  addInstanced(context, geometry, context.materials.accent, instances, "motif-columns");
}

function addCornice(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances = [
    facadeInstance(0, height * 0.78, depth / 2 + 0.08, width * 0.9, height * 0.035, 0),
    facadeInstance(0, height * 0.92, depth / 2 + 0.09, width * 0.96, height * 0.03, 0),
  ];
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-cornice");
}

function addArchFrames(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(context.genome.rhythm.bays, 3, 8);
  const geometry = createWindowGeometry(context.genome.rhythm.windowShape === "round_arch" ? "round_arch" : "lancet");
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    const x = -width * 0.38 + (width * 0.76 * index) / Math.max(1, count - 1);
    instances.push(facadeInstance(x, height * 0.22, depth / 2 + 0.085, width * 0.09, height * 0.22, 0));
  }
  addInstanced(context, geometry, context.materials.accent, instances, "motif-arch-frames");
}

function addRoundWindow(context: MotifContext) {
  const { height, depth } = context.dimensions;
  const geometry = new THREE.CylinderGeometry(0.32, 0.32, 0.06, 24);
  geometry.rotateX(Math.PI / 2);
  geometry.translate(0, height * 0.68, depth / 2 + 0.09);
  addMesh(context, geometry, context.materials.window, "motif-round-window");
}

function addFlyingButtress(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(context.genome.rhythm.bays, 4, 7);
  const geometry = new THREE.BoxGeometry(1, 1, 1);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    const z = -depth * 0.42 + (depth * 0.84 * index) / Math.max(1, count - 1);
    for (const side of [-1, 1]) {
      instances.push({
        position: new THREE.Vector3(side * width * 0.38, height * 0.36, z),
        scale: new THREE.Vector3(0.08, height * 0.64, 0.08),
        rotation: new THREE.Euler(0, 0, side * -18 * DEG),
      });
    }
  }
  addInstanced(context, geometry, context.materials.accent, instances, "motif-buttress");
}

function addPortal(context: MotifContext) {
  const { height, depth } = context.dimensions;
  const geometry = createWindowGeometry("round_arch");
  geometry.scale(0.62, 1, 1);
  geometry.translate(0, height * 0.14, depth / 2 + 0.1);
  addMesh(context, geometry, context.materials.dark, "motif-portal");
}

function addDentils(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(context.genome.rhythm.bays * 3, 12, 30);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    instances.push(facadeInstance(-width * 0.45 + (width * 0.9 * index) / (count - 1), height * 0.84, depth / 2 + 0.12, width * 0.018, height * 0.035, 0));
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-dentils");
}

function addFacadeGrid(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const bays = clamp(context.genome.rhythm.bays, 3, 10);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index <= bays; index += 1) {
    instances.push(facadeInstance(-width * 0.42 + (width * 0.84 * index) / bays, height * 0.46, depth / 2 + 0.11, width * 0.01, height * 0.72, 0));
  }
  for (let floor = 1; floor <= context.floors; floor += 1) {
    instances.push(facadeInstance(0, (height * floor) / (context.floors + 1), depth / 2 + 0.115, width * 0.84, height * 0.008, 0));
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-facade-grid");
}

function addBayWindows(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances = [-0.24, 0.24].map((offset) =>
    facadeInstance(width * offset, height * 0.38, depth / 2 + 0.22, width * 0.16, height * 0.34, 0),
  );
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.glass, instances, "motif-bay-windows");
}

function addEdgeTrim(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances = [
    facadeInstance(-width * 0.28, height * 0.94, depth / 2 + 0.13, width * 0.36, height * 0.018, 0),
    facadeInstance(width * 0.28, height * 0.94, depth / 2 + 0.13, width * 0.36, height * 0.018, 0),
  ];
  instances[0].rotation = new THREE.Euler(0, 0, 28 * DEG);
  instances[1].rotation = new THREE.Euler(0, 0, -28 * DEG);
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-edge-trim");
}

function addVerticalFins(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(Math.round(context.genome.rhythm.bays * lerp(1.2, 2.3, context.genome.ornament.density)), 5, 22);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    const x = -width * 0.45 + (width * 0.9 * index) / Math.max(1, count - 1);
    instances.push(facadeInstance(x, height * 0.48, depth / 2 + 0.12, width * 0.012, height * 0.78, 0));
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-vertical-fins");
}

function addSunburst(context: MotifContext) {
  const { height, depth } = context.dimensions;
  const instances: InstanceSpec[] = [];
  const rays = 11;
  for (let index = 0; index < rays; index += 1) {
    const angle = -52 * DEG + (104 * DEG * index) / (rays - 1);
    instances.push({
      position: new THREE.Vector3(Math.sin(angle) * 0.23, height * 1.03 + Math.cos(angle) * 0.14, depth / 2 + 0.14),
      scale: new THREE.Vector3(0.025, height * 0.17, 0.025),
      rotation: new THREE.Euler(0, 0, -angle),
    });
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-sunburst");
}

function addSetbackBands(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < 4; index += 1) {
    const t = index / 4;
    instances.push(facadeInstance(0, height * (0.52 + t * 0.12), depth / 2 + 0.1, width * (0.82 - t * 0.1), height * 0.022, 0));
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-setback-bands");
}

function addCornerGlass(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances = [
    facadeInstance(width / 2 + 0.05, height * 0.45, depth * 0.24, width * 0.15, height * 0.46, Math.PI / 2),
    facadeInstance(width * 0.38, height * 0.45, depth / 2 + 0.05, width * 0.18, height * 0.46, 0),
  ];
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.window, instances, "motif-corner-glass");
}

function addRoofPlate(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = boxGeometry(width * 1.12, height * 0.035, depth * 1.14, 0, height + height * 0.045, 0);
  addMesh(context, geometry, context.materials.accent, "motif-roof-plate");
}

function addPilotis(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = new THREE.CylinderGeometry(0.04, 0.05, 1, 8);
  const instances: InstanceSpec[] = [];
  for (const x of [-0.36, -0.12, 0.12, 0.36]) {
    for (const z of [-0.32, 0.32]) {
      instances.push({
        position: new THREE.Vector3(width * x, height * 0.08, depth * z),
        scale: new THREE.Vector3(1, height * 0.16, 1),
      });
    }
  }
  addInstanced(context, geometry, context.materials.dark, instances, "motif-pilotis");
}

function addBracing(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(context.genome.rhythm.bays, 4, 9);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    const x = -width * 0.42 + (width * 0.84 * index) / Math.max(1, count - 1);
    const tilt = index % 2 === 0 ? 18 * DEG : -18 * DEG;
    instances.push({
      position: new THREE.Vector3(x, height * 0.5, depth / 2 + 0.14),
      scale: new THREE.Vector3(width * 0.012, height * 0.88, width * 0.012),
      rotation: new THREE.Euler(0, 0, tilt),
    });
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.dark, instances, "motif-bracing");
}

function addServiceSpine(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = boxGeometry(width * 0.18, height * 0.88, depth * 0.18, width * 0.46, height * 0.44, -depth * 0.2);
  addMesh(context, geometry, context.materials.dark, "motif-service-spine");
}

function addFrame(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances = [
    facadeInstance(-width * 0.48, height * 0.5, depth / 2 + 0.16, width * 0.025, height, 0),
    facadeInstance(width * 0.48, height * 0.5, depth / 2 + 0.16, width * 0.025, height, 0),
    facadeInstance(0, height * 0.08, depth / 2 + 0.16, width, height * 0.025, 0),
    facadeInstance(0, height * 0.92, depth / 2 + 0.16, width, height * 0.025, 0),
  ];
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.dark, instances, "motif-frame");
}

function addWindowReveals(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(context.genome.rhythm.bays, 3, 7);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    instances.push(facadeInstance(-width * 0.38 + (width * 0.76 * index) / Math.max(1, count - 1), height * 0.45, depth / 2 + 0.13, width * 0.12, height * 0.42, 0));
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.dark, instances, "motif-window-reveals");
}

function addCellularDots(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = new THREE.CylinderGeometry(0.08, 0.08, 0.04, 10);
  geometry.rotateX(Math.PI / 2);
  const instances: InstanceSpec[] = [];
  for (let floor = 0; floor < Math.min(context.floors, 6); floor += 1) {
    for (let bay = 0; bay < Math.min(context.genome.rhythm.bays, 8); bay += 1) {
      instances.push(facadeInstance(-width * 0.38 + bay * width * 0.1, height * (0.22 + floor * 0.11), depth / 2 + 0.12, 1, 1, 0));
    }
  }
  addInstanced(context, geometry, context.materials.window, instances, "motif-cellular");
}

function addPlinth(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  addMesh(context, boxGeometry(width * 1.08, height * 0.12, depth * 1.08, 0, height * 0.06, 0), context.materials.dark, "motif-plinth");
}

function addVerandah(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances = [
    facadeInstance(0, height * 0.24, depth / 2 + 0.48, width * 1.02, height * 0.035, 0),
    facadeInstance(0, height * 0.38, depth / 2 + 0.48, width * 1.04, height * 0.025, 0),
  ];
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-verandah");
}

function addGreenRoof(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = boxGeometry(width * 0.82, height * 0.035, depth * 0.76, 0, height + height * 0.07, 0);
  addMesh(context, geometry, context.materials.foliage, "motif-green-roof");
}

function addSolarCanopy(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = boxGeometry(width * 0.72, height * 0.018, depth * 0.32, 0, height + height * 0.14, -depth * 0.12, new THREE.Euler(-10 * DEG, 0, 0));
  addMesh(context, geometry, context.materials.glass, "motif-solar-canopy");
}

function addPodiumStacks(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < 4; index += 1) {
    instances.push({
      position: new THREE.Vector3((index - 1.5) * width * 0.18, height * (0.18 + index * 0.11), depth / 2 + 0.2),
      scale: new THREE.Vector3(width * 0.28, height * 0.12, depth * 0.18),
    });
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-podium-stacks");
}

function addSkyBridges(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances = [
    facadeInstance(0, height * 0.52, depth * 0.58, width * 0.78, height * 0.055, 0),
    facadeInstance(0, height * 0.72, -depth * 0.58, width * 0.62, height * 0.05, 0),
  ];
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.glass, instances, "motif-sky-bridges");
}

function addFacetedPlanes(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const geometry = extrudedProfileGeometry([[-width * 0.32, -height * 0.12], [width * 0.32, 0], [width * 0.18, height * 0.22], [-width * 0.24, height * 0.16]], depth * 0.025, 0, height * 0.58, depth / 2 + 0.16);
  addMesh(context, geometry, context.materials.glass, "motif-faceted-planes");
}

function addChevronSpandrels(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < 8; index += 1) {
    const x = -width * 0.35 + index * width * 0.1;
    instances.push({
      position: new THREE.Vector3(x, height * 0.56, depth / 2 + 0.14),
      scale: new THREE.Vector3(width * 0.012, height * 0.22, width * 0.012),
      rotation: new THREE.Euler(0, 0, (index % 2 === 0 ? 24 : -24) * DEG),
    });
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-chevron");
}

function addCantileveredSlabs(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < 5; index += 1) {
    const side = index % 2 === 0 ? -1 : 1;
    instances.push({
      position: new THREE.Vector3(side * width * 0.18, height * (0.22 + index * 0.14), depth / 2 + 0.22),
      scale: new THREE.Vector3(width * (0.68 - index * 0.04), height * 0.032, depth * 0.2),
    });
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.accent, instances, "motif-cantilevered-slabs");
}

function addHangingGardens(context: MotifContext) {
  const { width, height, depth } = context.dimensions;
  const count = clamp(context.genome.rhythm.bays + 2, 5, 10);
  const instances: InstanceSpec[] = [];
  for (let index = 0; index < count; index += 1) {
    instances.push({
      position: new THREE.Vector3(-width * 0.4 + (width * 0.8 * index) / (count - 1), height * (0.24 + (index % 4) * 0.16), depth / 2 + 0.28),
      scale: new THREE.Vector3(width * 0.06, height * 0.045, depth * 0.08),
    });
  }
  addInstanced(context, new THREE.BoxGeometry(1, 1, 1), context.materials.foliage, instances, "motif-hanging-gardens");
}

function addMesh(context: MotifContext, geometry: THREE.BufferGeometry, material: THREE.MeshStandardMaterial, name: string) {
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  context.group.add(mesh);
}

function addInstanced(
  context: MotifContext,
  geometry: THREE.BufferGeometry,
  material: THREE.MeshStandardMaterial,
  instances: InstanceSpec[],
  name: string,
) {
  const mesh = new THREE.InstancedMesh(geometry, material, instances.length);
  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  writeInstances(mesh, instances);
  context.group.add(mesh);
}

function writeInstances(mesh: THREE.InstancedMesh, instances: InstanceSpec[]) {
  const matrix = new THREE.Matrix4();
  const quaternion = new THREE.Quaternion();
  for (let index = 0; index < instances.length; index += 1) {
    const instance = instances[index];
    quaternion.setFromEuler(instance.rotation ?? new THREE.Euler());
    matrix.compose(instance.position, quaternion, instance.scale);
    mesh.setMatrixAt(index, matrix);
  }
  mesh.instanceMatrix.needsUpdate = true;
}

function createWindowGeometry(shape: StyleGenome["rhythm"]["windowShape"]): THREE.BufferGeometry {
  if (shape === "lancet") {
    return centeredExtrudedShape([[-0.35, -0.5], [0.35, -0.5], [0.35, 0.08], [0, 0.5], [-0.35, 0.08]], 0.08);
  }
  if (shape === "round_arch") {
    const points: [number, number][] = [];
    for (let index = 0; index <= 10; index += 1) {
      const angle = Math.PI - (Math.PI * index) / 10;
      points.push([Math.cos(angle) * 0.35, Math.sin(angle) * 0.35 + 0.12]);
    }
    points.push([0.35, -0.5], [-0.35, -0.5]);
    return centeredExtrudedShape(points, 0.08);
  }
  if (shape === "porthole" || shape === "cellular") {
    const geometry = new THREE.CylinderGeometry(0.46, 0.46, 0.08, shape === "cellular" ? 10 : 22);
    geometry.rotateX(Math.PI / 2);
    return geometry;
  }
  if (shape === "faceted") {
    return centeredExtrudedShape([[-0.4, -0.42], [0.26, -0.5], [0.42, 0.18], [-0.12, 0.5], [-0.38, 0.14]], 0.08);
  }
  return roundedBoxGeometry(1, 1, 1, 0.16, 2);
}

function centeredExtrudedShape(points: [number, number][], depth: number): THREE.BufferGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(points[0][0], points[0][1]);
  for (const point of points.slice(1)) {
    shape.lineTo(point[0], point[1]);
  }
  shape.closePath();
  const bevel = Math.min(0.07, depth * 0.35);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 2,
  });
  geometry.translate(0, 0, -depth / 2);
  geometry.computeVertexNormals();
  return geometry;
}

function boxGeometry(
  width: number,
  height: number,
  depth: number,
  x: number,
  y: number,
  z: number,
  rotation = new THREE.Euler(),
): THREE.BufferGeometry {
  const radius = Math.min(MAX_CORNER_RADIUS, Math.min(width, height, depth) * CORNER_RADIUS_RATIO);
  const geometry = roundedBoxGeometry(width, height, depth, radius, 4);
  const matrix = new THREE.Matrix4();
  matrix.compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(rotation), new THREE.Vector3(1, 1, 1));
  geometry.applyMatrix4(matrix);
  return geometry;
}

// Minkowski-style rounded box: clamp each vertex of a segmented box to an inner
// box and push it back out along the corner normal, giving smooth plastic edges.
function roundedBoxGeometry(width: number, height: number, depth: number, radius: number, segments: number): THREE.BufferGeometry {
  const r = Math.max(0.001, Math.min(radius, width / 2, height / 2, depth / 2));
  const geometry = new THREE.BoxGeometry(width, height, depth, segments, segments, segments);
  const position = geometry.getAttribute("position");
  const normal = geometry.getAttribute("normal");
  const innerX = width / 2 - r;
  const innerY = height / 2 - r;
  const innerZ = depth / 2 - r;

  for (let index = 0; index < position.count; index += 1) {
    const px = position.getX(index);
    const py = position.getY(index);
    const pz = position.getZ(index);
    const cx = clamp(px, -innerX, innerX);
    const cy = clamp(py, -innerY, innerY);
    const cz = clamp(pz, -innerZ, innerZ);
    const dx = px - cx;
    const dy = py - cy;
    const dz = pz - cz;
    const length = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (length > 1e-6) {
      const nx = dx / length;
      const ny = dy / length;
      const nz = dz / length;
      position.setXYZ(index, cx + nx * r, cy + ny * r, cz + nz * r);
      normal.setXYZ(index, nx, ny, nz);
    }
  }

  return geometry;
}

function extrudedProfileGeometry(points: number[][], depth: number, x: number, y: number, z: number): THREE.BufferGeometry {
  const pairs = points.map((point) => [point[0], point[1]] as [number, number]);
  const geometry = centeredExtrudedShape(pairs, depth);
  geometry.translate(x, y, z);
  return geometry;
}

function hippedRoofGeometry(width: number, depth: number, height: number, y: number): THREE.BufferGeometry {
  const halfWidth = width / 2;
  const halfDepth = depth / 2;
  const vertices = new Float32Array([
    -halfWidth, y, -halfDepth,
    halfWidth, y, -halfDepth,
    halfWidth, y, halfDepth,
    -halfWidth, y, halfDepth,
    0, y + height, -halfDepth * 0.22,
    0, y + height, halfDepth * 0.22,
  ]);
  const indices = [0, 1, 4, 1, 2, 5, 1, 5, 4, 2, 3, 5, 3, 0, 4, 3, 4, 5, 0, 3, 2, 0, 2, 1];
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function curvedRoofGeometry(width: number, depth: number, height: number, y: number): THREE.BufferGeometry {
  const points: [number, number][] = [];
  const segments = 7;
  for (let index = 0; index <= segments; index += 1) {
    const t = index / segments;
    const x = -width / 2 + width * t;
    const arc = Math.sin(Math.PI * t) * height;
    points.push([x, arc]);
  }
  points.push([width / 2, 0], [-width / 2, 0]);
  return extrudedProfileGeometry(points, depth, 0, y, 0);
}

function mergeGeometries(geometries: THREE.BufferGeometry[]): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];

  for (const source of geometries) {
    const geometry = source.index ? source.toNonIndexed() : source;
    // Rounded massing carries analytic smooth normals — recomputing would flatten them.
    if (!geometry.getAttribute("normal")) {
      geometry.computeVertexNormals();
    }
    const position = geometry.getAttribute("position");
    const normal = geometry.getAttribute("normal");

    for (let index = 0; index < position.count; index += 1) {
      positions.push(position.getX(index), position.getY(index), position.getZ(index));
      normals.push(normal.getX(index), normal.getY(index), normal.getZ(index));
    }
  }

  const merged = new THREE.BufferGeometry();
  merged.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  merged.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  merged.computeBoundingSphere();
  return merged;
}

function countTriangles(group: THREE.Group): number {
  let triangles = 0;
  group.traverse((object: THREE.Object3D) => {
    if (object instanceof THREE.Mesh || object instanceof THREE.InstancedMesh) {
      const position = object.geometry.getAttribute("position");
      const geometryTriangles = object.geometry.index ? object.geometry.index.count / 3 : position.count / 3;
      const instances = object instanceof THREE.InstancedMesh ? object.count : 1;
      triangles += Math.round(geometryTriangles * instances);
    }
  });
  return triangles;
}

function mulberry32(seed: number): Rng {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashSeed(input: string): number {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function lerp(start: number, end: number, amount: number): number {
  return start + (end - start) * amount;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
