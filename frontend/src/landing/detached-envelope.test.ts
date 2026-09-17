import { expect, it } from 'vitest'
import * as THREE from 'three'
import { createDetachedHouse } from './detached-house'
import { detachedLayout as layout } from './detached-layout'
import { batchDetached } from './detached-material'
import { frontRoof, frontRoofHeight } from './detached-front-roof'

it('uses rectangular trusses, open gutters, soffits and grounded exterior walls', () => {
  const home = createDetachedHouse(1)
  const named = (name: string) => home.children.filter(object => object.name === name) as THREE.Mesh[]
  expect(named('Rectangular timber truss').length).toBeGreaterThan(0)
  expect(named('Rectangular timber truss').every(mesh => mesh.geometry.type === 'BoxGeometry')).toBe(true)
  expect(named('Open half-round gutter').length).toBeGreaterThan(0)
  expect(named('Folded metal ridge capping').length).toBeGreaterThan(0)
  expect(named('Continuous ceiling and eave soffit')).toHaveLength(2)
  expect(named('Balcony brick corbel')).toHaveLength(2)
  for (const name of ['Left elevation face brickwork', 'Porch brick pier base']) {
    expect(Math.min(...named(name).map(mesh => new THREE.Box3().setFromObject(mesh).min.y))).toBeCloseTo(0)
  }
  home.traverse(object => { if (object instanceof THREE.Mesh) { object.geometry.dispose(); (object.material as THREE.Material).dispose() } })
})

it('sets pier heights and wraps house two cladding above the garage only', () => {
  for (const number of [1, 2, 4]) {
    const home = createDetachedHouse(number)
    const piers = home.children.filter(object => object.name === 'Porch brick pier base')
    expect(piers).toHaveLength(2)
    if (number !== 2) for (const pier of piers) {
      expect(new THREE.Box3().setFromObject(pier).max.y).toBeCloseTo(number === 1 ? layout.upper + 1.02 : layout.ceiling)
      expect(((pier as THREE.Mesh).material as THREE.Material).name).toBe(number === 1 ? 'Warm brick 1' : 'Detached stone cladding')
    }
    if (number === 2) {
      const cladding = home.children.filter(object => object instanceof THREE.Mesh && (object.material as THREE.Material).name === 'Detached lapped weatherboards')
      expect(cladding.length).toBeGreaterThan(0)
      expect(cladding.some(object => object.name.startsWith('Upper side'))).toBe(true)
      const materialAt = (x: number, y: number, z: number, direction: THREE.Vector3) => {
        home.updateMatrixWorld(true)
        const hit = new THREE.Raycaster(new THREE.Vector3(x, y, z), direction).intersectObject(home).find(hit => hit.object.userData.sw_system === 'architecture')
        return ((hit?.object as THREE.Mesh).material as THREE.Material).name
      }
      expect(materialAt(7.8, layout.upper - .16, 2, new THREE.Vector3(0, 0, -1))).toBe('Detached lapped weatherboards')
      expect(materialAt(10, 5, -3, new THREE.Vector3(-1, 0, 0))).toBe('Detached lapped weatherboards')
      expect(materialAt(10, 4, -3, new THREE.Vector3(-1, 0, 0))).toBe('Warm brick 1')
      expect(materialAt(-2, 4, -3, new THREE.Vector3(1, 0, 0))).toBe('Warm brick 1')
      expect(home.children.some(object => object.name === 'Vertical window shade' || object.name === 'Upper window reveal')).toBe(false)
      expect(home.children.some(object => object.name === 'Front multi room and entry door' && object.userData.sw_glass)).toBe(true)
    }
    home.traverse(object => { if (object instanceof THREE.Mesh) { object.geometry.dispose(); (object.material as THREE.Material).dispose() } })
  }
})

it('steps the balcony hip forward and preserves the rear roof slopes', () => {
  expect(frontRoofHeight(6, frontRoof.mainFront)).toBe(layout.ceiling)
  expect(frontRoofHeight(1.8, frontRoof.balconyFront)).toBe(layout.ceiling)
  expect(frontRoofHeight(1.8, frontRoof.mainFront)).toBeGreaterThan(layout.ceiling)
  for (const x of [0, 2, 4, 6, 8]) for (const depth of [9, 11, frontRoof.rear]) {
    const original = layout.ceiling + (layout.ridge - layout.ceiling) / 4.45 * Math.min(x + .45, 8.45 - x, frontRoof.rear - depth)
    expect(frontRoofHeight(x, depth)).toBeCloseTo(original)
  }
})

it('leaves the front door and upper glazing unobstructed by facade finishes', () => {
  const house = createDetachedHouse(1)
  house.updateMatrixWorld(true)
  const front = (x: number, y: number) => new THREE.Raycaster(new THREE.Vector3(x, y, 3), new THREE.Vector3(0, 0, -1)).intersectObject(house).filter(hit => hit.object.userData.sw_system === 'architecture')[0]?.object.name
  expect(front(2.5, layout.ground + .2)).toContain('door')
  expect(front(4.6, layout.upper + .75)).toContain('glazing')
  expect(front(7.8, layout.upper - .18)).toContain('Floor-edge')
  expect(house.children.filter(mesh => mesh.name === 'Balcony side handrail')).toHaveLength(4)
  expect(house.children.filter(mesh => mesh.name === 'Garage raised rendered parapet')).toHaveLength(2)
  batchDetached(house)
  const finishes = new Set<string>()
  house.traverse(object => { if (object instanceof THREE.Mesh) finishes.add((object.material as THREE.Material).name) })
  expect(finishes.has('Detached horizontal cladding')).toBe(true)
  expect(finishes.has('Detached render')).toBe(true)
  expect(finishes.has('Warm brick 1')).toBe(true)
  house.traverse(object => {
    if (object instanceof THREE.Mesh) { object.geometry.dispose(); if (!Array.isArray(object.material)) object.material.dispose() }
  })
})
