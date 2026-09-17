import { expect, it } from 'vitest'
import * as THREE from 'three'
import { addBuildingServices } from './terrace-services'
import { addTelecomAndSolar } from './terrace-energy'
import data from './terrace-services-data.json'

it('keeps electrical equipment inside the garage and cables clear of every front entrance', () => {
  const model = new THREE.Group()
  addBuildingServices(model)
  addTelecomAndSolar(model)
  model.updateMatrixWorld(true)
  for (let house = 1; house <= 7; house++) {
    // Measured entrance and garage bounds, including the sidelight and entrance approach.
    const entrance = new THREE.Box3(new THREE.Vector3(4.28, .35, -1.5), new THREE.Vector3(5.7, 2.75, 0))
    const garage = new THREE.Box3(new THREE.Vector3(.25, .35, -6.5), new THREE.Vector3(3.78, 2.97, -.83))
    const equipment: string[] = []
    model.traverse(object => {
      if (!(object instanceof THREE.Mesh) || object.userData.sw_dwelling !== house || object.userData.sw_system !== 'electrical') return
      const mounted = /^Garage (meter cabinet|switchboard|solar inverter|NBN termination)$/.test(object.name)
      if (mounted) equipment.push(object.name)
      const positions = object.geometry.getAttribute('position')
      for (let i = 0; i < positions.count; i++) {
        const world = new THREE.Vector3().fromBufferAttribute(positions, i).applyMatrix4(object.matrixWorld)
        const local = new THREE.Vector3(world.x - (house - 1) * 7, world.y, world.z)
        if (house % 2 === 0) local.x = 7 - local.x
        expect(entrance.containsPoint(local), `${house}: ${object.name} crosses entry`).toBe(false)
        if (mounted) expect(garage.containsPoint(local), `${house}: ${object.name} outside garage`).toBe(true)
      }
    })
    expect(equipment.sort()).toEqual(['Garage NBN termination', 'Garage meter cabinet', 'Garage solar inverter', 'Garage switchboard'])
    expect(data.actions.filter(item => item.house === house && / \| (Meter cabinet|Distribution board|Electrical riser)$/.test(item.name)).map(item => item.action)).toEqual(['remove', 'remove', 'remove'])
  }
  model.traverse(object => {
    if (object instanceof THREE.Mesh) {
      object.geometry.dispose()
      if (!Array.isArray(object.material)) object.material.dispose()
    }
  })
})
