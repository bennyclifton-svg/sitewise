import * as THREE from "three";

type RimUniforms = {
  rimColor: { value: THREE.Color };
  rimIntensity: { value: number };
  rimLightDirection: { value: THREE.Vector3 };
};

type RimUserData = {
  rimUniforms: RimUniforms;
};

export type LightingRig = {
  sun: THREE.DirectionalLight;
  rim: THREE.DirectionalLight;
  target: THREE.Object3D;
  ground: THREE.Mesh<THREE.PlaneGeometry, THREE.ShadowMaterial>;
  lastAzimuth: number;
  lastElevation: number;
};

export type LightingUpdate = {
  scrollProgress: number;
  bounds: THREE.Box3;
  windowMaterials: THREE.MeshStandardMaterial[];
  rimMaterials: THREE.MeshStandardMaterial[];
  hoverBoost: number;
  reducedMotion: boolean;
};

const DEG = Math.PI / 180;

export function createRimMaterial(color: THREE.Color, roughness: number): THREE.MeshStandardMaterial {
  const uniforms: RimUniforms = {
    rimColor: { value: new THREE.Color("#dceeff") },
    rimIntensity: { value: 0.08 },
    rimLightDirection: { value: new THREE.Vector3(0, 1, 0) },
  };

  const material = new THREE.MeshStandardMaterial({
    color,
    roughness,
    metalness: 0,
  });

  material.userData.rimUniforms = uniforms;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.rimColor = uniforms.rimColor;
    shader.uniforms.rimIntensity = uniforms.rimIntensity;
    shader.uniforms.rimLightDirection = uniforms.rimLightDirection;
    shader.vertexShader = shader.vertexShader
      .replace("void main() {", "varying vec3 vRimWorldNormal;\nvarying vec3 vRimWorldPosition;\nvoid main() {")
      .replace(
        "#include <begin_vertex>",
        [
          "#include <begin_vertex>",
          "vec4 rimWorldPosition = modelMatrix * vec4(transformed, 1.0);",
          "vRimWorldPosition = rimWorldPosition.xyz;",
          "vRimWorldNormal = normalize(mat3(modelMatrix) * objectNormal);",
        ].join("\n"),
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "void main() {",
        [
          "uniform vec3 rimColor;",
          "uniform float rimIntensity;",
          "uniform vec3 rimLightDirection;",
          "varying vec3 vRimWorldNormal;",
          "varying vec3 vRimWorldPosition;",
          "void main() {",
        ].join("\n"),
      )
      .replace(
        "#include <dithering_fragment>",
        [
          "vec3 rimViewDirection = normalize(cameraPosition - vRimWorldPosition);",
          "vec3 rimNormal = normalize(vRimWorldNormal);",
          "float rimFresnel = pow(1.0 - max(dot(rimViewDirection, rimNormal), 0.0), 2.35);",
          "float rimBacklight = smoothstep(0.15, 1.0, dot(rimNormal, normalize(-rimLightDirection)) * 0.5 + 0.5);",
          "gl_FragColor.rgb += rimColor * rimIntensity * rimFresnel * rimBacklight;",
          "#include <dithering_fragment>",
        ].join("\n"),
      );
  };
  material.customProgramCacheKey = () => "style-genome-rim-v1";
  return material;
}

export function createLightingRig(scene: THREE.Scene): LightingRig {
  const target = new THREE.Object3D();
  target.name = "style-genome-light-target";
  scene.add(target);

  const sun = new THREE.DirectionalLight("#fff2dc", 2.1);
  sun.name = "style-genome-sun";
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  sun.shadow.bias = -0.00025;
  sun.shadow.normalBias = 0.018;
  sun.target = target;
  scene.add(sun);

  const rim = new THREE.DirectionalLight("#c8dcff", 0.28);
  rim.name = "style-genome-rim";
  rim.castShadow = false;
  rim.target = target;
  scene.add(rim);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(80, 80),
    new THREE.ShadowMaterial({
      color: "#000000",
      opacity: 0.3,
      transparent: true,
    }),
  );
  ground.name = "style-genome-shadow-catcher";
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  return {
    sun,
    rim,
    target,
    ground,
    lastAzimuth: Number.NaN,
    lastElevation: Number.NaN,
  };
}

export function updateLightingRig(rig: LightingRig, update: LightingUpdate): boolean {
  const progress = update.reducedMotion ? 0.68 : clamp01(update.scrollProgress);
  const center = update.bounds.getCenter(new THREE.Vector3());
  const size = update.bounds.getSize(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z, 8) * 2.25;
  const azimuth = lerp(-60, 240, progress) * DEG;
  const baselineElevation = lerp(18, 5, progress);
  const elevationDeg = baselineElevation + Math.sin(Math.PI * progress) * 48;
  const elevation = elevationDeg * DEG;

  const x = Math.cos(azimuth) * Math.cos(elevation) * radius;
  const y = Math.sin(elevation) * radius;
  const z = Math.sin(azimuth) * Math.cos(elevation) * radius;
  rig.sun.position.set(center.x + x, center.y + y, center.z + z);
  rig.target.position.copy(center);
  rig.target.updateMatrixWorld();

  rig.rim.position.set(center.x - x, center.y + Math.max(1.5, y * 0.35), center.z - z);
  rig.rim.intensity = 0.18 + (1 - smoothstep(22, 54, elevationDeg)) * 0.18 + update.hoverBoost * 0.08;

  const shadowDirty =
    Math.abs(azimuth - rig.lastAzimuth) > 0.015 ||
    Math.abs(elevation - rig.lastElevation) > 0.01;

  if (shadowDirty) {
    fitShadowCamera(rig.sun.shadow.camera, size);
    rig.sun.shadow.camera.updateProjectionMatrix();
    rig.lastAzimuth = azimuth;
    rig.lastElevation = elevation;
  }

  const sunDirection = rig.sun.position.clone().sub(center).normalize();
  const rimIntensity = 0.08 + (1 - smoothstep(16, 42, elevationDeg)) * 0.56 + update.hoverBoost * 0.18;
  for (const material of update.rimMaterials) {
    const rimData = material.userData as Partial<RimUserData>;
    if (rimData.rimUniforms) {
      rimData.rimUniforms.rimIntensity.value = rimIntensity;
      rimData.rimUniforms.rimLightDirection.value.copy(sunDirection);
    }
  }

  const windowGlow = 0.08 + (1 - smoothstep(8, 18, elevationDeg)) * 1.85 + update.hoverBoost * 0.6;
  for (const material of update.windowMaterials) {
    material.emissiveIntensity = windowGlow;
    material.needsUpdate = true;
  }

  rig.ground.position.set(center.x, -0.015, center.z);
  return shadowDirty;
}

function fitShadowCamera(camera: THREE.OrthographicCamera, size: THREE.Vector3) {
  const reach = Math.max(size.x, size.y, size.z, 6) * 0.8;
  camera.left = -reach;
  camera.right = reach;
  camera.top = reach;
  camera.bottom = -reach;
  camera.near = 0.2;
  camera.far = reach * 5.5;
}

function lerp(start: number, end: number, amount: number): number {
  return start + (end - start) * amount;
}

function smoothstep(edge0: number, edge1: number, value: number): number {
  const t = clamp01((value - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}
