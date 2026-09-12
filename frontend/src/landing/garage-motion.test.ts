import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import { createGarageMotion } from './garage-motion'

describe('garage departure', () => {
  it('clears the door before departure, clears the garage before turning, and resets for replay', () => {
    const car = new THREE.Mesh(new THREE.BoxGeometry())
    car.userData.sw_motion = 'car'
    car.userData.sw_car_origin = [-2.12, .5, 6.51305]
    const parked = new THREE.Mesh(new THREE.BoxGeometry())
    parked.position.set(-3, .28, -13.5)
    const slat = new THREE.Mesh(new THREE.BoxGeometry())
    slat.userData.sw_motion = 'door:0'
    const pose = createGarageMotion([{mesh:car},{mesh:slat},{mesh:parked}])
    pose(.2)
    expect(car.position.x).toBeCloseTo(-2.12)
    expect(slat.position.y+.55).toBeGreaterThan(2.475)
    pose(.48)
    expect(car.position.x+2.45).toBeLessThan(-4.81)
    expect(car.rotation.y).toBe(0)
    pose(.69)
    expect(car.position.x).toBeCloseTo(-9.65)
    expect(car.rotation.y).toBeCloseTo(Math.PI/2)
    pose(1)
    expect(slat.position.y).toBeCloseTo(0)
    expect(car.position.z).toBeCloseTo(19.4)
    expect(car.position.z + 2.45).toBeLessThan(22)
    pose(0)
    expect(car.position.x).toBeCloseTo(-2.12)
    expect(car.position.z).toBeCloseTo(6.51305)
    expect(car.rotation.y).toBe(0)
    expect(parked.position.toArray()).toEqual([-3, .28, -13.5])
  })

  it('rolls continuously through the corner, accelerates on the straight and brakes at the gate', () => {
    const car = new THREE.Mesh(new THREE.BoxGeometry())
    car.userData.sw_motion = 'car'
    car.userData.sw_car_origin = [-2.12, .5, 6.51305]
    const pose = createGarageMotion([{mesh:car}])
    const rear = (t: number) => {
      pose(t)
      return new THREE.Vector2(car.position.x+1.4*Math.cos(car.rotation.y), car.position.z-1.4*Math.sin(car.rotation.y))
    }
    const speed = (t: number) => rear(t-.0001).distanceTo(rear(t+.0001))/.0002
    for (const t of [.48,.69,.83]) {
      expect(speed(t)).toBeGreaterThan(15)
      expect(Math.abs(speed(t-.0003)-speed(t+.0003))).toBeLessThan(.5)
    }
    const a=rear(.56), b=rear(.5601)
    pose(.56005)
    const forward=new THREE.Vector2(-Math.cos(car.rotation.y),Math.sin(car.rotation.y))
    expect(b.sub(a).normalize().dot(forward)).toBeGreaterThan(.9999)
    expect(speed(.81)).toBeGreaterThan(speed(.70))
    expect(speed(.95)).toBeLessThan(speed(.85))
    expect(speed(.97)).toBeLessThan(.1)
  })
})
