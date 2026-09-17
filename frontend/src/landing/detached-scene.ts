import * as THREE from 'three'
import { createDetachedHouse } from './detached-house'
import { addDetachedServices } from './detached-services'
import { detachedLayout as layout } from './detached-layout'
import { box, pipe } from './terrace-parts'
import { addDetachedLandscape } from './detached-landscape'
import { addDetachedGarageCar } from './detached-garage'
import { addDetachedStreet, addDetachedMeters } from './detached-street'

export function createDetachedScene(car?: THREE.Group) {
  const model = new THREE.Group()
  const width = layout.count * layout.lotWidth
  for (let house = 1; house <= layout.count; house++) {
    const home = createDetachedHouse(house)
    if (house === 2 && car) addDetachedGarageCar(home, car)
    addDetachedServices(home, house)
    addDetachedMeters(home, house)
    home.position.x = (house - 1) * layout.lotWidth + 1.21
    box(home, [5.4, .06, 5.7], [6.17, .06, 1.55], 'landscape', house).name = 'Driveway'
    box(home, [1, .04, 4.5], [2.1, .05, 2.25], 'landscape', house).name = 'Entry path'
    box(home, [9.8, .035, 4.5], [4.6, .025, -18.0], 'landscape', house).name = 'Rear lawn'
    for (const x of [-1.15, 10.44]) box(home, [.06, 1.6, 21.5], [x, .8, -10.6], 'landscape', house).name = 'Side boundary fence'
    box(home, [11.6, 1.6, .06], [4.615, .8, -21.45], 'landscape', house).name = 'Rear boundary fence'
    addDetachedLandscape(home, house)
    if (house === 2) { home.scale.x = -1; home.position.x += layout.width }
    model.add(home)
  }
  for (const [system, radius, y, z] of [['electrical', .035, -.5, 4.5], ['hydraulic', .06, -1.3, 4.8], ['civil', .16, -.8, 5]] as const) pipe(model, [[0, y, z], [width, y, z]], radius, system).name = `Street ${system} main`
  const plinth = new THREE.Group()
  addDetachedStreet(model)
  for (const [y, depth, colour] of [[-.6, 1.2, '#F4F1EA'], [-1.28, .16, '#087ac9']] as const) {
    const slab = new THREE.Mesh(new THREE.BoxGeometry(width + .4, depth, 27.5), new THREE.MeshStandardMaterial({ color: colour, roughness: .7 }))
    slab.position.set(width / 2, y, -8); slab.receiveShadow = true; plinth.add(slab)
  }
  return { model, plinth }
}
