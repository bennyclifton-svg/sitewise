import * as THREE from 'three'
import { detachedLayout as layout } from './detached-layout'

export function openDetachedGarage(home: THREE.Group) {
  const door = new THREE.Group()
  door.name = 'House two raised garage door'
  door.position.set(6.355, layout.garage + 2.4, -1.24)
  home.add(door)
  for (const child of [...home.children]) {
    if (child.name === 'Garage frontage door' || child.name === 'Garage vertical timber slat') door.attach(child)
  }
  door.rotation.x = Math.PI / 2
}

export function addDetachedGarageCar(home: THREE.Group, source: THREE.Group) {
  const car = source.clone(true)
  car.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    object.geometry = object.geometry.clone()
    object.material = Array.isArray(object.material) ? object.material.map(material => material.clone()) : object.material.clone()
    object.userData = { sw_system: 'interiors', sw_dwelling: 2 }
  })
  const bounds = new THREE.Box3().setFromObject(car), size = bounds.getSize(new THREE.Vector3())
  car.position.sub(bounds.getCenter(new THREE.Vector3()))
  const parked = new THREE.Group()
  parked.name = 'House two car facing the street'
  parked.add(car)
  const scale = 4.45 / size.x
  parked.scale.setScalar(scale)
  // Source nose is -X; +90 degrees turns it toward the street (+Z).
  parked.rotation.y = Math.PI / 2
  parked.position.set(5.15, layout.garage + size.y * scale / 2, -3.95)
  home.add(parked)
}
