import { timberRun, roofProfile } from './detached-roof-details'
import * as THREE from 'three'
import { box, part, pipe, type Point } from './terrace-parts'
import { detachedLayout as layout, detachedFacades, detachedRooms } from './detached-layout'
import { addDetachedFrontRoof } from './detached-front-roof'
import { addDetachedFacadeDetails } from './detached-facade-details'
import { addDetachedWindowFurnishings } from './detached-window-furnishings'
import { refineDetachedWeatherboards } from './detached-weatherboards'
import { openDetachedGarage } from './detached-garage'
import { openDetachedBalcony } from './detached-balcony'
import { articulatedRoof } from './detached-tile-relief'

type Opening = { start: number; end: number; sill: number; head: number; door?: boolean }

export function createDetachedHouse(house: number) {
  const model = new THREE.Group()
  model.name = `Detached house ${house}`
  const variant = detachedFacades[house - 1]
  const cuboid = (name: string, size: Point, at: Point, system = 'architecture', brick = false) => {
    const mesh = box(model, size, at, system, house)
    mesh.name = name
    ;(mesh.material as THREE.Material).name = brick ? 'Warm brick 1' : 'White study model'
    return mesh
  }
  const line = (name: string, points: Point[], radius: number, system = 'structure') => {
    const mesh = pipe(model, points, radius, system, house); mesh.name = name; return mesh
  }
  // Walls are split at openings so the cutaway has framed voids, not painted-on windows.
  const wall = (name: string, a: Point, b: Point, height: number, openings: Opening[] = [], interior = false) => {
    const alongX = a[2] === b[2], length = Math.abs(alongX ? b[0] - a[0] : b[2] - a[2])
    const at = (distance: number, y: number): Point => alongX ? [a[0] + distance, a[1] + y, a[2]] : [a[0], a[1] + y, a[2] - distance]
    const slab = (start: number, end: number, bottom: number, top: number) => {
      if (end <= start || top <= bottom) return
      if (house === layout.cutaway) return
      // House two is mirrored: local x=8 is the suspended garage-side return.
      const garageReturn = house === 2 && name === 'Upper side' && a[0] === 8
      const garageEnd = 6.86 - .96
      if (garageReturn && start < garageEnd && end > garageEnd) {
        slab(start, garageEnd, bottom, top)
        slab(garageEnd, end, bottom, top)
        return
      }
      if (!interior && a[1] < 1 && bottom === 0) bottom = -a[1]
      const front = name.startsWith('Front') || name === 'Garage frontage'
      const cladding = name === 'Upper front' ? variant.finish === 'cladding' : house === 2 ? garageReturn && end <= garageEnd : name.startsWith('Upper') && !(name === 'Upper side' && a[0] === 0)
      const brickTop = house === 2 && !interior && !cladding ? height : !interior && a[1] < 1 ? (front ? variant.brickBase : house === 4 ? .9 : .65) : 0
      const cuts = [bottom, ...(brickTop > bottom && brickTop < top ? [brickTop] : []), top]
      for (let i = 1; i < cuts.length; i++) {
        const low = cuts[i - 1], high = cuts[i]
        const size: Point = alongX ? [end - start, high - low, interior ? .09 : .24] : [interior ? .09 : .24, high - low, end - start]
        const brick = high <= brickTop
        const mesh = cuboid(`${name} ${brick ? 'face brickwork' : 'wall finish'}`, size, at((start + end) / 2, (low + high) / 2), 'architecture', brick)
        if (!brick && !interior) (mesh.material as THREE.Material).name = cladding ? 'Detached horizontal cladding' : 'Detached render'
      }
      if (brickTop > bottom && brickTop < top) {
        const trim = cuboid(`${name} brick corbel`, alongX ? [end - start, .045, .28] : [.28, .045, end - start], at((start + end) / 2, brickTop - .0225), 'architecture', true)
        trim.userData.sw_detail = 'corbel'
      }
    }
    let cursor = 0
    for (const opening of [...openings, { start: length, end: length, sill: 0, head: height }]) {
      slab(cursor, opening.start, 0, height)
      slab(opening.start, opening.end, 0, opening.sill)
      slab(opening.start, opening.end, opening.head, height)
      cursor = opening.end
    }
    for (let d = 0; d <= length; d += .45) {
      const opening = openings.find(o => d > o.start && d < o.end)
      if (!opening) cuboid(`${name} timber stud`, alongX ? [.038, height, .09] : [.09, height, .038], at(d, height / 2), 'structure')
      else {
        if (opening.sill > 0) cuboid(`${name} sill stud`, alongX ? [.038, opening.sill, .09] : [.09, opening.sill, .038], at(d, opening.sill / 2), 'structure')
        cuboid(`${name} header stud`, alongX ? [.038, height - opening.head, .09] : [.09, height - opening.head, .038], at(d, (height + opening.head) / 2), 'structure')
      }
    }
    for (const y of [.025, height - .025]) line(`${name} wall plate`, [at(0, y), at(length, y)], .025)
    for (const o of openings) {
      line(`${name} opening lintel`, [at(o.start, o.head), at(o.end, o.head)], .045)
      if (o.door && house === layout.cutaway) continue
      const width = o.end - o.start, h = o.head - o.sill
      const glazedEntry = house === 2 && o.door && name === 'Front multi room and entry'
      const glass = cuboid(`${name} ${o.door ? 'door' : 'glazing'}`, alongX ? [width, h, .025] : [.025, h, width], at((o.start + o.end) / 2, (o.sill + o.head) / 2))
      if (glazedEntry) {
        glass.scale.set(.8, .85, 1); glass.userData.sw_glass = true; (glass.material as THREE.Material).name = 'Glazing'
        for (const d of [o.start + width * .05, o.end - width * .05]) cuboid('Entry door solid stile', [width * .1, h, .04], at(d, h / 2))
        for (const y of [h * .0375, h * .9625]) cuboid('Entry door solid rail', [width * .8, h * .075, .04], at((o.start + o.end) / 2, y))
        for (let pane = 1; pane < 5; pane++) cuboid('Entry five-pane glazing bar', [.018, h * .85, .04], at(o.start + width * (.1 + .8 * pane / 5), h / 2))
      }
      if (!o.door) { glass.userData.sw_glass = true; (glass.material as THREE.Material).name = 'Glazing' }
      for (const d of [o.start, o.end, ...(!o.door && width > 1.1 ? [(o.start + o.end) / 2] : [])]) line(`${name} window jamb`, [at(d, o.sill), at(d, o.head)], .022, 'architecture')
      for (const y of [o.sill, o.head]) line(`${name} window frame`, [at(o.start, y), at(o.end, y)], .022, 'architecture')
      if (!o.door && width < 1 && h > 1.2) {
        const transom = house === 2 && name === 'Upper front' ? (o.head + o.sill) / 2 : o.head - .38
        line(`${name} awning transom`, [at(o.start, transom), at(o.end, transom)], .017, 'architecture')
      }
      if (!o.door && name === 'Front multi room and entry') cuboid('Front window horizontal transom', [width, .035, .045], at((o.start + o.end) / 2, (o.sill + o.head) / 2))
    }
  }
  const gf = layout.ground, ff = layout.upper
  cuboid('Ground left-wing slab', [3.35, .18, 12.23], [1.675, gf - .09, -7.235], 'structure')
  cuboid('Ground rear-wing slab', [5.88, .18, 6.49], [6.29, gf - .09, -10.105], 'structure')
  cuboid('Family slab extension', [4.31, .18, 2.37], [5.635, gf - .09, -14.535], 'structure')
  cuboid('Garage slab 86 mm setdown', [5.64, .16, 5.5], [6.17, layout.garage - .08, -4.11], 'structure')
  // A real stairwell remains open through the upper floor.
  for (const [x, z, w, d] of [[4.0, 3.435, 8.0, 4.95], [5.4, 6.405, 5.2, .99], [4.0, 9.805, 8.0, 5.81], [.25, 6.4, .5, 1.0]]) {
    cuboid('First-floor deck around stairwell', [w, .10, d], [x, ff - .10, -z], 'structure')
  }
  for (let d = 1.1; d < 12.7; d += .45) {
    const stair = d > 5.9 && d < 6.9
    cuboid('Timber floor joist', [stair ? 5.2 : 8, .22, .045], [stair ? 5.4 : 4, ff - .22, -d], 'structure')
  }
  for (const x of [.12, 3.47, 9.11]) {
    cuboid('Concrete edge beam', [.4, .5, 13], [x, -.15, -7.85], 'structure')
    for (const d of [1.4, 7.8, 14.1]) {
      const pier = part(model, new THREE.CylinderGeometry(.15, .15, 2.2, 10), 'structure', house)
      pier.position.set(x, -1.1, -d); pier.name = 'Foundation pier'
    }
  }
  wall('Front multi room and entry', [0, gf, -1.12], [3.47, gf, -1.12], 2.75, [{ start: .38, end: 1.5, sill: .75, head: 2.2 }, { start: 2.02, end: 2.94, sill: 0, head: 2.4, door: true }])
  wall('Garage frontage', [3.47, layout.garage, -1.24], [9.23, layout.garage, -1.24], 2.84, [{ start: .47, end: 5.28, sill: 0, head: 2.4, door: true }])
  wall('Left elevation', [0, gf, -1.12], [0, gf, -13.2], 2.75, [{ start: 1.2, end: 3.61, sill: 1.15, head: 1.75 }, { start: 6.3, end: 7.15, sill: 1.2, head: 2.4 }, { start: 8.7, end: 11.35, sill: .6, head: 2.4 }])
  wall('Right elevation', [9.23, gf, -1.24], [9.23, gf, -11.4], 2.75, [{ start: 7.1, end: 8.3, sill: 1.35, head: 2.4 }])
  wall('Rear family elevation', [3.47, gf, -15.72], [7.8, gf, -15.72], 2.75, [{ start: .4, end: 1.2, sill: .65, head: 2.4 }, { start: 1.55, end: 4, sill: .15, head: 2.4 }])
  wall('Family side', [7.8, gf, -11.4], [7.8, gf, -15.72], 2.75, [{ start: 1.1, end: 2.91, sill: .6, head: 2.4 }])
  wall('Alfresco sliding door', [3.47, gf, -12.75], [3.47, gf, -15.72], 2.75, [{ start: .2, end: 2.61, sill: .05, head: 2.4 }])
  const frontWindows = variant.windows === 2 ? [4.5, 6.3] : [4.3, 5.65, 7]
  wall('Upper front', [0, ff, -.96], [8, ff, -.96], 2.45, [{ start: .32, end: 2.72, sill: .02, head: 2.12 }, ...frontWindows.map(start => ({ start, end: start + (variant.windows === 2 ? .85 : .6), sill: .6, head: 2.12 }))])
  wall('Upper rear', [0, ff, -12.71], [8, ff, -12.71], 2.45, [{ start: 4.8, end: 6.61, sill: 1.1, head: 2.12 }])
  for (const x of [0, 8]) wall('Upper side', [x, ff, -.96], [x, ff, -12.71], 2.45, [{ start: 4.5, end: 5.35, sill: 1.1, head: 2.12 }, { start: 7.6, end: 8.45, sill: 1.1, head: 2.12 }, { start: 9.6, end: 11.1, sill: 1.1, head: 2.12 }])
  // Finish bands follow the split wall geometry, so they cannot bridge openings.
  if (house !== layout.cutaway) {
    for (const [size, at] of [
      [[8.24, .32, .24], [4, ff - .16, -.96]],
      [[8.24, .32, .24], [4, ff - .16, -12.71]],
      [[.24, .32, 11.75], [0, ff - .16, -6.835]],
      ... (house === 2 ? [
        [[.24, .32, 5.9], [8, ff - .16, -3.91]],
        [[.24, .32, 5.85], [8, ff - .16, -9.785]],
      ] : [[[.24, .32, 11.75], [8, ff - .16, -6.835]]]),
    ] as [Point, Point][]) {
      const mesh = cuboid('Floor-edge rendered enclosure', size, at)
      ;(mesh.material as THREE.Material).name = house === 2 && (at[2] === -.96 || (at[0] === 8 && at[2] === -3.91)) ? 'Detached horizontal cladding' : 'Detached render'
    }
    cuboid('Entrance door pull', [.025, .32, .05], [2.83, gf + 1.05, -1.065])
  }
  cuboid('Front porch', [3.59, .13, 1], [1.795, layout.garage - .065, -.5], 'structure')
  cuboid('Front balcony', [3.59, .14, .96], [1.795, ff - .07, -.48], 'structure')
  for (const x of [.14, 3.45]) {
    const pierTop = house === 1 ? ff + 1.02 : house === 4 ? layout.ceiling : layout.garage + variant.brickBase
    if (house !== 1 && house !== 4) cuboid('Porch timber post', [.135, ff - .65 - layout.garage, .135], [x, (ff - .65 + layout.garage) / 2, -.12], 'structure')
    const postBase = house === 1 ? pierTop : ff
    if (house !== 4) cuboid('Balcony timber post', [.135, layout.ceiling - postBase, .135], [x, (postBase + layout.ceiling) / 2, house === 1 ? 0 : -.12], 'structure')
    if (house !== layout.cutaway) {
      const pier = cuboid('Porch brick pier base', [.34, pierTop, .34], [x, pierTop / 2, house === 1 || house === 4 ? 0 : -.12], 'architecture', true)
      if (house === 4) (pier.material as THREE.Material).name = 'Detached stone cladding'
    }
  }
  for (let x = .2; x < 3.5; x += variant.railSpacing) cuboid('Balcony baluster', [variant.railWidth, .96, .025], [x, ff + .53, -.07])
  for (const y of [ff + .05, ff + 1.02]) line('Balcony handrail', [[.14, y, -.07], [3.45, y, -.07]], .024, 'architecture')
  for (const x of [.14, 3.45]) {
    for (let d = .18; d < .92; d += variant.railSpacing) cuboid('Balcony side baluster', [.025, .96, variant.railWidth], [x, ff + .53, -d])
    for (const y of [ff + .05, ff + 1.02]) line('Balcony side handrail', [[x, y, -.07], [x, y, -.96]], .024, 'architecture')
  }
  if (house !== layout.cutaway) {
    for (const [size, at] of [
      [[3.75, .65, .12], [1.795, ff - .325, .025]],
      [[.12, .65, 1.12], [-.065, ff - .325, -.475]],
      [[.12, .65, 1.12], [3.655, ff - .325, -.475]],
    ] as [Point, Point][]) {
      const fascia = cuboid('Balcony rendered feature fascia', size, at)
      ;(fascia.material as THREE.Material).name = 'Detached render'
    }
    for (const y of [ff - .055, ff - .595]) {
      cuboid('Balcony brick corbel', [3.81, .11, .23], [1.795, y, .055], 'architecture', true)
      for (const x of [-.065, 3.655]) cuboid('Balcony side brick corbel', [.23, .11, 1.12], [x, y, -.475], 'architecture', true)
    }
    cuboid('Balcony soffit', [3.59, .045, 1.1], [1.795, ff - .63, -.46])
  }
  for (let i = 0; i < variant.entryFins; i++) cuboid('Entrance feature batten', [.04, 2.5, .06], [3.1 + i * .1, gf + 1.25, -.95])
  cuboid('Alfresco paving', [3.59, .12, 2.97], [1.795, gf - .172 - .06, -14.235], 'structure')
  for (const x of [.15, 3.44]) cuboid('Alfresco timber post', [.135, 2.75, .135], [x, gf + 1.2, -15.58], 'structure')
  // Winder stair, furniture and equipment are shared across all facade variants.
  for (let i = 0; i < 17; i++) {
    const first = i < 8, step = first ? i : 16 - i
    cuboid('Stair timber tread', [.88, .045, .26], [first ? .75 : 1.78, gf + (i + 1) * (ff - gf) / 17, -5.0 - step * .26], 'interiors')
  }
  cuboid('Stair half landing', [1.94, .10, .85], [1.26, gf + 8 * (ff - gf) / 17, -7.12], 'interiors')
  line('Stair handrail', [[.28, gf + .95, -5], [.28, gf + 2.4, -7], [2.24, gf + 2.4, -7], [2.24, ff + .95, -5]], .024, 'interiors')
  for (const room of detachedRooms) {
    const base = room.floor ? ff : gf, cx = room.x + room.width / 2, d = room.depth + room.length / 2
    if (room.name !== 'Garage' && room.name !== 'Stairs') {
      cuboid(`${room.name} floor finish`, [room.width, .025, room.length], [cx, base + .014, -d], 'interiors')
      const lamp = part(model, new THREE.CylinderGeometry(.09, .09, .03, 12), 'electrical', house)
      lamp.position.set(cx, base + (room.floor ? 2.4 : 2.68), -d); lamp.name = `${room.name} downlight`
    }
    if (room.name.startsWith('Bed ')) {
      cuboid(`${room.name} bed base`, [1.5, .3, 2.05], [cx, base + .2, -d], 'interiors')
      cuboid(`${room.name} mattress`, [1.48, .18, 2], [cx, base + .43, -d], 'interiors')
      cuboid(`${room.name} headboard`, [1.6, 1, .07], [cx, base + .52, -d - 1], 'interiors')
      for (const offset of [-.4, .4]) cuboid(`${room.name} pillow`, [.55, .12, .38], [cx + offset, base + .56, -d - .65], 'interiors')
      cuboid(`${room.name} wardrobe`, [.6, 2.1, 1.5], [room.x + .3, base + 1.05, -room.depth - .8], 'interiors')
    }
    if (['Family', 'Multi', 'Sitting'].includes(room.name)) {
      cuboid(`${room.name} sofa`, [2.1, .45, .85], [cx, base + .3, -d], 'interiors')
      cuboid(`${room.name} sofa back`, [2.1, .42, .16], [cx, base + .7, -d - .36], 'interiors')
      cuboid(`${room.name} coffee table`, [1.0, .07, .55], [cx, base + .4, -d + 1], 'interiors')
    }
    if (room.wet) {
      cuboid(`${room.name} vanity`, [.55, .75, .85], [room.x + .35, base + .4, -d], 'interiors')
      cuboid(`${room.name} basin`, [.5, .08, .6], [room.x + .35, base + .83, -d], 'hydraulic')
      line(`${room.name} mixer`, [[room.x + .35, base + .85, -d - .24], [room.x + .35, base + 1.02, -d - .24], [room.x + .35, base + 1.02, -d]], .012, 'hydraulic')
      cuboid(`${room.name} WC cistern`, [.4, .55, .18], [room.x + room.width - .35, base + .6, -d - .4], 'interiors')
      const wc = part(model, new THREE.SphereGeometry(.24, 12, 8), 'interiors', house)
      wc.scale.set(.8, .6, 1.2); wc.position.set(room.x + room.width - .35, base + .4, -d); wc.name = `${room.name} WC pan`
      if (room.floor) {
        cuboid(`${room.name} shower tray`, [.9, .04, .9], [cx, base + .02, -room.depth - .5], 'interiors')
        line(`${room.name} shower rail`, [[cx, base + .8, -room.depth - .08], [cx, base + 2, -room.depth - .08], [cx, base + 2, -room.depth - .3]], .014, 'hydraulic')
      }
    }
  }
  cuboid('Kitchen island', [.9, .88, 2.1], [4.2, gf + .44, -10.4], 'interiors')
  cuboid('Island benchtop', [1.0, .04, 2.2], [4.2, gf + .9, -10.4], 'interiors')
  cuboid('Kitchen cabinetry', [.62, .88, 3.4], [6.74, gf + .44, -10.1], 'interiors')
  cuboid('Induction cooktop', [.57, .035, .8], [6.74, gf + .9, -10], 'electrical')
  cuboid('Rangehood', [.6, .3, .8], [6.74, gf + 2, -10], 'mechanical')
  cuboid('Refrigerator', [.75, 1.85, .75], [8.5, gf + .925, -9.1], 'interiors')
  cuboid('Dining table', [1.0, .08, 1.8], [1.8, gf + .75, -11], 'interiors')
  for (const x of [1.05, 2.55]) for (const d of [10.5, 11.4]) {
    cuboid('Dining chair seat', [.42, .05, .42], [x, gf + .45, -d], 'interiors')
    cuboid('Dining chair back', [.42, .4, .05], [x, gf + .67, -d - .2], 'interiors')
  }
  // Compact room partitions expose studs in house three; omit its door leaves.
  wall('Garage separation', [3.35, gf, -1.36], [3.35, gf, -6.86], 2.75, [{ start: 4.4, end: 5.25, sill: 0, head: 2.04, door: true }], true)
  if (house === 2) wall('Garage internal rear wall', [3.35, layout.garage, -6.86], [9.11, layout.garage, -6.86], 2.84, [], true)
  for (const room of detachedRooms.filter(r => r.floor && r.name !== 'Sitting' && r.name !== 'Walk-in robe')) {
    wall(`${room.name} partition`, [room.x, ff, -room.depth - room.length], [room.x + room.width, ff, -room.depth - room.length], 2.45, [{ start: .15, end: 1, sill: 0, head: 2.04, door: true }], true)
  }
  addDetachedFrontRoof(model, house)
  addHipRoof(model, house, [-.45, 12.3, 8.25, 16.17], gf + 2.75, gf + 3.45, house !== layout.cutaway)
  // Section B: low 3-degree garage roof, behind the raised side parapet.
  const garageRoof = cuboid('Low pitched garage roof', [1.23, .10, 5.8], [8.615, gf + 3.85, -4.14], house === layout.cutaway ? 'structure' : 'architecture')
  garageRoof.rotation.x = THREE.MathUtils.degToRad(-3)
  for (const [size, at] of [
    [[.24, 1.365, 6.04], [9.23, gf + 3.4325, -4.14]],
    [[1.47, 1.365, .24], [8.615, gf + 3.4325, -1.24]],
  ] as [Point, Point][]) {
    if (house !== layout.cutaway) {
      const parapet = cuboid('Garage raised rendered parapet', size, at)
      ;(parapet.material as THREE.Material).name = 'Detached render'
    }
  }
  line('Garage parapet coping', [[7.94, gf + 4.14, -1.24], [9.23, gf + 4.14, -1.24], [9.23, gf + 4.14, -7.16]], .04, 'architecture')
  if (house === 2) model.traverse(object => {
    if (object instanceof THREE.Mesh && (object.material as THREE.Material).name === 'Detached render') (object.material as THREE.Material).name = 'Warm brick 1'
  })
  addDetachedFacadeDetails(model, house)
  refineDetachedWeatherboards(model, house)
  addDetachedWindowFurnishings(model, house)
  if (house === 2) openDetachedGarage(model)
  if (house === 2) openDetachedBalcony(model)
  return model
}

function addHipRoof(model: THREE.Group, house: number, bounds: number[], eave: number, ridge: number, envelope: boolean) {
  const [left, front, right, rear] = bounds, centre = (left + right) / 2, hip = (right - left) / 2
  const first = Math.min(front + hip, (front + rear) / 2), last = Math.max(rear - hip, (front + rear) / 2)
  const vertices = [[left, eave, -front], [right, eave, -front], [right, eave, -rear], [left, eave, -rear], [centre, ridge, -first], [centre, ridge, -last]]
  if (envelope) {
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices.flat(), 3))
    geometry.setIndex([0, 4, 1, 1, 4, 5, 1, 5, 2, 2, 5, 3, 3, 5, 4, 3, 4, 0]); geometry.computeVertexNormals()
    const surface = articulatedRoof(geometry)
    const mesh = part(model, surface, 'architecture', house); geometry.dispose()
    ;(mesh.material as THREE.Material).side = THREE.DoubleSide; mesh.name = 'Hipped tiled roof'
    ;(mesh.material as THREE.Material).name = 'Detached roof tiles'
    for (const [a, b] of [[0, 4], [1, 4], [2, 5], [3, 5], [4, 5]]) {
      if (new THREE.Vector3(...vertices[a]).distanceTo(new THREE.Vector3(...vertices[b])) > .001) roofProfile(model, [vertices[a] as Point, vertices[b] as Point], 'cap', house)
    }
    for (const [size, at] of [
      [[right - left, .18, .04], [(left + right) / 2, eave - .09, -front]],
      [[right - left, .18, .04], [(left + right) / 2, eave - .09, -rear]],
      [[.04, .18, rear - front], [left, eave - .09, -(front + rear) / 2]],
      [[.04, .18, rear - front], [right, eave - .09, -(front + rear) / 2]],
    ] as [Point, Point][]) box(model, size, at, 'architecture', house).name = 'Roof fascia'
    for (let t = .05; t < 1; t += .045) {
      const x0 = left + (centre - left) * t, x1 = right + (centre - right) * t
      const z0 = front + (first - front) * t, z1 = rear + (last - rear) * t, y = eave + (ridge - eave) * t + .012
      pipe(model, [[x0, y, -z0], [x1, y, -z0], [x1, y, -z1], [x0, y, -z1], [x0, y, -z0]], .009, 'architecture', house).name = 'Tile course'
    }
  }
  roofProfile(model, [[left, eave, -front], [right, eave, -front], [right, eave, -rear], [left, eave, -rear], [left, eave, -front]], 'gutter', house)
  if (envelope) box(model, [right - left, .04, rear - front], [centre, eave - .14, -(front + rear) / 2], 'architecture', house).name = 'Rear roof ceiling and soffit'
  for (let depth = front + .15; depth < rear; depth += .6) {
    const t = Math.min(1, (depth - front) / hip, (rear - depth) / hip), top = eave + (ridge - eave) * t
    // Keep the timber below the tile skin, avoiding protrusions and self-shadow stripes.
    timberRun(model, [[left, eave - .08, -depth], [centre, top - .08, -depth], [right, eave - .08, -depth], [left, eave - .08, -depth]], .07, .035, house)
    for (const x of [left + hip * .5, centre, right - hip * .5]) timberRun(model, [[x, eave - .08, -depth], [centre, top - .08, -depth]], .07, .035, house)
  }
}
