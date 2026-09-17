import { expect, it } from 'vitest'
import * as THREE from 'three'
import { rearRoofHeight, removeClosedDoorTriangles } from './terrace-life'
import { blinds, cutawayFinishes, openings, rearBlades } from './terrace-life-data'

it('removes a closed door without removing adjacent facade triangles in the same batch', () => {
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([
    0, 0, 0, 1, 0, 0, 0, 2, 0,
    1.1, 0, 0, 2, 0, 0, 2, 2, 0,
  ], 3))
  const mesh = new THREE.Mesh(geometry)
  mesh.position.x = 10
  mesh.updateMatrixWorld()
  removeClosedDoorTriangles(mesh, [new THREE.Box3(new THREE.Vector3(9.99, -.01, -.01), new THREE.Vector3(11.01, 2.01, .01))])
  expect(Array.from(geometry.getIndex()!.array)).toEqual([3, 4, 5])
})

it('uses repeatable lived-in variation outside the cutaway dwelling', () => {
  expect([...new Set(openings.filter(item => item.kind === 'garage').map(item => item.house))]).toEqual([3, 6])
  expect(openings.filter(item => item.kind === 'entry').every(item => item.house === 1)).toBe(true)
  expect(blinds.every(item => item.house !== 5)).toBe(true)
  expect(blinds.some(item => item.closed === 0)).toBe(true)
  expect(blinds.some(item => item.closed === 1)).toBe(true)
  expect(blinds.some(item => item.closed > 0 && item.closed < 1)).toBe(true)
})

it('rakes only the six shared upper rear blades to the main roof line', () => {
  expect(rearBlades).toHaveLength(6)
  expect(rearBlades.every(blade => blade.house === 0 && blade.minimum[1] > 3 && blade.minimum[0] > 6 && blade.maximum[0] < 43)).toBe(true)
  expect(rearRoofHeight(7.8)).toBeCloseTo(10.3)
  expect(rearRoofHeight(14.6)).toBeCloseTo(8.95)
  expect(rearRoofHeight(17.12)).toBeLessThan(rearRoofHeight(14.35))
})

it('strips only unit 5 finishes while preserving stairs, appliances and services', () => {
  expect(cutawayFinishes.length).toBeGreaterThan(40)
  expect(cutawayFinishes.every(item => item.house === 5)).toBe(true)
  expect(cutawayFinishes.some(item => item.name.includes('Plasterboard ceiling'))).toBe(true)
  expect(cutawayFinishes.some(item => item.name.includes('Wet service riser lining'))).toBe(true)
  expect(cutawayFinishes.some(item => item.name.includes('drywall'))).toBe(true)
  expect(cutawayFinishes.some(item => item.name.includes('timber stud'))).toBe(true)
  expect(cutawayFinishes.some(item => item.name.includes('robe'))).toBe(true)
  expect(cutawayFinishes.some(item => item.name.includes('pleated linen'))).toBe(true)
  expect(cutawayFinishes.filter(item => item.name.includes('door open'))).toHaveLength(9)
  expect(cutawayFinishes.every(item => !/stair screen|stair handrail|bedside|pillow|cabinet|appliance|oven|washing machine|refrigerator/i.test(item.name))).toBe(true)
})
