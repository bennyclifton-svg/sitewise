import * as THREE from 'three'
import data from './terrace-street-data.json'
import { dwellingPoint } from './terrace-services'
import { removeClosedDoorTriangles } from './terrace-life'
import { box, part, pipe, type Point } from './terrace-parts'

export const poleOffset = .75
const blue = '#087ac9'
export type ServiceRoute = { name: string; system: string; house: number; radius: number; points: Point[] }

export function streetRoutes(): ServiceRoute[] {
  const routes: ServiceRoute[] = []
  const add = (name: string, system: string, house: number, radius: number, points: Point[]) => routes.push({ name, system, house, radius, points })
  add('400 mm stormwater main', 'civil', 0, .2, [[-2, -.75, 6.4], [51, -.75, 6.4]])
  add('Lower sewer main', 'hydraulic', 0, .11, [[-2, -1.9, 5.8], [51, -1.9, 5.8]])
  add('Pole riser and pillar feed', 'electrical', 0, .018, [[50, 8.35, 4.4 + poleOffset], [50, 7.65, 5.24 + poleOffset], [50, 7.05, 5.24 + poleOffset], [50, 6.9, 5.14 + poleOffset], [50, -.45, 5.14 + poleOffset], [4.4, -.45, 5.14 + poleOffset], [4.4, -.45, 3.5], [4.4, .6, 3.5]])
  add('Pillar to distribution conduit', 'electrical', 0, .045, [[4.4, .6, 3.5], [4.4, -.45, 3.5], [4.4, -.45, 4.65]])
  for (const home of data.homes) {
    const h = home.house, x = home.frontDrain[0], wx = home.water[0]
    add('Existing sanitary lateral to lower main', 'hydraulic', h, .055, [home.sewer as Point, [home.sewer[0], -1.9, 5.8]])
    const tank = dwellingPoint(h, [2, -.55, 1.6])
    add('Front pit to detention tank', 'civil', h, .075, [home.frontDrain as Point, [x, -.6, 2.6], [tank[0], -.6, 2.6]])
    add('Detention overflow to stormwater main', 'civil', h, .075, [[tank[0], -.55, 2.6], [tank[0], -.75, 6.4]])
    add('Rear pit to front pit', 'civil', h, .075, [home.rearDrain as Point, [x, -.6, -15.8], [x, -.6, 3.4], home.frontDrain as Point])
    add('Meter supply loop', 'hydraulic', h, .025, [home.water as Point, [wx, -.65, 3.5], [wx, .28, 3.5], [wx + .24, .28, 3.5], [wx + .24, -.65, 3.5], home.coldRiser as Point])
  }
  // Crossarms run perpendicular to the street span, with four separate conductors.
  for (let strand = 0; strand < 4; strand++) {
    add(`Overhead power span ${strand + 1}`, 'electrical', 0, .008, Array.from({ length: 33 }, (_, i) => {
      const t = i / 32
      return [-1 + t * 51, 8.35 - (.48 + strand * .025) * Math.sin(Math.PI * t), 4.4 + strand * .4 + poleOffset] as Point
    }))
  }
  return routes
}

export function addStreet(model: THREE.Group) {
  model.updateMatrixWorld(true)
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    const material = object.material as THREE.MeshStandardMaterial
    const replacements = data.replacements.filter(item => item.house === object.userData.sw_dwelling && item.system === object.userData.sw_system && item.material === material.name)
    if (replacements.length) removeClosedDoorTriangles(object, replacements.map(item => new THREE.Box3(new THREE.Vector3(...item.minimum), new THREE.Vector3(...item.maximum)).expandByScalar(.003)))
    if (Number(object.userData.sw_dwelling) === 0 && /Stormwater green|Cold water blue|Sanitary drainage|Electrical conduit amber/.test(material.name)) object.userData.sw_colour = '#FFFFFF'
  })
  for (const route of streetRoutes()) {
    const mesh = pipe(model, route.points, route.radius, route.system, route.house, '#FFFFFF')
    mesh.name = route.name
    mesh.userData.sw_network = true
  }
  for (const x of [-1, 50]) {
    const pole = part(model, new THREE.CylinderGeometry(.07, .12, 8.6, 12), 'electrical')
    pole.position.set(x, 4.3, 5 + poleOffset)
    box(model, [.10, .12, 1.65], [x, 8.1, 5 + poleOffset], 'electrical')
    for (const z of [4.4, 4.8, 5.2, 5.6]) {
      const insulator = part(model, new THREE.CylinderGeometry(.045, .055, .18, 10), 'electrical')
      insulator.position.set(x, 8.25, z + poleOffset)
      for (const y of [8.20, 8.26, 8.32]) {
        const collar = part(model, new THREE.CylinderGeometry(.065, .065, .025, 10), 'electrical')
        collar.position.set(x, y, z + poleOffset)
      }
    }
    pipe(model, [[x, 7.65, 5 + poleOffset], [x, 8.05, 4.35 + poleOffset]], .018, 'electrical')
    pipe(model, [[x, 7.65, 5 + poleOffset], [x, 8.05, 5.65 + poleOffset]], .018, 'electrical')
  }
  const transformer = part(model, new THREE.CylinderGeometry(.18, .18, .52, 16), 'electrical')
  transformer.name = 'Right pole transformer'
  transformer.position.set(50, 7.32, 5.24 + poleOffset)
  const cap = part(model, new THREE.CylinderGeometry(.20, .20, .045, 16), 'electrical')
  cap.position.set(50, 7.60, 5.24 + poleOffset)
  box(model, [.12, .08, .35], [50, 7.04, 5.10 + poleOffset], 'electrical')
  for (const y of [1.0, 3.0, 5.0, 6.6]) box(model, [.15, .025, .10], [50, y, 5.12 + poleOffset], 'electrical')
  box(model, [.5, 1.05, .35], [4.4, .525, 3.5], 'electrical', 1, blue).name = 'Power distribution pillar'
  for (const home of data.homes) {
    const x = home.frontDrain[0], wx = home.water[0]
    const tank = box(model, [2, .5, 2], dwellingPoint(home.house, [2, -.65, 1.6]), 'civil', home.house)
    tank.name = 'Driveway detention tank 2 m x 2 m x 0.5 m'
    tank.userData.sw_tank = true
    box(model, [.4, .06, .4], dwellingPoint(home.house, [2, -.37, 1.6]), 'civil', home.house)
    for (const z of [3.4, -15.8]) {
      box(model, [.45, .64, .45], [x, -.3, z], 'civil', home.house, blue)
      box(model, [.49, .035, .49], [x, .04, z], 'civil', home.house).name = 'Stormwater pit lid'
    }
    const meter = part(model, new THREE.CylinderGeometry(.10, .10, .14, 12), 'hydraulic', home.house, blue)
    meter.position.set(wx + .12, .28, 3.5)
    box(model, [.36, .08, .25], [wx + .12, .13, 3.5], 'hydraulic', home.house)
  }
  for (const door of data.doors) {
    const [x, y, z] = door.point
    box(model, [.13, .28, .12], [x, y, z], 'electrical', door.house)
    const lens = box(model, [.1, .025, .08], [x, y - .15, z + .02], 'electrical', door.house)
    lens.material.emissive.set('#fff1dc'); lens.material.emissiveIntensity = 1.4
    const wash = new THREE.SpotLight('#fff1dc', 7, 3.2, .48, 1, 2)
    wash.position.set(x, y - .12, z + .05)
    wash.target.position.set(x, .5, z - .23)
    wash.userData.sw_system = 'electrical'
    model.add(wash, wash.target)
    // Local wall light joins the dwelling's board, not an isolated visual fixture.
    pipe(model, [data.homes[door.house - 1].board as Point, [x, 1.4, z - .2], [x, y, z - .2]], .012, 'electrical', door.house)
  }
}

export function varyTrees(model: THREE.Group) {
  model.updateMatrixWorld(true)
  const heights = [.88, 1.1, .96, 1.16, .91, 1.04, .83]
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh) || object.userData.sw_system !== 'landscape') return
    const material = object.material as THREE.MeshStandardMaterial
    if (!/Tree bark|Living foliage/.test(material.name)) return
    const anchors = data.trees.filter(tree => tree.house === object.userData.sw_dwelling)
    const position = object.geometry.getAttribute('position')
    const inverse = object.matrixWorld.clone().invert()
    const world = new THREE.Vector3()
    for (let i = 0; i < position.count; i++) {
      world.fromBufferAttribute(position, i).applyMatrix4(object.matrixWorld)
      const tree = anchors.find(anchor => anchor.rear === (world.z < -9))
      if (!tree) continue
      const scale = heights[(tree.house - 1 + (tree.rear ? 3 : 0)) % heights.length]
      world.sub(new THREE.Vector3(...tree.base)).multiply(new THREE.Vector3(.96 + (scale - 1) * .45, scale, .96 + (scale - 1) * .45)).add(new THREE.Vector3(...tree.base)).applyMatrix4(inverse)
      position.setXYZ(i, world.x, world.y, world.z)
    }
    position.needsUpdate = true
    object.geometry.computeVertexNormals(); object.geometry.computeBoundingBox(); object.geometry.computeBoundingSphere()
  })
}
