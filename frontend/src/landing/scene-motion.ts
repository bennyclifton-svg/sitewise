import * as THREE from 'three'
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js'

// Targets follow the detailed southern dwelling; civil and landscape need the whole site.
export const systemViews = {
  all: { position: [-49, 29, 49], target: [0, 1, 3] },
  architecture: { position: [-23, 15, 34], target: [0, 4, 10] },
  structure: { position: [-19, 23, 30], target: [0, 4, 10] },
  electrical: { position: [-17, 13, 28], target: [0, 4.5, 11] },
  mechanical: { position: [17, 15, 31], target: [0, 4.8, 11] },
  hydraulic: { position: [19, 11, 25], target: [0, 3.2, 11] },
  civil: { position: [-25, 51, 39], target: [-2, -1, 3] },
  landscape: { position: [35, 22, 33], target: [6, 1, 2] },
  interiors: { position: [-15, 15, 26], target: [0, 4, 11] },
} satisfies Record<string, { position: number[]; target: number[] }>
export type SystemView = keyof typeof systemViews

export function cameraFlight(camera: THREE.PerspectiveCamera | THREE.OrthographicCamera, controls: OrbitControls, system: SystemView) {
  const view = systemViews[system]
  const fromTarget = controls.target.clone()
  const toTarget = new THREE.Vector3(...view.target)
  const from = new THREE.Spherical().setFromVector3(camera.position.clone().sub(fromTarget))
  const to = new THREE.Spherical().setFromVector3(new THREE.Vector3(...view.position).sub(toTarget))
  const aspect = camera instanceof THREE.PerspectiveCamera ? camera.aspect : (camera.right-camera.left)/(camera.top-camera.bottom)
  to.radius *= Math.max(1, Math.min(1.35, .82 / aspect))
  const turn = THREE.MathUtils.euclideanModulo(to.theta - from.theta + Math.PI, Math.PI * 2) - Math.PI
  return (progress: number) => {
    const t = THREE.MathUtils.clamp(progress, 0, 1)
    const ease = t*t*t*(t*(t*6-15)+10)
    const orbit = new THREE.Spherical(
      THREE.MathUtils.lerp(from.radius, to.radius, ease) + Math.sin(Math.PI * ease) * 2,
      THREE.MathUtils.lerp(from.phi, to.phi, ease), from.theta + turn * ease,
    )
    controls.target.lerpVectors(fromTarget, toTarget, ease)
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(orbit))
    controls.update()
  }
}

type SceneMotion = {
  host: HTMLElement; camera: THREE.PerspectiveCamera | THREE.OrthographicCamera; controls: OrbitControls;
  render: () => void; garage: (progress: number) => void;
  ambient?: (elapsed: number) => void; lighting?: (night: number) => void;
}

export function mountSceneMotion({host,camera,controls,render,garage,ambient,lighting}: SceneMotion) {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)')
  const pause = host.querySelector<HTMLButtonElement>('[data-motion-pause]')
  const day = host.querySelector<HTMLButtonElement>('[data-day-night]')
  let raf = 0, previous = 0, elapsed = 0, flightTime = 0
  let onscreen = false, paused = reduced.matches, disposed = false
  let night = 0, nightTarget = 0
  let flight: ((progress: number) => void) | undefined
  function cancelCamera() { flight = undefined }
  function sync() {
    cancelAnimationFrame(raf); previous = 0
    if (!disposed && onscreen && !document.hidden && !paused) raf = requestAnimationFrame(tick)
    pause?.setAttribute('aria-pressed', String(paused))
    if (pause) { pause.setAttribute('aria-label', paused ? 'Resume animation' : 'Pause animation'); pause.disabled = reduced.matches }
  }
  function tick(now: number) {
    const delta = previous ? Math.min(now - previous, 64) : 0
    previous = now; elapsed += delta
    garage(Math.min(1, elapsed / 18000))
    ambient?.(elapsed / 1000)
    const step = delta / 4000
    night += Math.sign(nightTarget - night) * Math.min(Math.abs(nightTarget - night), step)
    lighting?.(night * night * (3 - 2 * night))
    if (flight) {
      flightTime += delta
      flight(Math.min(1, flightTime / 3200))
      if (flightTime >= 3200) flight = undefined
    }
    render()
    raf = requestAnimationFrame(tick)
  }
  function focus(system: SystemView) {
    flight = cameraFlight(camera, controls, system); flightTime = 0
    flight(1); flight = undefined; render()
  }
  const togglePause = () => { paused = !paused; cancelCamera(); sync(); window.dispatchEvent(new CustomEvent('sitewise:motion-pause', {detail: paused})) }
  const toggleDay = () => {
    nightTarget = 1 - nightTarget
    day?.setAttribute('aria-pressed', String(Boolean(nightTarget)))
    day?.setAttribute('aria-label', nightTarget ? 'Switch to daylight' : 'Switch to night lighting')
    if (paused || reduced.matches) { night = nightTarget; lighting?.(night); render() }
  }
  const preferenceChanged = () => { paused = reduced.matches; cancelCamera(); sync() }
  const projectFocus = () => { focus('architecture') }
  controls.addEventListener('start', cancelCamera)
  pause?.addEventListener('click', togglePause)
  day?.addEventListener('click', toggleDay)
  reduced.addEventListener('change', preferenceChanged)
  document.addEventListener('visibilitychange', sync)
  window.addEventListener('sitewise:project-focus', projectFocus)
  const observer = new IntersectionObserver(([entry]) => { onscreen = entry.isIntersecting; sync() })
  observer.observe(host)
  if (pause) pause.disabled = reduced.matches
  if (day) day.disabled = false
  garage(0); lighting?.(0); sync()
  window.addEventListener('pagehide', () => {
    disposed = true; cancelAnimationFrame(raf); observer.disconnect()
    controls.removeEventListener('start', cancelCamera)
    reduced.removeEventListener('change', preferenceChanged)
    document.removeEventListener('visibilitychange', sync)
    window.removeEventListener('sitewise:project-focus', projectFocus)
  }, { once: true })
  return { focus, cancelCamera }
}
