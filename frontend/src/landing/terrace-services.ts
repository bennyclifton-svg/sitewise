import * as THREE from 'three'
import data from './terrace-services-data.json'
import { box, part, pipe, type Point } from './terrace-parts'

export const garageSwitchboard: Point = [.36, 1.5, -3]

export const serviceRooms = [
  { name: 'Garage', floor: 0, x: 1.8, z: -3.2, socketX: .3 },
  { name: 'Entry', floor: 0, x: 5.2, z: -3.0, socketX: 6.65 },
  { name: 'Stair hall', floor: 0, x: 4.0, z: -6.0, socketX: 4.45 },
  { name: 'Powder', floor: 0, x: 5.65, z: -7.6, socketX: 4.6 },
  { name: 'Kitchen', floor: 0, x: 1.8, z: -9.65, socketX: .3 },
  { name: 'Living dining', floor: 0, x: 2.4, z: -12.3, socketX: .3 },
  { name: 'Bedroom 3', floor: 1, x: 2.3, z: -3.2, socketX: .3 },
  { name: 'Bedroom 4', floor: 1, x: 2.3, z: -12.3, socketX: .3 },
  { name: 'Bathroom', floor: 1, x: 5.65, z: -8.0, socketX: 4.6 },
  { name: 'Laundry', floor: 1, x: 5.6, z: -12.5, socketX: 6.65 },
  { name: 'Landing', floor: 1, x: 4.1, z: -6.0, socketX: 4.45 },
  { name: 'Bedroom 2', floor: 2, x: 2.3, z: -3.2, socketX: .3 },
  { name: 'Master bedroom', floor: 2, x: 2.3, z: -12.3, socketX: .3 },
  { name: 'Ensuite', floor: 2, x: 5.65, z: -8.0, socketX: 4.6 },
  { name: 'Dressing', floor: 2, x: 5.6, z: -12.0, socketX: 6.65 },
  { name: 'Upper landing', floor: 2, x: 4.1, z: -6.0, socketX: 4.45 },
]

export function dwellingPoint(house: number, point: Point): Point {
  return [(house - 1) * 7 + (house % 2 === 0 ? 7 - point[0] : point[0]), point[1], point[2]]
}

function correctSource(model: THREE.Group) {
  model.updateMatrixWorld(true)
  const additions: THREE.Mesh[] = []
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    if (object.userData.sw_life === 'parked-car') object.userData.sw_contextOnly = true
    const material = object.material as THREE.MeshStandardMaterial
    const records = data.actions.filter(r => r.house === object.userData.sw_dwelling && r.system === object.userData.sw_system && r.material === material.name)
    if (!records.length) return
    const bounds = records.map(r => new THREE.Box3(new THREE.Vector3(...r.minimum), new THREE.Vector3(...r.maximum)).expandByScalar(.003))
    const position = object.geometry.getAttribute('position'), index = object.geometry.index
    const retained: number[] = [], selected = records.map(() => [] as number[])
    const vertices = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()]
    for (let i = 0; i < (index?.count ?? position.count); i += 3) {
      const ids = [0, 1, 2].map(j => index ? index.getX(i + j) : i + j)
      ids.forEach((id, j) => vertices[j].fromBufferAttribute(position, id).applyMatrix4(object.matrixWorld))
      const match = bounds.findIndex(b => vertices.every(v => b.containsPoint(v)))
      if (match < 0) retained.push(...ids)
      else if (records[match].action !== 'remove') selected[match].push(...ids)
    }
    selected.forEach((ids, i) => {
      if (!ids.length) return
      const copy = object.clone()
      copy.geometry = object.geometry.clone(); copy.geometry.setIndex(ids)
      copy.material = material.clone()
      copy.name = records[i].name
      copy.userData = { ...object.userData, sw_system: records[i].memberships[0], sw_service_systems: JSON.stringify(records[i].memberships), sw_contextOnly: records[i].action === 'context' }
      additions.push(copy)
    })
    object.geometry.setIndex(retained)
  })
  additions.forEach(mesh => model.add(mesh))
}

/** Direct ceiling runs with a slight relaxed curve, then a local drop to the fitting. */
function cable(model: THREE.Group, points: Point[], house: number) {
  const a = new THREE.Vector3(...points[0]), b = new THREE.Vector3(...points.at(-1)!)
  const height = Math.max(a.y, b.y + .16)
  const curve = new THREE.CatmullRomCurve3([
    a, new THREE.Vector3(a.x * .55 + b.x * .45, height - .06, a.z * .55 + b.z * .45 + .10),
    new THREE.Vector3(b.x, height, b.z), b,
  ])
  const mesh = part(model, new THREE.TubeGeometry(curve, 24, .009, 6, false), 'electrical', house)
  mesh.name = 'Direct relaxed electrical cable'
}

export function addBuildingServices(model: THREE.Group) {
  correctSource(model)
  for (let house = 1; house <= 7; house++) {
    const point = (p: Point) => dwellingPoint(house, p)
    const run = (points: Point[], radius: number, system: string) => pipe(model, points.map(p => point(p as Point)), radius, system, house)
    const meter: Point = [.36, 1.5, -2]
    box(model, [.18, .9, .39], point(meter), 'electrical', house).name = 'Garage meter cabinet'
    box(model, [.15, .65, .5], point(garageSwitchboard), 'electrical', house).name = 'Garage switchboard'
    run([[.36, -.45, 4.65], [.36, -.45, -2], meter], .018, 'electrical').name = 'Street supply to garage meter'
    run([meter, garageSwitchboard], .018, 'electrical').name = 'Garage meter to switchboard'
    run([garageSwitchboard, [.36, 3.15, -3], [.36, 3.15, -6.62], [3.94, 3.15, -6.62], [3.94, 9.3, -6.62]], .027, 'electrical').name = 'Garage switchboard to overhead electrical riser'
    for (const room of serviceRooms) {
      const ceiling = 2.95 + room.floor * 3.1, floor = .35 + room.floor * 3.1
      const light: Point = [room.x, ceiling, room.z]
      const lamp = part(model, new THREE.CylinderGeometry(.075, .075, .035, 12), 'electrical', house)
      lamp.position.set(...point(light)); lamp.name = `${room.name} light`
      const socket: Point = [room.socketX, floor + (/Kitchen|Powder|Bathroom|Ensuite|Laundry/.test(room.name) ? .95 : .3), room.z]
      box(model, [.035, .085, .14], point(socket), 'electrical', house).name = `${room.name} double GPO`
      cable(model, [[3.94, Math.min(9.28, ceiling + .20), -6.62], light].map(p => point(p as Point)), house)
      cable(model, [[3.94, Math.min(9.28, ceiling + .23), -6.62], socket].map(p => point(p as Point)), house)
    }
    for (const anchor of data.anchors) {
      const p = anchor.point as Point
      const floor = Math.max(0, Math.min(2, Math.floor((p[1] - .35) / 3.1)))
      cable(model, [[3.94, Math.min(9.28, 3.15 + floor * 3.1), -6.62], p].map(p => point(p as Point)), house)
    }
    // Outdoor plant is fed separately, rather than appearing as unexplained disconnected boxes.
    for (const p of [[5.4, .7, -15], [6.35, .7, -15]] as Point[]) cable(model, [[3.94, 3.15, -6.62], p].map(p => point(p as Point)), house)
    for (const route of data.routes) {
      const points = route.points.map(p => new THREE.Vector3(...point(p as Point)))
      const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal')
      const duct = part(model, new THREE.TubeGeometry(curve, 40, .1, 10, false), 'mechanical', house)
      duct.name = route.name.startsWith('Supply') ? '200 mm flexible supply duct' : '200 mm range hood exhaust to rear'
      if (route.name.startsWith('Dedicated')) box(model, [.3, .3, .08], point([.6, 2.95, -14.65]), 'mechanical', house)
    }
    for (const wet of [{ floor: 0, z: -8.1 }, { floor: 1, z: -8.1 }, { floor: 2, z: -8.1 }, { floor: 1, z: -12.5 }]) {
      const y = 2.95 + wet.floor * 3.1
      if (wet.z < -10) box(model, [.25, .035, .25], point([5.65, y, wet.z]), 'mechanical', house)
      run([[5.65, y, wet.z], [6.55, y + .15, wet.z], [6.55, y + .15, -15.45], [7.08, y + .15, -15.45]], .1, 'mechanical').name = 'Wet area extract to side-facing rear outlet'
      box(model, [.07, .28, .28], point([7.08, y + .15, -15.45]), 'mechanical', house)
    }
    run([[6.84, 6.6, 0], [6.84, .25, 0], [6.84, -.45, 0], [6.84, -.6, 3.4]], .045, 'civil').name = 'Front downpipe to pit'
    run([[6.84, 6.6, -14.4], [6.84, .25, -14.4], [6.84, -.45, -14.4]], .045, 'civil').name = 'Rear downpipe to rear pit'
    run([[3.7, -.6, 3.4], [6.84, -.6, 3.4]], .045, 'civil').name = 'Balcony drain to detention inlet pit'
    const fan = new THREE.Group()
    fan.position.set(...point([5.375, .65, -15.245])); fan.userData.sw_condenserFan = true
    const hub = part(fan, new THREE.SphereGeometry(.045, 10, 6), 'mechanical', house)
    hub.scale.z = .5
    for (let i = 0; i < 5; i++) {
      const blade = box(fan, [.07, .20, .018], [0, .12, 0], 'mechanical', house)
      const angle = i * Math.PI * 2 / 5
      blade.position.set(Math.sin(angle) * .12, Math.cos(angle) * .12, 0)
      blade.rotation.z = -angle + .4
    }
    model.add(fan)
    for (const base of [.35, 3.45, 6.55]) {
      const basin: Point = [5.04, base + .87, -7.32]
      const wc: Point = [6.04, base + .55, -7.12]
      for (const [p, hot] of [[basin, true], [wc, false]] as [Point, boolean][]) {
        run([[4.75, base - .1, -7.12], [p[0], base - .1, p[2]], p], .012, 'hydraulic')
        if (hot) run([[4.84, base - .1, -7.12], [p[0] + .07, base - .1, p[2]], [p[0] + .07, p[1], p[2]]], .012, 'hydraulic')
        run([p, [p[0], base - .13, p[2]], [4.98, base - .16, -7.12]], hot ? .025 : .055, 'hydraulic')
      }
      const waste: Point = [5.45, base + .015, -8.0]
      box(model, [.13, .02, .13], point(waste), 'hydraulic', house).name = 'Wet area floor waste'
      run([waste, [5.45, base - .12, -8.0], [4.98, base - .16, -7.12]], .025, 'hydraulic')
      if (base > 1) {
        for (const x of [4.75, 4.84]) run([[x, base - .1, -7.12], [6.25, base - .1, -8.97], [6.25, base + 1, -8.97]], .012, 'hydraulic')
        run([[6.15, base + .025, -8.7], [6.15, base - .13, -8.7], [4.98, base - .16, -7.12]], .025, 'hydraulic')
      }
    }
    box(model, [.13, .02, .13], point([5.5, 3.47, -12.4]), 'hydraulic', house).name = 'Laundry floor waste'
    run([[5.5, 3.47, -12.4], [5.5, 3.30, -12.4], [4.98, 3.29, -7.12]], .025, 'hydraulic')
    run([[4.75, 3.35, -7.12], [5.8, 3.35, -13.8], [5.8, 4.0, -13.8]], .012, 'hydraulic')
    run([[5.8, 4.0, -13.8], [5.8, 3.3, -13.8], [4.98, 3.29, -7.12]], .025, 'hydraulic')
    box(model, [7, 1.78, .10], [(house - 1) * 7 + 3.5, .94, -20.4], 'landscape', house).name = 'Rear garden fence'
  }
}
