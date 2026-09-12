import * as THREE from 'three'

const origin = new THREE.Vector3(-2.12, .5, 10.93335)
const clamp = (value: number) => THREE.MathUtils.clamp(value, 0, 1)
const ease = (value: number) => { const t = clamp(value); return t*t*(3-2*t) }

export function createGarageMotion(parts: { mesh: THREE.Mesh }[]) {
  const cars = parts.filter(({mesh}) => mesh.userData.sw_motion === 'car')
  const slats = parts.filter(({mesh}) => String(mesh.userData.sw_motion).startsWith('door:'))
  for (const {mesh} of cars) {
    // Export batches are in world coordinates; give all vehicle materials one shared pivot.
    mesh.geometry.translate(-origin.x, -origin.y, -origin.z)
    mesh.geometry.scale(.86, .86, .86)
    mesh.position.copy(origin)
  }
  return (progress: number) => {
    const lift = 2.35 * ease((progress-.04)/.16) * (1-ease((progress-.69)/.17))
    for (const {mesh} of slats) {
      const index = Number(String(mesh.userData.sw_motion).split(':')[1])
      const height = .55+index*.1
      const travel = height+lift
      const angle = Math.min(Math.PI*1.8, Math.max(0,(travel-2.8)/.19))
      // Slats follow the lintel drum instead of stretching or sinking into the ground.
      mesh.position.set(.19*(1-Math.cos(angle)), Math.min(travel,2.8)+.19*Math.sin(angle)-height, 0)
    }
    let x: number
    let z=origin.z, heading=0
    if (progress < .48) x=THREE.MathUtils.lerp(origin.x,-7.9,ease((progress-.22)/.26))
    else if (progress < .67) {
      heading=ease((progress-.48)/.19)*Math.PI/2
      x=-7.9-1.75*Math.sin(heading)
      z=origin.z+1.75*(1-Math.cos(heading))
    } else {
      heading=Math.PI/2; x=-9.65
      // Stop with the nose behind the footpath, while still on the driveway.
      z=THREE.MathUtils.lerp(origin.z+1.75,19.4,ease((progress-.67)/.30))
    }
    const elevation=.5-.23*ease((-x-4.9)/2)-.36*ease((z-22)/2)
    for (const {mesh} of cars) { mesh.position.set(x,elevation,z); mesh.rotation.y=heading }
  }
}
