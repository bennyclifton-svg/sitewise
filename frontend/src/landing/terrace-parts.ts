import * as THREE from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

export type Point = [number, number, number]
export function part(parent: THREE.Object3D, geometry: THREE.BufferGeometry, system: string, house = 0, colour?: string) {
  const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: colour ?? '#FFFFFF', roughness: .55 }))
  mesh.userData = { sw_system: system, sw_dwelling: house, ...(colour ? { sw_colour: colour } : {}) }
  parent.add(mesh)
  return mesh
}
export function box(parent: THREE.Object3D, size: Point, position: Point, system: string, house = 0, colour?: string) {
  const mesh = part(parent, new THREE.BoxGeometry(...size), system, house, colour)
  mesh.position.set(...position)
  return mesh
}
export function pipe(parent: THREE.Object3D, points: Point[], radius: number, system: string, house = 0, colour?: string) {
  points = points.filter((point, i) => i === 0 || new THREE.Vector3(...point).distanceTo(new THREE.Vector3(...points[i - 1])) > .00001)
  const pieces = points.slice(1).map((point, i) => {
    const a = new THREE.Vector3(...points[i]), b = new THREE.Vector3(...point)
    const direction = b.clone().sub(a)
    const geometry = new THREE.CylinderGeometry(radius, radius, direction.length(), 8)
    geometry.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize()))
    geometry.translate(...a.add(b).multiplyScalar(.5).toArray())
    return geometry
  })
  const merged = mergeGeometries(pieces)
  pieces.forEach(geometry => geometry.dispose())
  return part(parent, merged, system, house, colour)
}
