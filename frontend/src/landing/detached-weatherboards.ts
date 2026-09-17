import * as THREE from 'three'
import { box, part } from './terrace-parts'
import { detachedLayout as layout } from './detached-layout'

/** Replace house two's flat 240 mm skin with a 120 mm lapped profile. */
export function refineDetachedWeatherboards(model: THREE.Group, house: number) {
  if (house !== 2) return
  // The new lap recedes to 30 mm but studs extend 45 mm: move the framing
  // behind the skin, retaining it for the structural discipline view.
  for (const object of model.children) {
    if (object.userData.sw_system !== 'structure') continue
    if (object.name.startsWith('Upper front ')) object.position.z -= .08
    if (object.name.startsWith('Upper side ') && object.position.x > 7.8) object.position.x -= .08
  }
  const skins = model.children.filter((object): object is THREE.Mesh => object instanceof THREE.Mesh && (object.material as THREE.Material).name === 'Detached horizontal cladding')
  for (const skin of skins) {
    const bounds = new THREE.Box3().setFromObject(skin)
    const side = bounds.max.x - bounds.min.x < .3 && skin.position.x === 8
    let start = side ? bounds.min.z : bounds.min.x
    let end = side ? bounds.max.z : bounds.max.x
    // Front boards cover the side-board ends; no open square at the corner.
    if (!side) {
      start = Math.max(-.06, start <= 0 ? start - .06 : start)
      end = Math.min(8.06, end >= 8 ? end + .06 : end)
    }
    const pitch = .15, datum = layout.upper - .32
    for (let row = Math.floor((bounds.min.y - datum) / pitch); datum + row * pitch < bounds.max.y - .0001; row++) {
      const base = datum + row * pitch
      const low = Math.max(base, bounds.min.y), high = Math.min(base + pitch, bounds.max.y)
      const face = (y: number) => .06 - .03 * (y - base) / pitch
      const point = (run: number, y: number, offset: number) => side ? [8 + offset, y, run] : [run, y, -.96 + offset]
      const vertices = [point(start, low, -.06), point(end, low, -.06), point(end, high, -.06), point(start, high, -.06), point(start, low, face(low)), point(end, low, face(low)), point(end, high, face(high)), point(start, high, face(high))]
      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices.flat(), 3))
      geometry.setIndex([0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,0,4,7,0,7,3,1,2,6,1,6,5])
      const surface = geometry.toNonIndexed(); surface.computeVertexNormals(); geometry.dispose()
      const board = part(model, surface, 'architecture', house)
      board.name = skin.name
      const material = board.material as THREE.MeshStandardMaterial
      material.name = 'Detached lapped weatherboards'; material.side = THREE.DoubleSide; material.roughness = .82
    }
    model.remove(skin); skin.geometry.dispose(); (skin.material as THREE.Material).dispose()
  }
  for (const x of [0, 8]) {
    const trim = box(model, [x === 0 ? .26 : .14, layout.ceiling - layout.upper + .32, .14], [x, (layout.ceiling + layout.upper - .32) / 2, -.96], 'architecture', house)
    trim.name = 'Weatherboard closed corner trim'
  }
  const junction = box(model, [.14, layout.ceiling - layout.upper + .32, .08], [8, (layout.ceiling + layout.upper - .32) / 2, -6.86], 'architecture', house)
  junction.name = 'Weatherboard to brick vertical junction'
}
