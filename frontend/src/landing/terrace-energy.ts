import * as THREE from 'three'
import { box, pipe, type Point } from './terrace-parts'
import { rearRoofHeight } from './terrace-life'
import { dwellingPoint, garageSwitchboard } from './terrace-services'

export function addTelecomAndSolar(model: THREE.Group) {
  const white = '#FFFFFF'
  pipe(model, [[-2, -.4, 4.25], [51, -.4, 4.25]], .018, 'electrical', 0, white).name = 'Street telecommunications cable'
  box(model, [.45, .38, .28], [24.5, -.19, 4.25], 'electrical', 0).name = 'Telecommunications footpath pit'
  box(model, [.48, .035, .31], [24.5, .02, 4.25], 'electrical', 0).name = 'Telecommunications pit lid'
  for (let house = 1; house <= 7; house++) {
    const p = (point: Point) => dwellingPoint(house, point)
    const terminal = p([.36, 1.25, -5])
    pipe(model, [p([.36, -.4, 4.25]), p([.36, -.4, -5]), terminal], .012, 'electrical', house).name = 'NBN lead-in to garage wall'
    box(model, [.12, .26, .20], terminal, 'electrical', house).name = 'Garage NBN termination'
    const inverter = p([.36, 1.5, -4])
    box(model, [.18, .55, .38], inverter, 'electrical', house).name = 'Garage solar inverter'
    pipe(model, [inverter, p(garageSwitchboard)], .014, 'electrical', house).name = 'Solar inverter to switchboard'
    const base = (house - 1) * 7
    const cableX = inverter[0]
    const bus: Point = [base + 3.25, 10.37, -7.8]
    pipe(model, [bus, [cableX, 10.37, -7.8], [cableX, 9.65 + 2 * .65 / 5.8 + .07, -4], inverter], .016, 'electrical', house).name = 'Solar cable down garage party wall'
    for (const roof of [
      ...[3.95, 5.85].map(depth => ({ depth, height: 9.65 + (depth - 2) * .65 / 5.8, slope: .65 / 5.8 })),
      ...[9.25, 11.15].map(depth => ({ depth, height: rearRoofHeight(depth), slope: -1.35 / 6.8 })),
    ]) {
      for (const x of [1.7, 2.8, 3.9, 5.0]) {
        // Follow each broad upper roof plane; keep the steep front and rear dormer cap clear.
        const panel = new THREE.Group()
        panel.position.set(base + x, roof.height + .07, -roof.depth)
        panel.rotation.x = Math.atan(roof.slope)
        box(panel, [1.04, .055, 1.7], [0, 0, 0], 'electrical', house).name = 'Solar panel frame'
        box(panel, [.97, .015, 1.63], [0, .035, 0], 'electrical', house, white).name = 'Solar cells'
        for (const z of [-.4, 0, .4]) box(panel, [.97, .004, .009], [0, .045, z], 'electrical', house)
        box(panel, [.009, .004, 1.63], [0, .045, 0], 'electrical', house)
        model.add(panel)
        pipe(model, [[base + x, roof.height + .05, -roof.depth], bus], .012, 'electrical', house)
        for (const z of [-.55, .55]) box(panel, [.8, .025, .04], [0, -.045, z], 'electrical', house)
        panel.traverse(object => { if (object instanceof THREE.Mesh) object.userData.sw_colour = house === 5 ? '#087ac9' : white })
      }
    }
  }
}
