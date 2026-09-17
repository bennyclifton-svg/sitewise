import * as THREE from 'three'
import { blinds, cutawayFinishes, openings, rearBlades } from './terrace-life-data'
import { cutawayDwelling } from './terrace-material'

const bounds = (item: { minimum: number[]; maximum: number[] }) => new THREE.Box3(
  new THREE.Vector3(...item.minimum), new THREE.Vector3(...item.maximum),
)

/** Remove only triangles inside measured source-object bounds, after web batching. */
export function removeClosedDoorTriangles(mesh: THREE.Mesh, boxes: THREE.Box3[]) {
  const geometry = mesh.geometry
  const positions = geometry.getAttribute('position')
  const index = geometry.getIndex()
  const kept: number[] = []
  const points = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()]
  for (let i = 0; i < (index?.count ?? positions.count); i += 3) {
    const triangle = [0, 1, 2].map(offset => index ? index.getX(i + offset) : i + offset)
    points.forEach((point, vertex) => point.fromBufferAttribute(positions, triangle[vertex]).applyMatrix4(mesh.matrixWorld))
    if (!boxes.some(box => points.every(point => box.containsPoint(point)))) kept.push(...triangle)
  }
  geometry.setIndex(kept)
  geometry.computeBoundingBox()
  geometry.computeBoundingSphere()
}

export function applyTerraceLife(model: THREE.Group, car: THREE.Group) {
  model.updateMatrixWorld(true)
  const finishes = cutawayFinishes.map(item => ({ ...item, box: bounds(item).expandByScalar(.003) }))
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh) || object.userData.sw_dwelling !== cutawayDwelling) return
    const material = object.material as THREE.MeshStandardMaterial
    const boxes = finishes.filter(item => item.house === cutawayDwelling && item.system === object.userData.sw_system && item.material === material.name).map(item => item.box)
    if (boxes.length) removeClosedDoorTriangles(object, boxes)
  })
  const doorBoxes = [...openings, ...rearBlades].map(item => ({ house: item.house, box: bounds(item).expandByScalar(.003) }))
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh) || object.userData.sw_system !== 'architecture') return
    const boxes = doorBoxes.filter(item => item.house === object.userData.sw_dwelling).map(item => item.box)
    if (boxes.length) removeClosedDoorTriangles(object, boxes)
  })

  for (const item of rearBlades) {
    const box = bounds(item)
    const centre = box.getCenter(new THREE.Vector3())
    const geometry = new THREE.BoxGeometry(...box.getSize(new THREE.Vector3()).toArray())
    geometry.translate(centre.x, centre.y, centre.z)
    const position = geometry.getAttribute('position')
    for (let i = 0; i < position.count; i++) {
      if (position.getY(i) > centre.y) position.setY(i, rearRoofHeight(-position.getZ(i)))
    }
    geometry.computeVertexNormals()
    const blade = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: '#FFFFFF', roughness: .6 }))
    blade.userData = { sw_system: 'architecture', sw_dwelling: 0, sw_colour: '#FFFFFF', sw_life: 'raked-rear-blade' }
    model.add(blade)
  }

  for (const house of [1, 3, 6]) {
    const items = openings.filter(item => item.house === house)
    const box = items.reduce((result, item) => result.union(bounds(item)), new THREE.Box3())
    const centre = box.getCenter(new THREE.Vector3())
    const garage = house !== 1
    if (house === 6) {
      for (let index = 0; index < 25; index++) {
        const slat = new THREE.Mesh(new THREE.BoxGeometry(box.max.x - box.min.x, .085, .055), new THREE.MeshStandardMaterial({ color: '#FFFFFF' }))
        slat.position.set(centre.x, .445 + index * .09, centre.z)
        slat.userData = { sw_system: 'architecture', sw_dwelling: house, sw_roller: { index, front: centre.z } }
        model.add(slat)
      }
      continue
    }
    const pivot = new THREE.Group()
    pivot.position.set(garage ? centre.x : box.min.x, garage ? box.max.y : box.min.y, centre.z)
    for (const item of items) {
      const partBox = bounds(item)
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(...partBox.getSize(new THREE.Vector3()).toArray()),
        new THREE.MeshStandardMaterial({ color: '#FFFFFF', roughness: .48 }))
      mesh.position.copy(partBox.getCenter(new THREE.Vector3()).sub(pivot.position))
      mesh.userData = { sw_system: 'architecture', sw_dwelling: house, sw_life: 'open-door' }
      pivot.add(mesh)
    }
    if (garage) pivot.rotation.x = house === 3 ? Math.PI / 2 : Math.PI / 3
    else pivot.rotation.y = THREE.MathUtils.degToRad(72)
    model.add(pivot)
  }

  for (const item of blinds) {
    if (!item.closed || (item.house === 7 && item.minimum[1] > 6)) continue
    const box = bounds(item)
    const size = box.getSize(new THREE.Vector3())
    const blind = new THREE.Mesh(new THREE.BoxGeometry(size.x, size.y * item.closed, .025),
      new THREE.MeshStandardMaterial({ color: '#FFFFFF', roughness: .8 }))
    blind.position.set((box.min.x + box.max.x) / 2, box.max.y - size.y * item.closed / 2, box.min.z - .06)
    blind.userData = { sw_system: 'interiors', sw_dwelling: item.house, sw_life: 'blind' }
    model.add(blind)
  }

  // The existing vehicle faces world -X. Turn its nose into the new garage (-Z).
  const carBox = new THREE.Box3().setFromObject(car)
  const carCentre = carBox.getCenter(new THREE.Vector3())
  const normalised = new THREE.Group()
  car.position.sub(carCentre)
  normalised.add(car)
  normalised.rotation.y = -Math.PI / 2
  const scale = 4.45 / carBox.getSize(new THREE.Vector3()).x
  normalised.scale.setScalar(scale)
  const garage = bounds(openings.find(item => item.house === 3)!)
  normalised.position.set(garage.getCenter(new THREE.Vector3()).x,
    .36 + carBox.getSize(new THREE.Vector3()).y * scale / 2, garage.getCenter(new THREE.Vector3()).z)
  model.add(normalised)
}

/** Continue the authored main roof slope from the ridge to the balcony edge. */
export function rearRoofHeight(depth: number) {
  return 10.3 + (depth - 7.8) * (8.95 - 10.3) / (14.6 - 7.8)
}
