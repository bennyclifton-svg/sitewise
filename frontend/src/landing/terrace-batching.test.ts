import { expect, it } from 'vitest'
import * as THREE from 'three'
import { batchTerrace, compactGeometry } from './terrace-batching'
import { box } from './terrace-parts'
import { terracePartAppearance } from './terrace-material'
import { rollerLift } from './terrace-animation'

it('keeps brickwork separate from smooth surfaces when batching a facade', () => {
  const model = new THREE.Group()
  const render = box(model, [1, 1, 1], [0, 0, 0], 'architecture', 1)
  const brick = box(model, [1, 1, 1], [2, 0, 0], 'architecture', 1)
  ;(render.material as THREE.MeshStandardMaterial).name = 'Pure white exterior render'
  ;(brick.material as THREE.MeshStandardMaterial).name = 'Warm brick 1'
  expect(batchTerrace(model, () => false)).toEqual({ before: 2, after: 2 })
  expect(model.children.map(mesh => ((mesh as THREE.Mesh).material as THREE.Material).name).sort()).toEqual(['Pure white exterior render', 'Warm brick 1'])
})

it('batches static meshes without changing triangles, transforms or discipline ownership', () => {
  const model = new THREE.Group()
  const room = new THREE.Group(); room.position.set(12, 3, -7); model.add(room)
  box(room, [1, 1, 1], [0, 0, 0], 'electrical', 5)
  box(room, [1, 1, 1], [2, 0, 0], 'electrical', 5)
  box(room, [1, 1, 1], [4, 0, 0], 'mechanical', 5)
  const oldBounds = new THREE.Box3().setFromObject(model)
  expect(batchTerrace(model, () => false)).toEqual({ before: 3, after: 2 })
  expect(new THREE.Box3().setFromObject(model).equals(oldBounds)).toBe(true)
  const meshes = model.children.filter(o => o instanceof THREE.Mesh) as THREE.Mesh[]
  expect(meshes.reduce((total, mesh) => total + mesh.geometry.index!.count / 3, 0)).toBe(36)
  expect(meshes.filter(mesh => terracePartAppearance(mesh.userData.sw_system, 5, 'electrical').visible)).toHaveLength(1)
})

it('batches within moving groups but keeps roller transforms and context filters separate', () => {
  const model = new THREE.Group(), rotor = new THREE.Group()
  rotor.userData.sw_rotor = 1; rotor.position.y = 8; model.add(rotor)
  box(rotor, [1, 1, 1], [0, 0, 0], 'mechanical', 1)
  box(rotor, [1, 1, 1], [1, 0, 0], 'mechanical', 1)
  const slat = box(model, [1, .1, .1], [0, 2, 0], 'architecture', 1)
  slat.userData.sw_roller = { index: 0, front: 0 }
  box(model, [1, 1, 1], [0, 0, 0], 'civil', 1).userData.sw_contextOnly = true
  box(model, [1, 1, 1], [2, 0, 0], 'civil', 1)
  batchTerrace(model, () => false)
  expect(rotor.children).toHaveLength(1)
  expect(slat.parent).toBe(model)
  expect(model.children.filter(o => o.userData.sw_system === 'civil')).toHaveLength(2)
  expect(rotor.children[0].userData.sw_animatedDetail).toBe(true)
})

it('removes unreferenced vertices and keeps the roller door open after its first lift', () => {
  const geometry = new THREE.BoxGeometry(1, 1, 1)
  geometry.setIndex([0, 1, 2])
  const compact = compactGeometry(geometry)
  expect(compact.getAttribute('position').count).toBe(3)
  expect(compact.index!.count).toBe(3)
  expect(rollerLift(0)).toBe(0)
  expect(rollerLift(5)).toBeGreaterThan(0)
  for (const time of [8, 30, 36, 72, 3600]) expect(rollerLift(time)).toBe(2.5)
  expect(rollerLift(0, true)).toBe(2.5)
})
