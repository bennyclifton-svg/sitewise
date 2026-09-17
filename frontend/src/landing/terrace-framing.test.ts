import { expect, it } from 'vitest'
import * as THREE from 'three'
import { terraceDistance } from './terrace-framing'

it.each([{ desktop: true, width: .57 }, { desktop: false, width: .92 }, { desktop: true, width: .64 }])('keeps the full site inside the available frame ($desktop, $width)', ({ desktop, width }) => {
  const bounds = new THREE.Box3(new THREE.Vector3(-5, -3, -24), new THREE.Vector3(54, 12, 12))
  const centre = bounds.getCenter(new THREE.Vector3())
  const direction = new THREE.Vector3(0, .15, 1).normalize()
  const aspect = desktop ? 1.6 : 1.25
  const camera = new THREE.PerspectiveCamera(42, aspect, .1, 1000)
  const distance = terraceDistance(bounds, centre, direction, camera.up, camera.fov, aspect, desktop, width)
  camera.position.copy(centre).addScaledVector(direction, distance)
  camera.lookAt(centre)
  camera.updateMatrixWorld()
  for (const x of [bounds.min.x, bounds.max.x])
    for (const y of [bounds.min.y, bounds.max.y])
      for (const z of [bounds.min.z, bounds.max.z]) {
        const point = new THREE.Vector3(x, y, z).project(camera)
        expect(Math.abs(point.x)).toBeLessThanOrEqual(width + 1e-6)
        expect(Math.abs(point.y)).toBeLessThanOrEqual(.72 + 1e-6)
        expect(point.z).toBeLessThan(1)
      }
})
