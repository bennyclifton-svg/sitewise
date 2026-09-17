import * as THREE from 'three'
import { box, part } from './terrace-parts'
import { detachedLayout as layout, detachedFacades } from './detached-layout'

/** A fixed irregular allocation keeps furnishings stable between renders. */
export function addDetachedWindowFurnishings(model: THREE.Group, house: number) {
  const upper = layout.upper
  if (house === 1 || house === 2) {
    const widths = house === 1 ? [.48, .63] : [.75, .38]
    for (const [left, width] of [[.34, widths[0]], [2.70 - widths[1], widths[1]]]) {
      const geometry = new THREE.PlaneGeometry(width, 2.04, 40, 1)
      const positions = geometry.getAttribute('position')
      for (let i = 0; i < positions.count; i++) positions.setZ(i, .035 * Math.sin((positions.getX(i) + width / 2) / width * Math.PI * 12))
      geometry.computeVertexNormals()
      const curtain = part(model, geometry, 'interiors', house)
      curtain.name = 'Main bedroom pleated curtain'
      curtain.position.set(left + width / 2, upper + 1.07, -1.13)
      const material = curtain.material as THREE.MeshStandardMaterial
      material.name = 'Curtain linen'; material.side = THREE.DoubleSide; material.roughness = 1
    }
    box(model, [2.48, .035, .035], [1.52, upper + 2.13, -1.13], 'interiors', house).name = 'Bedroom curtain track'
  }
  const drops = [[0, .68], [.38, 0, .87], [0, 0], [0, .56, 0]][house - 1]
  const starts = detachedFacades[house - 1].windows === 2 ? [4.5, 6.3] : [4.3, 5.65, 7]
  const width = detachedFacades[house - 1].windows === 2 ? .79 : .54
  starts.forEach((x, index) => {
    const drop = drops[index]
    if (!drop) return
    const height = 1.46 * drop, centre = x + width / 2 + .03
    box(model, [width, height, .018], [centre, upper + 2.09 - height / 2, -1.09], 'interiors', house).name = 'Partly lowered roller blind'
    box(model, [width + .025, .035, .035], [centre, upper + 2.09 - height, -1.09], 'interiors', house).name = 'Blind weighted hem'
    box(model, [width + .025, .055, .055], [centre, upper + 2.10, -1.09], 'interiors', house).name = 'Blind roller cassette'
  })
}
