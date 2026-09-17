import * as THREE from 'three'
import { box, part, pipe, type Point } from './terrace-parts'
import { rearRoofHeight } from './terrace-life'

export function rollerLift(time: number, reduced = false) {
  const t = THREE.MathUtils.clamp((time - 3) / 5, 0, 1)
  return reduced ? 2.5 : 2.5 * t * t * (3 - 2 * t)
}

export function rollerPose(index: number, lift: number) {
  const travel = .445 + index * .09 + lift
  const top = 2.65, radius = .24
  if (travel <= top) return { y: travel, z: 0, angle: 0 }
  const arc = Math.min(Math.PI / 2, (travel - top) / radius)
  return { y: top + radius * Math.sin(arc), z: -radius * (1 - Math.cos(arc)) - Math.max(0, travel - top - radius * Math.PI / 2), angle: arc }
}

export function addAnimatedDetails(model: THREE.Group) {
  for (let house = 1; house <= 7; house++) {
    const x = (house - 1) * 7 + (house === 7 ? .8 : 6.1), z = -8.8
    const roof = rearRoofHeight(-z)
    const base = part(model, new THREE.CylinderGeometry(.24, .32, .15, 16), 'mechanical', house)
    base.position.set(x, roof + .09, z)
    const neck = part(model, new THREE.CylinderGeometry(.18, .18, .30, 12), 'mechanical', house)
    neck.position.set(x, roof + .30, z)
    const rotor = new THREE.Group()
    rotor.position.set(x, roof + .58, z)
    rotor.userData.sw_rotor = house
    const dome = part(rotor, new THREE.SphereGeometry(.28, 16, 10), 'mechanical', house)
    dome.scale.setScalar(1)
    for (let i = 0; i < 16; i++) {
      // Curved seams hug a spherical turbine rather than projecting as boxy fins.
      const points = Array.from({ length: 13 }, (_, j) => {
        const latitude = -.5 * Math.PI + .12 + j / 12 * (Math.PI - .24)
        const angle = i * Math.PI / 8 + latitude * .45
        return [Math.cos(latitude) * Math.sin(angle) * .285, Math.sin(latitude) * .285, Math.cos(latitude) * Math.cos(angle) * .285] as Point
      })
      pipe(rotor, points, .008, 'mechanical', house)
    }
    model.add(rotor)
  }
  for (let i = 0; i < 2; i++) {
    const bird = new THREE.Group()
    bird.name = `White finch ${i + 1}`
    bird.userData.sw_bird = { index: i, cycle: -1 }
    const body = part(bird, new THREE.SphereGeometry(.035, 8, 6), 'landscape', 0, '#FFFFFF')
    body.scale.set(1.7, .8, .8)
    for (const side of [-1, 1]) {
      const pivot = new THREE.Group()
      pivot.userData.sw_wing = side
      const wing = box(pivot, [.065, .006, .11], [0, 0, side * .075], 'landscape', 0, '#FFFFFF')
      wing.rotation.y = side * -.3
      bird.add(pivot)
    }
    bird.traverse(object => {
      object.userData.sw_fit = false
      if (object instanceof THREE.Mesh) {
        // Tiny white birds should stay light even when their wings turn from the sun.
        const material = object.material as THREE.MeshStandardMaterial
        material.emissive.set('#FFFFFF'); material.emissiveIntensity = .45
      }
    })
    bird.visible = false
    model.add(bird)
  }
}

export function mountTerraceAnimation(model: THREE.Group, host: HTMLElement, render: () => void, updateShadows: () => void = () => {}) {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)')
  const rotors: THREE.Object3D[] = [], wings: THREE.Object3D[] = [], slats: THREE.Object3D[] = [], birds: THREE.Object3D[] = [], fans: THREE.Object3D[] = []
  model.traverse(object => {
    if (object.userData.sw_condenserFan) fans.push(object)
    if (object.userData.sw_rotor) rotors.push(object)
    if (object.userData.sw_wing) wings.push(object)
    if (object.userData.sw_roller) slats.push(object)
    if (object.userData.sw_bird) birds.push(object)
  })
  let raf = 0, elapsed = 0, previous = 0, onscreen = false, previousLift = -1
  function pose(time: number) {
    fans.forEach(fan => { fan.rotation.z = time * 9 })
    rotors.forEach((rotor, i) => { rotor.rotation.y = time * (.8 + i * .055) })
    const lift = rollerLift(time, reduced.matches)
    if (lift !== previousLift) { updateShadows(); previousLift = lift }
    slats.forEach(slat => {
      const state = rollerPose(slat.userData.sw_roller.index, lift)
      slat.position.y = state.y
      slat.position.z = slat.userData.sw_roller.front + state.z
      slat.rotation.x = state.angle
    })
    birds.forEach(bird => {
      const state = bird.userData.sw_bird
      const period = state.index === 0 ? 43 : 59
      const cycle = Math.floor(time / period)
      if (cycle !== state.cycle) {
        state.cycle = cycle
        state.start = 8 + Math.random() * 7 + state.index * 2.3
        state.duration = 1.5 + Math.random() * .7
        state.distance = 55 + Math.random() * 18
        state.rise = 8 + Math.random() * 7
        state.depth = (state.index ? -1 : 1) * (8 + Math.random() * 10)
      }
      const t = (time % period - state.start) / state.duration
      bird.visible = !reduced.matches && t >= 0 && t <= 1
      if (bird.visible) {
        bird.position.set(6 + t * state.distance, 3.6 + t * state.rise + Math.sin(t * Math.PI * 3) * .45, 1 + t * state.depth + Math.sin(t * Math.PI * 2) * .8)
        bird.rotation.y = -Math.atan2(state.depth, state.distance)
        bird.rotation.z = Math.atan2(state.rise, state.distance)
      }
    })
    wings.forEach((wing, i) => { wing.rotation.x = wing.userData.sw_wing * Math.sin(time * (31 + i) + i * 1.7) * .9 })
  }

  function tick(now: number) {
    raf = requestAnimationFrame(tick)
    if (previous && now - previous < 32) return
    elapsed += previous ? Math.min((now - previous) / 1000, .1) : 0
    previous = now
    pose(elapsed); render()
  }
  function sync() {
    cancelAnimationFrame(raf); previous = 0
    pose(elapsed); render()
    if (onscreen && !document.hidden && !reduced.matches) raf = requestAnimationFrame(tick)
  }
  const observer = new IntersectionObserver(([entry]) => { onscreen = entry.isIntersecting; sync() })
  observer.observe(host)
  document.addEventListener('visibilitychange', sync)
  reduced.addEventListener('change', sync)
  sync()
  return () => {
    cancelAnimationFrame(raf); observer.disconnect()
    document.removeEventListener('visibilitychange', sync)
    reduced.removeEventListener('change', sync)
  }
}
