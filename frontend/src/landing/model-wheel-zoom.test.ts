import { expect, it } from 'vitest'
import * as THREE from 'three'
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { mountModelWheelZoom } from './model-wheel-zoom'

it('consumes wheel only over visible model geometry and releases it outside', () => {
  const canvas = document.createElement('canvas')
  canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 200, height: 200 }) as DOMRect
  const camera = new THREE.PerspectiveCamera(50, 1, .1, 100)
  camera.position.z = 5
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial())
  const controls = { enableZoom: false } as OrbitControls
  // Matches OrbitControls' existing bubble listener, registered before the gate.
  canvas.addEventListener('wheel', event => { if (controls.enableZoom) event.preventDefault() })
  const dispose = mountModelWheelZoom(canvas, camera, controls, [mesh])
  const wheel = (x: number, y: number) => {
    const event = new WheelEvent('wheel', { clientX: x, clientY: y, cancelable: true })
    canvas.dispatchEvent(event)
    return event.defaultPrevented
  }
  expect(wheel(100, 100)).toBe(true)
  expect(wheel(5, 5)).toBe(false)
  mesh.visible = false
  expect(wheel(100, 100)).toBe(false)
  mesh.visible = true
  expect(wheel(100, 100)).toBe(true)
  canvas.dispatchEvent(new Event('pointerleave'))
  expect(controls.enableZoom).toBe(false)
  dispose()
  expect(wheel(100, 100)).toBe(false)
  mesh.geometry.dispose(); mesh.material.dispose()
})
