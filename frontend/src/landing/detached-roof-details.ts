import * as THREE from 'three'
import { box, part, type Point } from './terrace-parts'

export function timberRun(model: THREE.Group, points: Point[], width: number, depth: number, house: number) {
  for (let i = 1; i < points.length; i++) {
    const a = new THREE.Vector3(...points[i - 1]), b = new THREE.Vector3(...points[i]), direction = b.clone().sub(a)
    if (direction.length() < .001) continue
    const beam = box(model, [width, direction.length(), depth], a.clone().add(b).multiplyScalar(.5).toArray() as Point, 'structure', house)
    beam.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize()); beam.name = 'Rectangular timber truss'
  }
}

/** Open profiles: no top face across the gutter and no round ridge member. */
export function roofProfile(model: THREE.Group, points: Point[], kind: 'gutter' | 'cap', house: number) {
  const profile = kind === 'cap' ? [[-.12, -.06], [0, .015], [.12, -.06]] : Array.from({ length: 13 }, (_, i) => {
    const angle = Math.PI * i / 12
    return [-Math.cos(angle) * .075, -Math.sin(angle) * .075]
  })
  for (let i = 1; i < points.length; i++) {
    const a = new THREE.Vector3(...points[i - 1]), b = new THREE.Vector3(...points[i]), direction = b.clone().sub(a).normalize()
    const side = new THREE.Vector3().crossVectors(direction, new THREE.Vector3(0, 1, 0)).normalize()
    const up = new THREE.Vector3().crossVectors(side, direction).normalize(), positions: number[] = []
    const at = (origin: THREE.Vector3, p: number[]) => origin.clone().addScaledVector(side, p[0]).addScaledVector(up, p[1]).toArray()
    for (let j = 1; j < profile.length; j++) positions.push(...at(a, profile[j - 1]), ...at(b, profile[j - 1]), ...at(b, profile[j]), ...at(a, profile[j - 1]), ...at(b, profile[j]), ...at(a, profile[j]))
    const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3)); geometry.computeVertexNormals()
    const mesh = part(model, geometry, kind === 'gutter' ? 'civil' : 'architecture', house)
    mesh.name = kind === 'gutter' ? 'Open half-round gutter' : 'Folded metal ridge capping'; (mesh.material as THREE.Material).side = THREE.DoubleSide
  }
}
