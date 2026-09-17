import * as THREE from 'three'

/** Fit every site-bound corner inside the model's reserved screen area. */
export function terraceDistance(bounds: THREE.Box3, centre: THREE.Vector3, direction: THREE.Vector3, cameraUp: THREE.Vector3, fov: number, aspect: number, desktop: boolean, widthFraction = desktop ? .57 : .92) {
  const right = new THREE.Vector3().crossVectors(cameraUp, direction).normalize()
  const up = new THREE.Vector3().crossVectors(direction, right).normalize()
  const vertical = Math.tan(THREE.MathUtils.degToRad(fov / 2))
  const horizontal = vertical * aspect
  let distance = 70
  if (!bounds.isEmpty()) {
    for (const x of [bounds.min.x, bounds.max.x])
      for (const y of [bounds.min.y, bounds.max.y])
        for (const z of [bounds.min.z, bounds.max.z]) {
          const point = new THREE.Vector3(x, y, z).sub(centre)
          distance = Math.max(distance,
            point.dot(direction) + Math.abs(point.dot(right)) / (horizontal * widthFraction),
            point.dot(direction) + Math.abs(point.dot(up)) / (vertical * .72))
        }
  }
  return distance
}
