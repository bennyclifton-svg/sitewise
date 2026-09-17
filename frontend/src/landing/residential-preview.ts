import * as THREE from 'three'
import { createDetachedScene } from './detached-scene'
import { detachedLayout } from './detached-layout'
import { batchDetached, prepareDetachedMaterial } from './detached-material'

export function createResidentialPreview(car?: THREE.Group) {
  const { model, plinth } = createDetachedScene(car)
  batchDetached(model)
  const root = new THREE.Group()
  root.add(model, plinth)
  const meshes: THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>[] = []
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh) || !(object.material instanceof THREE.MeshStandardMaterial)) return
    prepareDetachedMaterial(object.material)
    const blue = object.userData.sw_dwelling === detachedLayout.cutaway
    object.material.color.set(blue ? '#087ac9' : '#FFFFFF')
    if (object.userData.sw_glass) {
      object.material.color.set(blue ? '#087ac9' : '#7f929f')
      object.material.roughness = .2
      object.material.transparent = true
      object.material.opacity = .58
      object.material.depthWrite = false
    }
    object.castShadow = !object.userData.sw_glass
    object.receiveShadow = true
    meshes.push(object as THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>)
  })
  const bounds = new THREE.Box3().setFromObject(root)
  const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), .025)
  function select(system: string) {
    plinth.visible = system === 'all'
    for (const mesh of meshes) {
      const cutaway = mesh.userData.sw_dwelling === detachedLayout.cutaway
      mesh.visible = system === 'all'
        ? !(cutaway && mesh.userData.sw_system === 'architecture')
        : mesh.userData.sw_system === system
      mesh.material.clippingPlanes = system === 'all' ? [ground] : []
    }
  }
  function dispose() {
    root.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return
      object.geometry.dispose()
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.forEach(material => material.dispose())
    })
  }
  return { root, meshes, bounds, select, dispose }
}
