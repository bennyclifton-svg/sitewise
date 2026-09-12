import * as THREE from 'three'

const clamp = (value: number) => THREE.MathUtils.clamp(value, 0, 1)
const ease = (value: number) => { const t = clamp(value); return t*t*(3-2*t) }

// Hermite distance curves share their endpoint speeds, so the car never stops
// between manoeuvres. Speeds are metres per unit of animation progress.
function travel(t: number, start: number, end: number, length: number, speedIn: number, speedOut: number) {
  const u = clamp((t-start)/(end-start)), u2 = u*u, u3 = u2*u
  return (-2*u3+3*u2)*length + (u3-2*u2+u)*(end-start)*speedIn + (u3-u2)*(end-start)*speedOut
}

export function createGarageMotion(parts: { mesh: THREE.Mesh }[]) {
  const cars = parts.filter(({mesh}) => mesh.userData.sw_motion === 'car')
  const anchor: unknown = cars[0]?.mesh.userData.sw_car_origin
  if (!Array.isArray(anchor) || anchor.length !== 3 || !anchor.every(value => typeof value === 'number' && Number.isFinite(value))) {
    throw new Error('Animated vehicle requires its model garage origin')
  }
  const origin = new THREE.Vector3(anchor[0], anchor[1], anchor[2])
  const rearAxleOffset = 1.4
  const turnStartX = -7.9 + rearAxleOffset
  const radius = turnStartX + 9.65
  const approach = origin.x + rearAxleOffset - turnStartX
  const corner = radius * Math.PI/2
  const departure = 19.4 - rearAxleOffset - origin.z - radius
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
    let distance: number
    if (progress < .48) distance=travel(progress,.22,.48,approach,0,22)
    else if (progress < .69) distance=approach+travel(progress,.48,.69,corner,22,24)
    else if (progress < .83) distance=approach+corner+travel(progress,.69,.83,departure*.6,24,34)
    else distance=approach+corner+departure*.6+travel(progress,.83,.97,departure*.4,34,0)
    let rearX: number, rearZ=origin.z, heading=0
    if (distance < approach) rearX=origin.x+rearAxleOffset-distance
    else if (distance < approach+corner) {
      heading=(distance-approach)/radius
      rearX=turnStartX-radius*Math.sin(heading)
      rearZ+=radius*(1-Math.cos(heading))
    } else {
      heading=Math.PI/2; rearX=-9.65
      rearZ+=radius+distance-approach-corner
    }
    // Follow the rear axle around the corner; the body swings forward of it.
    // This gives a rolling turn instead of rotating the vehicle about its centre.
    const x=rearX-rearAxleOffset*Math.cos(heading)
    const z=rearZ+rearAxleOffset*Math.sin(heading)
    const elevation=.5-.23*ease((-x-4.9)/2)-.36*ease((z-22)/2)
    for (const {mesh} of cars) { mesh.position.set(x,elevation,z); mesh.rotation.y=heading }
  }
}
