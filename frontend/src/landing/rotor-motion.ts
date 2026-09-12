import * as THREE from 'three'

export function createRotors(parts: { mesh: THREE.Mesh }[]) {
  const rotors = parts.flatMap(({ mesh }) => {
    const [kind, axis, x, y, z] = String(mesh.userData.sw_motion ?? '').split(':')
    if (kind !== 'rotor' || (axis !== 'y' && axis !== 'z')) return []
    const pivot = new THREE.Vector3(Number(x), Number(y), Number(z))
    if (![pivot.x, pivot.y, pivot.z].every(Number.isFinite)) return []
    mesh.geometry.translate(-pivot.x, -pivot.y, -pivot.z)
    mesh.position.copy(pivot)
    return [{ mesh, axis, speed: axis === 'y' ? 1.8 : 6 } as const]
  })
  return (elapsed: number) => {
    for (const { mesh, axis, speed } of rotors) mesh.rotation[axis] = elapsed * speed % (Math.PI * 2)
  }
}
