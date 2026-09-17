import * as THREE from 'three'

/** Raised tile noses and shallow pans, in metres, above the roof plane. */
export function tileRelief(height: number, run: number) {
  const course = ((height % .095) + .095) % .095 / .095
  const stagger = Math.floor(height / .095) % 2 * .16
  const pan = Math.sin((run + stagger) / .32 * Math.PI)
  return .008 + .022 * (1 - course) + .006 * pan * pan
}

export function articulatedRoof(source: THREE.BufferGeometry) {
  const points = source.getAttribute('position'), index = source.index!, vertices: number[] = []
  for (let f = 0; f < index.count; f += 3) {
    const a = new THREE.Vector3().fromBufferAttribute(points, index.getX(f))
    const b = new THREE.Vector3().fromBufferAttribute(points, index.getX(f + 1))
    const c = new THREE.Vector3().fromBufferAttribute(points, index.getX(f + 2))
    const normal = b.clone().sub(a).cross(c.clone().sub(a))
    const n = Math.ceil(Math.max(a.distanceTo(b), b.distanceTo(c), c.distanceTo(a)) / .18)
    const at = (i: number, j: number) => {
      const p = a.clone().addScaledVector(b.clone().sub(a), i / n).addScaledVector(c.clone().sub(a), j / n)
      p.y += tileRelief(p.y, Math.abs(normal.x) > Math.abs(normal.z) ? p.z : p.x)
      return p.toArray()
    }
    for (let i = 0; i < n; i++) for (let j = 0; j < n - i; j++) {
      vertices.push(...at(i, j), ...at(i + 1, j), ...at(i, j + 1))
      if (i + j < n - 1) vertices.push(...at(i + 1, j), ...at(i + 1, j + 1), ...at(i, j + 1))
    }
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3)); geometry.computeVertexNormals()
  return geometry
}

