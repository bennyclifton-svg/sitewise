import * as THREE from 'three'
import { box, part } from './terrace-parts'

/** Three rows below the existing eight longitudinal strip footings. */
export function addTerraceFoundations(model: THREE.Group) {
  const rows = [-.38, -7.2, -14.02]
  for (let boundary = 0; boundary < 8; boundary++) {
    // Match the measured centre lines of the source strip footings.
    const x = boundary === 7 ? 48.88 : boundary * 7 + .12
    const house = Math.min(boundary + 1, 7)
    for (const z of rows) {
      const pier = part(model, new THREE.CylinderGeometry(.15, .15, 3, 16), 'structure', house)
      pier.name = 'Bored pier 300 mm diameter, 3 m deep'
      pier.position.set(x, -1.5, z)
    }
  }
  // Existing lengthwise footings remain; these strips tie the three pier rows together.
  for (let house = 1; house <= 7; house++) {
    for (const z of rows) {
      box(model, [7, .45, .76], [(house - 1) * 7 + 3.5, -.625, z], 'structure', house)
        .name = 'Transverse strip footing'
    }
  }
}
