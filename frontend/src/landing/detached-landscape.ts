import * as THREE from 'three'
import { box, part, pipe, type Point } from './terrace-parts'

/** Repeatable branching and individual leaves replace the placeholder crown spheres. */
function tree(parent: THREE.Group, house: number, x: number, z: number, height: number, seed: number, spread = 1) {
  let state = seed
  const random = () => { state = (state * 1664525 + 1013904223) >>> 0; return state / 4294967296 }
  const root = new THREE.Group(); root.position.set(x, 0, z); parent.add(root)
  root.name = 'Ornamental tree'; root.scale.set(spread, 1, spread)
  const trunk = part(root, new THREE.CylinderGeometry(.035, .105, height * .75, 9), 'landscape', house)
  trunk.position.y = height * .375; trunk.rotation.z = .03; trunk.name = 'Branching ornamental tree trunk'
  const vertices: number[] = [], indices: number[] = []
  for (let b = 0; b < 13; b++) {
    const angle = b * 2.39996, startY = height * (.34 + b * .026)
    const radius = height * (.22 + random() * .06) * (1 - b * .027)
    const tip = new THREE.Vector3(Math.cos(angle) * radius, startY + height * .22, Math.sin(angle) * radius)
    pipe(root, [[0, startY, 0], [tip.x * .42, startY + height * .1, tip.z * .42], tip.toArray() as Point], .014 + .012 * (1 - b / 13), 'landscape', house).name = 'Tree branch'
    for (let twig = 0; twig < 5; twig++) {
      const end = tip.clone().add(new THREE.Vector3((random() - .5) * .5, random() * height * .1, (random() - .5) * .5))
      pipe(root, [tip.clone().multiplyScalar(.78).toArray() as Point, end.toArray() as Point], .006, 'landscape', house).name = 'Tree twig'
      for (let leaf = 0; leaf < 20; leaf++) {
        const centre = end.clone().add(new THREE.Vector3((random() - .5) * .7, (random() - .5) * .5, (random() - .5) * .7))
        const length = .10 + random() * .10, width = length * .33
        const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(random() * 1.8 - .9, random() * Math.PI * 2, random() * .8))
        const points = [[0, .018, 0], [0, 0, -length], [-width, 0, -length * .3], [-width * .7, 0, length * .45], [0, 0, length], [width * .7, 0, length * .45], [width, 0, -length * .3]]
        const first = vertices.length / 3
        points.forEach(p => vertices.push(...new THREE.Vector3(...p).applyQuaternion(q).add(centre).toArray()))
        for (let i = 1; i <= 6; i++) indices.push(first, first + i, first + (i === 6 ? 1 : i + 1))
      }
    }
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3)); geometry.setIndex(indices); geometry.computeVertexNormals()
  const leaves = part(root, geometry, 'landscape', house)
  leaves.name = 'Individual tree leaves'; (leaves.material as THREE.Material).side = THREE.DoubleSide
}

export function addDetachedLandscape(home: THREE.Group, house: number) {
  const moved = house === 2 || house === 3
  const frontTreeDepth = house === 2 ? 1.5 : house === 3 ? .7 : 2.5
  tree(home, house, moved ? 9.65 : -.15, frontTreeDepth, [3.25, 4.1, 3.6, 2.9][house - 1], house * 117, [1, .62, .8, 1.15][house - 1])
  if (moved) {
    const z = frontTreeDepth
    for (const x of [9.04, 10.26]) box(home, [.10, .35, 1.5], [x, .175, z], 'landscape', house).name = 'Tree planter side'
    for (const edge of [-.7, .7]) box(home, [1.22, .35, .10], [9.65, .175, z + edge], 'landscape', house).name = 'Tree planter end'
  }
  tree(home, house, 1.1, -18.7, 4.0, house * 313)
  tree(home, house, 8.1, -18.2, 4.4, house * 521)
  for (const [x, z, width, depth] of [[.05, 1.65, 2.05, 3.8], [3.03, 1.6, .5, 3.9], [8.9, 2.15, .65, 3.0]]) {
    box(home, [width, .055, depth], [x, .05, z], 'landscape', house).name = 'Front garden bed'
    for (const edge of [-1, 1]) box(home, [.035, .13, depth], [x + edge * width / 2, .1, z], 'landscape', house).name = 'Garden steel edging'
    for (let i = 0; i < 16; i++) {
      const cx = x + Math.sin(i * 7.1 + house) * width * .38, cz = z - depth * .4 + i / 16 * depth * .8
      const positions: number[] = [], indices: number[] = []
      for (let blade = 0; blade < 11; blade++) {
        const a = blade * 2.399, h = .22 + .14 * Math.abs(Math.sin(blade + i)), first = positions.length / 3
        const dx = Math.cos(a), dz = Math.sin(a)
        positions.push(cx - dz * .012, .09, cz + dx * .012, cx + dz * .012, .09, cz - dx * .012,
          cx + dx * .1 - dz * .009, h, cz + dz * .1 + dx * .009, cx + dx * .1 + dz * .009, h, cz + dz * .1 - dx * .009,
          cx + dx * .21, h * .65, cz + dz * .21)
        indices.push(first, first + 1, first + 2, first + 1, first + 3, first + 2, first + 2, first + 3, first + 4)
      }
      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3)); geometry.setIndex(indices); geometry.computeVertexNormals()
      const plant = part(home, geometry, 'landscape', house); plant.name = 'Strappy groundcover'; (plant.material as THREE.Material).side = THREE.DoubleSide
    }
  }
  const body = box(home, [.44, .70, .36], [.14, .35, 3.98], 'landscape', house)
  body.name = 'Front letterbox'
  box(home, [.44, .14, .36], [.14, .83, 3.98], 'landscape', house).name = 'Letterbox slot lintel'
  for (const x of [-.045, .325]) box(home, [.07, .06, .36], [x, .73, 3.98], 'landscape', house).name = 'Letterbox slot jamb'
  const recess = box(home, [.30, .06, .02], [.14, .73, 3.82], 'landscape', house)
  recess.name = 'Recessed letterbox mail slot'
  // A dark cavity remains legible through the white study-model material pass.
  recess.geometry.setAttribute('color', new THREE.Float32BufferAttribute(new Array(recess.geometry.getAttribute('position').count * 3).fill(.035), 3))
  ;(recess.material as THREE.MeshStandardMaterial).vertexColors = true
  box(home, [.48, .04, .4], [.14, .92, 3.98], 'landscape', house).name = 'Letterbox cap'
  for (let i = 0; i < 4; i++) box(home, [.9, .045, .7], [2.1, .075, .3 + i * .9], 'landscape', house).name = 'Entry paving jointed slab'
}
