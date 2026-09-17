import { expect, it } from 'vitest'
import * as THREE from 'three'
import { createDetachedScene } from './detached-scene'
import { detachedLayout, detachedRooms } from './detached-layout'
import { batchDetached } from './detached-material'

it('builds four independent houses with every discipline and an open third envelope', () => {
  const { model, plinth } = createDetachedScene()
  const homes = model.children.filter(object => object.name.startsWith('Detached house'))
  expect(homes).toHaveLength(4)
  expect(detachedRooms.filter(room => room.name.startsWith('Bed '))).toHaveLength(4)
  expect(detachedLayout.upper - detachedLayout.ground).toBeCloseTo(3.07)
  expect(detachedLayout.ground - detachedLayout.garage).toBeCloseTo(.086)
  for (const [i, home] of homes.entries()) {
    expect(home.position.x).toBeCloseTo(i * 11.65 + 1.21 + (i === 1 ? detachedLayout.width : 0))
    expect(home.scale.x).toBe(i === 1 ? -1 : 1)
    const systems = new Set<string>()
    home.traverse(object => { if (object instanceof THREE.Mesh) systems.add(object.userData.sw_system) })
    expect([...systems].sort()).toEqual(['architecture', 'civil', 'electrical', 'hydraulic', 'interiors', 'landscape', 'mechanical', 'structure'])
    expect(home.children.some(object => object.name === 'Hipped tiled roof')).toBe(i !== 2)
    expect(home.children.some(object => object.name === 'Rectangular timber truss')).toBe(true)
    expect(home.children.some(object => object.name === 'Garage switchboard')).toBe(true)
  }
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    const vertices = object.geometry.getAttribute('position').array
    expect(Array.from(vertices).every(Number.isFinite), object.name).toBe(true)
  })
  const before = new THREE.Box3().setFromObject(model)
  const counts = batchDetached(model)
  expect(counts.after).toBeLessThan(140)
  const after = new THREE.Box3().setFromObject(model)
  expect(after.min.distanceTo(before.min)).toBeLessThan(.00001)
  expect(after.max.distanceTo(before.max)).toBeLessThan(.00001)
  for (const root of [model, plinth]) root.traverse(object => {
    if (object instanceof THREE.Mesh) { object.geometry.dispose(); if (!Array.isArray(object.material)) object.material.dispose() }
  })
})
