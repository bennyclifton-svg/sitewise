import { afterEach, expect, it, vi } from 'vitest'
import * as THREE from 'three'
import { cameraFlight, mountSceneMotion, systemViews } from './scene-motion'
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js'

afterEach(() => { window.dispatchEvent(new Event('pagehide')); vi.useRealTimers(); vi.unstubAllGlobals() })

it('keeps the garage moving when the visitor takes control of the camera', () => {
  vi.useFakeTimers()
  vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener() {}, removeEventListener() {} }))
  vi.stubGlobal('IntersectionObserver', class {
    callback: (entries: { isIntersecting: boolean }[]) => void
    constructor(callback: (entries: { isIntersecting: boolean }[]) => void) { this.callback = callback }
    observe() { this.callback([{ isIntersecting: true }]) }
    disconnect() {}
  })
  const host = document.createElement('div')
  host.innerHTML = '<button data-motion-pause></button><button data-day-night></button><p data-scene-status></p>'
  const controls = Object.assign(new THREE.EventDispatcher<{start: object}>(), { target: new THREE.Vector3(), update() {} })
  const garage = vi.fn()
  const camera = new THREE.PerspectiveCamera()
  camera.position.set(-40, 26, 46)
  const motion = mountSceneMotion({ host, camera, controls: controls as unknown as OrbitControls,
    render() {}, garage })
  motion.focus('mechanical')
  vi.advanceTimersByTime(300)
  const before = garage.mock.calls.length
  controls.dispatchEvent({ type: 'start' })
  const position = camera.position.clone()
  vi.advanceTimersByTime(300)
  expect(garage.mock.calls.length).toBeGreaterThan(before)
  expect(camera.position.equals(position)).toBe(true)
  host.querySelector<HTMLButtonElement>('[data-motion-pause]')!.click()
  const paused = garage.mock.calls.length
  vi.advanceTimersByTime(500)
  expect(garage.mock.calls.length).toBe(paused)
})

it('lands each discipline at its authored view and can retarget without a jump', () => {
  const camera = new THREE.PerspectiveCamera(43, 1)
  const controls = { target: new THREE.Vector3(), update() {} } as unknown as OrbitControls
  camera.position.set(-49, 29, 49)
  for (const system of Object.keys(systemViews) as (keyof typeof systemViews)[]) {
    const start = camera.position.clone()
    const flight = cameraFlight(camera, controls, system)
    flight(0)
    expect(camera.position.distanceTo(start)).toBeLessThan(.00001)
    flight(1)
    expect(camera.position.distanceTo(new THREE.Vector3(...systemViews[system].position))).toBeLessThan(.00001)
    expect(controls.target.toArray()).toEqual(systemViews[system].target)
  }
  cameraFlight(camera, controls, 'civil')(.4)
  const midway = camera.position.clone()
  cameraFlight(camera, controls, 'interiors')(0)
  expect(camera.position.distanceTo(midway)).toBeLessThan(.00001)
})

it('uses still views with reduced motion and lets night lighting change without autoplay', () => {
  vi.useFakeTimers()
  vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener() {}, removeEventListener() {} }))
  vi.stubGlobal('IntersectionObserver', class {
    observe() {}
    disconnect() {}
  })
  const host = document.createElement('div')
  host.innerHTML = '<button data-motion-pause></button><button data-day-night></button>'
  const camera = new THREE.PerspectiveCamera(43, 1)
  camera.position.set(-40, 26, 46)
  const controls = Object.assign(new THREE.EventDispatcher(), { target: new THREE.Vector3(), update() {} })
  const garage = vi.fn(), ambient = vi.fn(), lighting = vi.fn()
  const motion = mountSceneMotion({host, camera, controls: controls as unknown as OrbitControls,
    render() {}, garage, ambient, lighting})
  motion.focus('civil')
  expect(camera.position.distanceTo(new THREE.Vector3(...systemViews.civil.position))).toBeLessThan(.00001)
  host.querySelector<HTMLButtonElement>('[data-day-night]')!.click()
  expect(lighting).toHaveBeenLastCalledWith(1)
  vi.advanceTimersByTime(10000)
  expect(ambient).not.toHaveBeenCalled()
  expect(garage).toHaveBeenCalledTimes(1)
  expect(host.querySelector<HTMLButtonElement>('[data-motion-pause]')!.disabled).toBe(true)
})
