import * as THREE from 'three'
import { box, part, pipe, type Point } from './terrace-parts'
import { detachedLayout as layout, detachedRooms } from './detached-layout'

/** Schematic service routes; the architectural reference does not supply a coordinated MEP design. */
export function addDetachedServices(model: THREE.Group, house: number) {
  const cuboid = (name: string, size: Point, at: Point, system: string) => {
    const mesh = box(model, size, at, system, house); mesh.name = name; return mesh
  }
  const run = (name: string, points: Point[], radius: number, system: string) => {
    const mesh = pipe(model, points, radius, system, house); mesh.name = name; return mesh
  }
  const board: Point = [8.85, 1.7, -2.4]
  cuboid('Garage switchboard', [.16, .65, .5], board, 'electrical')
  cuboid('Garage inverter', [.18, .6, .4], [8.85, 1.6, -3.2], 'electrical')
  cuboid('Garage NBN terminal', [.12, .25, .2], [8.85, 1.6, -3.9], 'electrical')
  run('Underground electrical lead-in', [[8.85, -.5, 4.5], [8.85, -.5, -2.4], board], .025, 'electrical')
  run('Garage inverter connection', [[8.85, 1.6, -3.2], [8.85, 1.6, -2.4], board], .014, 'electrical')
  run('NBN underground lead-in', [[8.85, -.65, 4.2], [8.85, -.65, -3.9], [8.85, 1.6, -3.9]], .012, 'electrical')
  run('Garage board to ceiling and upper riser', [board, [8.85, 2.95, -2.4], [8.85, 2.95, -7.5], [4.1, 2.95, -7.5], [4.1, 5.78, -7.5]], .023, 'electrical')
  for (const room of detachedRooms.filter(room => room.name !== 'Stairs')) {
    const base = room.floor ? layout.upper : layout.ground
    const ceiling = room.floor ? layout.ceiling - .05 : layout.ground + 2.68
    const x = room.x + room.width / 2, d = room.depth + room.length / 2
    run(`${room.name} lighting circuit`, [[4.1, ceiling, -7.5], [x, ceiling, -7.5], [x, ceiling, -d]], .008, 'electrical')
    const socket: Point = [room.x + .04, base + .35, -d]
    cuboid(`${room.name} socket`, [.035, .09, .14], socket, 'electrical')
    run(`${room.name} socket circuit`, [[4.1, ceiling, -7.5], [socket[0], ceiling, -7.5], [socket[0], ceiling, socket[2]], socket], .008, 'electrical')
    if (!['Garage', 'Walk-in pantry', 'Walk-in robe'].includes(room.name)) {
      const vent = cuboid(`${room.name} ceiling grille`, [.28, .025, .28], [x + .6, ceiling - .035, -d], 'mechanical')
      vent.userData.sw_service_systems = JSON.stringify(['mechanical'])
      for (let i = 0; i < 5; i++) cuboid('Air grille louvre', [.23, .01, .012], [x + .6, ceiling - .055, -d - .1 + i * .05], 'mechanical')
      run(`${room.name} supply duct`, [[4.3, ceiling + .1, -7.5], [x + .6, ceiling + .1, -7.5], [x + .6, ceiling + .1, -d]], .085, 'mechanical')
    }
    if (room.wet || room.name === 'Kitchen') {
      const px = room.x + .35, y = base + .8
      for (const [offset, name] of [[0, 'Cold'], [.07, 'Hot']] as const) run(`${room.name} ${name} supply`, [[4.3 + offset, base - .12, -7.5], [px + offset, base - .12, -7.5], [px + offset, base - .12, -d], [px + offset, y, -d]], .012, 'hydraulic')
      run(`${room.name} sanitary branch`, [[px, y - .25, -d], [px, base - .15, -d], [4.55, base - .15, -d], [4.55, base - .15, -7.5]], .035, 'hydraulic')
      if (room.wet) run(`${room.name} extract`, [[x, ceiling + .05, -d], [8.1, ceiling + .05, -d]], .075, 'mechanical')
    }
  }
  for (const [x, radius, name] of [[4.3, .018, 'Cold water riser'], [4.37, .014, 'Hot water riser'], [4.55, .055, 'Sanitary stack']] as const) run(name, [[x, -.45, -7.5], [x, layout.ceiling + .15, -7.5]], radius, 'hydraulic')
  cuboid('Ducted AC indoor unit', [1.1, .45, .75], [4.3, 6.13, -7.5], 'mechanical')
  run('Main vertical AC duct', [[4.3, 6.13, -7.5], [4.3, 3.1, -7.5]], .15, 'mechanical')
  cuboid('Outdoor condenser', [.35, .85, .9], [9.65, .6, -11.2], 'mechanical')
  const fan = part(model, new THREE.CylinderGeometry(.25, .25, .04, 20), 'mechanical', house)
  fan.rotation.z = Math.PI / 2; fan.position.set(9.86, .65, -11.2); fan.name = 'Condenser fan grille'
  run('AC refrigerant lines', [[9.65, .7, -11.2], [9.65, 3.1, -11.2], [4.3, 3.1, -11.2], [4.3, 6.13, -7.5]], .018, 'mechanical')
  const tank = part(model, new THREE.CylinderGeometry(.24, .24, 1.45, 16), 'hydraulic', house)
  tank.position.set(9.7, .9, -10.1); tank.name = 'Hot water cylinder'
  run('Hot water plant connection', [[9.7, .8, -10.1], [9.7, -.1, -10.1], [4.37, -.1, -10.1], [4.37, -.1, -7.5]], .014, 'hydraulic')
  for (const [eaveX, wallX, d] of [[-.45, -.16, 1.45], [-.45, -.16, 11.8]]) {
    run('Wall-mounted downpipe with eave offset', [[eaveX, layout.ceiling, -d], [eaveX, layout.ceiling - .2, -d], [wallX, layout.ceiling - .55, -d], [wallX, -.6, -d]], .045, 'civil')
    cuboid('Stormwater pit', [.4, .35, .4], [wallX, -.13, -d], 'civil')
    cuboid('Pit grated lid', [.42, .025, .42], [wallX, .055, -d], 'civil')
  }
  run('Garage roof downpipe and spreader', [[8.45, layout.ceiling, -1.7], [8.45, layout.ceiling - .2, -1.7], [8.17, layout.ceiling - .5, -1.7], [8.17, 4.22, -1.7], [8.55, 4.22, -1.7]], .045, 'civil')
  run('Rear roof downpipe and spreader', [[8.45, layout.ceiling, -12.9], [8.45, layout.ceiling - .2, -12.9], [8.16, layout.ceiling - .5, -12.9], [8.16, 3.35, -12.9], [7.95, 3.35, -12.9]], .045, 'civil')
  run('Lower garage wall downpipe', [[9.34, 4.2, -6.9], [9.39, 3.9, -6.9], [9.39, -.6, -6.9]], .045, 'civil')
  run('Stormwater house connection', [[8.4, -.65, -12.7], [8.4, -.65, 4.8]], .075, 'civil')
  run('House sewer connection', [[4.55, -.7, -7.5], [9.85, -.7, -7.5], [9.85, -1.3, 4.8]], .055, 'hydraulic')
  run('Water lead-in', [[9.5, -.55, 4.6], [9.5, -.55, -7.5], [4.3, -.55, -7.5]], .018, 'hydraulic')
}
