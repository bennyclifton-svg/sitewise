import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import { createGarageMotion } from './garage-motion'

describe('garage departure', () => {
  it('clears the door before departure, clears the garage before turning, and resets for replay', () => {
    const car = new THREE.Mesh(new THREE.BoxGeometry())
    car.userData.sw_motion = 'car'
    const slat = new THREE.Mesh(new THREE.BoxGeometry())
    slat.userData.sw_motion = 'door:0'
    const pose = createGarageMotion([{mesh:car},{mesh:slat}])
    pose(.2)
    expect(car.position.x).toBeCloseTo(-2.12)
    expect(slat.position.y+.55).toBeGreaterThan(2.475)
    pose(.48)
    expect(car.position.x+2.45).toBeLessThan(-4.81)
    expect(car.rotation.y).toBe(0)
    pose(.67)
    expect(car.position.x).toBeCloseTo(-9.65)
    expect(car.rotation.y).toBeCloseTo(Math.PI/2)
    pose(1)
    expect(slat.position.y).toBeCloseTo(0)
    expect(car.position.z).toBe(19.4)
    expect(car.position.z + 2.45).toBeLessThan(22)
    pose(0)
    expect(car.position.x).toBeCloseTo(-2.12)
    expect(car.position.z).toBeCloseTo(10.93335)
    expect(car.rotation.y).toBe(0)
  })
})
