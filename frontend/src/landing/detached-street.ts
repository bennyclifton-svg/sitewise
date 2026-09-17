import * as THREE from 'three'
import { box, pipe, part, type Point } from './terrace-parts'
import { detachedLayout as layout } from './detached-layout'

export function addDetachedStreet(model: THREE.Group) {
  const width = layout.count * layout.lotWidth
  // Front of the plinth is z=5.75; keep the path flush to that edge.
  box(model, [width + .4, .08, 1.5], [width / 2, .04, 5], 'civil').name = 'Continuous street footpath'
  for (let x = 0; x <= width; x += 1.8) box(model, [.012, .003, 1.5], [x, .082, 5], 'civil').name = 'Footpath expansion joint'
  for (const x of [1.0, width / 2, width - 1.0]) {
    pipe(model, [[x, .08, 4.45], [x, 4.8, 4.45], [x, 5.15, 4.6], [x, 5.35, 4.95], [x, 5.35, 5.5]], .055, 'electrical').name = 'Overhanging street light pole'
    box(model, [.25, .10, .62], [x, 5.3, 5.4], 'electrical').name = 'Street light luminaire'
    box(model, [.21, .02, .53], [x, 5.24, 5.4], 'electrical').name = 'Street light lens'
    box(model, [.22, .12, .22], [x, .14, 4.45], 'electrical').name = 'Street light base'
  }
}

export function addDetachedMeters(home: THREE.Group, house: number) {
  const at: Point = [.55, .25, 3.25]
  pipe(home, [[.3, .08, at[2]], [.3, .25, at[2]], [.8, .25, at[2]], [.8, .08, at[2]]], .018, 'hydraulic', house).name = 'Garden water meter pipe'
  const meter = part(home, new THREE.CylinderGeometry(.075, .075, .10, 12), 'hydraulic', house)
  meter.position.set(...at); meter.name = 'Garden water meter'
  box(home, [.1, .018, .06], [.75, .31, at[2]], 'hydraulic', house).name = 'Water isolation valve'
  for (const [z, system, name, height] of [[-2.0, 'electrical', 'External electricity meter', 1.45], [-2.85, 'hydraulic', 'External gas meter', .8]] as const) {
    box(home, [.20, .55, .42], [9.45, height, z], system, house).name = name
    box(home, [.025, .13, .21], [9.565, height + .07, z], system, house).name = `${name} display`
    pipe(home, [[9.46, .1, z], [9.46, height - .3, z]], .018, system, house).name = `${name} connection`
  }
}
