import { timberRun, roofProfile } from './detached-roof-details'
import * as THREE from 'three'
import { detachedLayout as layout } from './detached-layout'
import { box, part, type Point } from './terrace-parts'
import { tileRelief } from './detached-tile-relief'

export const frontRoof = { left: -.45, right: 8.45, balconyRight: 4.04, balconyFront: -.45, mainFront: .51, rear: 13.16 }

export function frontRoofHeight(x: number, depth: number) {
  const r = frontRoof, slope = (layout.ridge - layout.ceiling) / 4.45
  const main = Math.min(x - r.left, r.right - x, depth - r.mainFront, r.rear - depth, 4.45)
  const balcony = Math.min(x - r.left, r.balconyRight - x, depth - r.balconyFront, r.rear - depth)
  return layout.ceiling + slope * Math.max(0, main, balcony)
}

/** One continuous stepped hip: the balcony projects, while the garage eave returns to its wall. */
export function addDetachedFrontRoof(model: THREE.Group, house: number) {
  const r = frontRoof, envelope = house !== layout.cutaway
  const point = (x: number, d: number, offset = 0): Point => [x, frontRoofHeight(x, d) + offset, -d]
  const tilePoint = (x: number, d: number): Point => {
    const h = frontRoofHeight(x, d)
    const acrossX = Math.abs(frontRoofHeight(x + .01, d) - h) > Math.abs(frontRoofHeight(x, d + .01) - h)
    return [x, h + tileRelief(h, acrossX ? d : x), -d]
  }
  if (envelope) {
    for (const [x0, x1, d0] of [[r.left, r.balconyRight, r.balconyFront], [r.balconyRight, r.right, r.mainFront]]) box(model, [x1 - x0, .04, r.rear - d0], [(x0 + x1) / 2, layout.ceiling - .14, -(d0 + r.rear) / 2], 'architecture', house).name = 'Continuous ceiling and eave soffit'
    const positions: number[] = []
    for (const [x0, x1, d0, d1] of [[r.left, r.balconyRight, r.balconyFront, r.rear], [r.balconyRight, r.right, r.mainFront, r.rear]]) {
      const nx = Math.ceil((x1 - x0) / .09), nd = Math.ceil((d1 - d0) / .09)
      for (let i = 0; i < nx; i++) for (let j = 0; j < nd; j++) {
        const x = x0 + (x1 - x0) * i / nx, xx = x0 + (x1 - x0) * (i + 1) / nx
        const d = d0 + (d1 - d0) * j / nd, dd = d0 + (d1 - d0) * (j + 1) / nd
        positions.push(...tilePoint(x, d), ...tilePoint(xx, d), ...tilePoint(xx, dd), ...tilePoint(x, d), ...tilePoint(xx, dd), ...tilePoint(x, dd))
      }
    }
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3)); geometry.computeVertexNormals()
    const mesh = part(model, geometry, 'architecture', house)
    mesh.name = 'Hipped tiled roof'; (mesh.material as THREE.Material).name = 'Detached roof tiles'
    ;(mesh.material as THREE.Material).side = THREE.DoubleSide
  }
  const outline = [[r.left, r.balconyFront], [r.balconyRight, r.balconyFront], [r.balconyRight, r.mainFront], [r.right, r.mainFront], [r.right, r.rear], [r.left, r.rear], [r.left, r.balconyFront]]
  for (let i = 1; i < outline.length; i++) {
    const [x, d] = outline[i - 1], [xx, dd] = outline[i]
    roofProfile(model, [[x, layout.ceiling, -d], [xx, layout.ceiling, -dd]], 'gutter', house)
    if (envelope) {
      box(model, [Math.max(.04, Math.abs(xx - x)), .18, Math.max(.04, Math.abs(dd - d))], [(x + xx) / 2, layout.ceiling - .09, -(d + dd) / 2], 'architecture', house).name = 'Stepped roof fascia'
    }
  }
  for (let d = -.3; d < r.rear; d += .6) {
    const right = d < r.mainFront ? r.balconyRight : r.right
    const points = Array.from({ length: 25 }, (_, i) => point(r.left + (right - r.left) * i / 24, d, -.08))
    timberRun(model, points, .07, .035, house)
    timberRun(model, [[r.left, layout.ceiling - .08, -d], [right, layout.ceiling - .08, -d]], .07, .035, house)
    for (let x = r.left + .7; x < right; x += .9) timberRun(model, [[x, layout.ceiling - .08, -d], point(x, d, -.08)], .07, .035, house)
  }
  if (envelope) {
    const centre = (r.left + r.balconyRight) / 2, peak = r.balconyFront + (r.balconyRight - r.left) / 2
    for (const path of [
      [[r.left, r.balconyFront], [centre, peak]], [[r.balconyRight, r.balconyFront], [centre, peak]],
      [[centre, peak], [centre, r.mainFront + centre - r.left]],
      [[r.right, r.mainFront], [4, r.mainFront + 4.45]],
      [[4, r.mainFront + 4.45], [4, r.rear - 4.45]],
      [[r.left, r.rear], [4, r.rear - 4.45]], [[r.right, r.rear], [4, r.rear - 4.45]],
    ]) roofProfile(model, path.map(([x, d]) => point(x, d, .015)), 'cap', house)
  }
  const centre = (r.left + r.balconyRight) / 2
  roofProfile(model, [point(centre, r.mainFront + centre - r.left, .015), point(4, r.mainFront + 4.45, .015)], 'cap', house)
  model.children[model.children.length - 1].name = 'Balcony hip to main ridge connector'
}

