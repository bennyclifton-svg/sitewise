import { expect, it } from 'vitest'
import * as THREE from 'three'
import { addBuildingServices, dwellingPoint, serviceRooms } from './terrace-services'
import data from './terrace-services-data.json'

it('provides a light and GPO for every named room in all seven mirrored dwellings', () => {
  const model = new THREE.Group()
  addBuildingServices(model)
  for (let house = 1; house <= 7; house++) {
    for (const room of serviceRooms) {
      const parts = model.children.filter(p => p.userData.sw_dwelling === house)
      expect(parts.some(p => p.name === `${room.name} light`)).toBe(true)
      expect(parts.some(p => p.name === `${room.name} double GPO`)).toBe(true)
    }
  }
  expect(model.children.filter(p => p.userData.sw_condenserFan)).toHaveLength(7)
  expect(model.children.filter(p => p.name === 'Wet area extract to side-facing rear outlet')).toHaveLength(28)
  expect(model.children.filter(p => p.name === 'Wet area floor waste')).toHaveLength(21)
  expect(model.children.filter(p => p.name === 'Laundry floor waste')).toHaveLength(7)
  for (const mesh of model.children) {
    if (!(mesh instanceof THREE.Mesh)) continue
    const position = mesh.geometry.getAttribute('position')
    expect(Array.from(position.array).every(Number.isFinite)).toBe(true)
    if (mesh.name === '200 mm flexible supply duct') expect((mesh.geometry as THREE.TubeGeometry).parameters.radius).toBe(.1)
    mesh.geometry.dispose()
  }
})

it('uses the same layout mirrored in alternating homes and separates drainage from context', () => {
  expect(dwellingPoint(1, [2, 3, -4])).toEqual([2, 3, -4])
  expect(dwellingPoint(2, [2, 3, -4])).toEqual([12, 3, -4])
  expect(dwellingPoint(5, [2, 3, -4])).toEqual([30, 3, -4])
  expect(data.actions.find(a => a.name === 'TH01 | Eaves gutter')?.memberships).toEqual(['civil'])
  expect(data.actions.find(a => a.name === 'TH01 | Rangehood')?.memberships).toEqual(['mechanical', 'electrical'])
  expect(data.actions.find(a => a.name === 'TH01 | Garage approach')?.action).toBe('context')
})
