import * as THREE from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'
import { isTerraceBrick } from './terrace-brick'

function moving(object: THREE.Object3D) {
  const d = object.userData
  return Boolean(d.sw_rotor || d.sw_condenserFan || d.sw_roller || d.sw_bird || d.sw_wing)
}

/** Remove unused source vertices left behind by the reversible cutaway edits. */
export function compactGeometry(source: THREE.BufferGeometry): THREE.BufferGeometry {
  const position = source.getAttribute('position'), normal = source.getAttribute('normal')
  const index = source.index
  const indices: number[] = [], positions: number[] = [], normals: number[] = []
  const remap = new Map<number, number>()
  for (let i = 0; i < (index?.count ?? position.count); i++) {
    const old = index ? index.getX(i) : i
    let next = remap.get(old)
    if (next === undefined) {
      next = remap.size; remap.set(old, next)
      positions.push(position.getX(old), position.getY(old), position.getZ(old))
      if (normal) normals.push(normal.getX(old), normal.getY(old), normal.getZ(old))
    }
    indices.push(next)
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setIndex(indices)
  if (normal) geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3))
  else geometry.computeVertexNormals()
  return geometry
}

/** Bake static transforms and batch by the exact visibility/material state used by filters. */
export function batchTerrace(model: THREE.Group, backdrop: (name: string, system: string) => boolean) {
  model.updateMatrixWorld(true)
  const batches = new Map<THREE.Object3D, Map<string, { meshes: THREE.Mesh[]; glass: boolean }>>()
  const discarded: THREE.Mesh[] = []
  let before = 0
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    before++
    const material = object.material as THREE.MeshStandardMaterial
    if (!material.isMeshStandardMaterial || material.map || material.normalMap || material.vertexColors) return
    if (backdrop(object.name, String(object.userData.sw_system)) || object.geometry.index?.count === 0) { discarded.push(object); return }
    // A moving mesh (roller slat) retains its own transform. Other moving roots can batch internally.
    if (moving(object)) return
    let root: THREE.Object3D = object.parent ?? model
    while (root !== model && !moving(root)) root = root.parent ?? model
    const d = object.userData
    const glass = Boolean(d.sw_glass) || material.name === 'Glazing'
    const key = JSON.stringify([d.sw_system, d.sw_dwelling, d.sw_service_systems ?? '[]', d.sw_colour,
      Boolean(d.sw_contextOnly), d.sw_fit !== false, glass, isTerraceBrick(material), material.side, material.emissive.getHex(), material.emissiveIntensity,
      material.transparent, material.opacity, material.depthWrite])
    if (!batches.has(root)) batches.set(root, new Map())
    const groups = batches.get(root)!
    if (!groups.has(key)) groups.set(key, { meshes: [], glass })
    groups.get(key)!.meshes.push(object)
  })
  const oldGeometry = new Set<THREE.BufferGeometry>(), oldMaterials = new Set<THREE.Material>()
  const remove = (mesh: THREE.Mesh) => {
    mesh.removeFromParent(); oldGeometry.add(mesh.geometry)
    if (!Array.isArray(mesh.material)) oldMaterials.add(mesh.material)
  }
  for (const [root, groups] of batches) {
    const inverse = root.matrixWorld.clone().invert()
    for (const { meshes, glass } of groups.values()) {
      const source = meshes[0]
      const pieces = meshes.map(mesh => compactGeometry(mesh.geometry).applyMatrix4(new THREE.Matrix4().multiplyMatrices(inverse, mesh.matrixWorld)))
      const geometry = mergeGeometries(pieces)!
      pieces.forEach(piece => piece.dispose())
      geometry.computeBoundingBox(); geometry.computeBoundingSphere()
      const material = (source.material as THREE.MeshStandardMaterial).clone()
      const batch = new THREE.Mesh(geometry, material)
      batch.name = `Batched ${source.userData.sw_system} townhouse ${source.userData.sw_dwelling}`
      batch.userData = { ...source.userData, sw_glass: glass, sw_animatedDetail: root !== model }
      root.add(batch)
      meshes.forEach(remove)
    }
  }
  discarded.forEach(remove)
  oldGeometry.forEach(geometry => geometry.dispose()); oldMaterials.forEach(material => material.dispose())
  let after = 0
  model.traverse(object => { if (object instanceof THREE.Mesh) after++ })
  return { before, after }
}
