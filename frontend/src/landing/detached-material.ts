import * as THREE from 'three'
import { batchTerrace } from './terrace-batching'
import { prepareTerraceMaterial } from './terrace-material'

/** Keep finish identity through batching without changing the terrace viewer. */
export function batchDetached(model: THREE.Group) {
  model.updateMatrixWorld(true)
  const groups = new Map<string, THREE.Group>(), meshes: THREE.Mesh[] = []
  model.traverse(object => { if (object instanceof THREE.Mesh) meshes.push(object) })
  for (const mesh of meshes) {
    // Reflection changes triangle winding when the shared batcher bakes transforms.
    if (mesh.matrixWorld.determinant() < 0) {
      mesh.geometry = mesh.geometry.clone()
      if (!mesh.geometry.index) mesh.geometry.setIndex(Array.from({ length: mesh.geometry.getAttribute('position').count }, (_, i) => i))
      const index = mesh.geometry.index!
      for (let i = 0; i < index.count; i += 3) {
        const second = index.getX(i + 1); index.setX(i + 1, index.getX(i + 2)); index.setX(i + 2, second)
      }
    }
    const key = (mesh.material as THREE.Material).name
    let group = groups.get(key)
    if (!group) { group = new THREE.Group(); group.name = key; model.add(group); groups.set(key, group) }
    group.attach(mesh)
  }
  let before = 0, after = 0
  for (const group of groups.values()) {
    const result = batchTerrace(group, () => false)
    before += result.before; after += result.after
  }
  return { before, after }
}

export function prepareDetachedMaterial(material: THREE.MeshStandardMaterial) {
  prepareTerraceMaterial(material)
  const cladding = material.name === 'Detached horizontal cladding'
  const render = material.name === 'Detached render'
  const tiles = material.name === 'Detached roof tiles'
  const stone = material.name === 'Detached stone cladding'
  if (!cladding && !render && !tiles && !stone) return
  material.roughness = render ? .93 : tiles ? .88 : .72
  material.customProgramCacheKey = () => `detached-finish-${cladding ? 'cladding' : tiles ? 'tiles' : stone ? 'stone' : 'render'}-v3`
  material.onBeforeCompile = shader => {
    const varying = 'varying vec3 detachedSurface;\nvarying vec3 detachedNormal;\n'
    shader.vertexShader = varying + shader.vertexShader.replace('#include <project_vertex>', '#include <project_vertex>\ndetachedSurface = (modelMatrix * vec4(transformed, 1.0)).xyz;\ndetachedNormal = mat3(modelMatrix) * normal;')
    shader.fragmentShader = varying + shader.fragmentShader.replace('#include <color_fragment>', `
      #include <color_fragment>
      ${stone ? `
        float run = abs(detachedNormal.x) > abs(detachedNormal.z) ? detachedSurface.z : detachedSurface.x;
        float row = floor(detachedSurface.y / .18);
        float offset = fract(sin(row * 12.9898) * 43758.5453) * .36;
        vec2 cell = vec2(run + offset, detachedSurface.y);
        vec2 edge = abs(mod(cell + vec2(.21, .09), vec2(.42, .18)) - vec2(.21, .09));
        vec2 joint = 1.0 - smoothstep(vec2(.006), vec2(.006) + max(fwidth(cell), vec2(.0001)), edge);
        float tone = fract(sin(dot(floor(cell / vec2(.42, .18)), vec2(12.9898, 78.233))) * 43758.5453);
        diffuseColor.rgb *= .72 + .19 * tone - .20 * max(joint.x, joint.y);
      ` : tiles ? `
        float tileRun = abs(detachedNormal.x) > abs(detachedNormal.z) ? detachedSurface.z : detachedSurface.x;
        float tileRow = floor(detachedSurface.y / .095);
        float tileJoint = abs(mod(tileRun + mod(tileRow, 2.0) * .15 + .15, .3) - .15);
        float tileEdge = 1.0 - smoothstep(.003, .003 + max(fwidth(tileRun), .0001), tileJoint);
        float rowJoint = abs(mod(detachedSurface.y + .0475, .095) - .0475);
        float rowEdge = 1.0 - smoothstep(.002, .002 + max(fwidth(detachedSurface.y), .0001), rowJoint);
        diffuseColor.rgb *= .94 - .13 * tileEdge - .12 * rowEdge;
      ` : cladding ? `
        float courseDistance = abs(mod(detachedSurface.y + .15, .3) - .15);
        float footprint = max(fwidth(detachedSurface.y), .0001);
        float seam = 1.0 - smoothstep(.002, .002 + footprint, courseDistance);
        diffuseColor.rgb *= 1.0 - .27 * seam;
      ` : `
        // Fine aggregate is filtered out below pixel size rather than sparkling at distance.
        vec3 grainCell = floor(detachedSurface * 330.0);
        float grain = fract(sin(dot(grainCell, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
        float grainVisibility = 1.0 - smoothstep(.001, .012, length(fwidth(detachedSurface)));
        diffuseColor.rgb *= .96 + .045 * (grain - .5) * grainVisibility;
      `}
    `)
  }
}
