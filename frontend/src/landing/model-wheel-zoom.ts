import * as THREE from 'three'
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js'

/** Gate OrbitControls before its bubbling wheel listener can consume the event. */
export function mountModelWheelZoom(canvas: HTMLCanvasElement, camera: THREE.Camera, controls: OrbitControls, meshes: THREE.Mesh[]) {
  const raycaster = new THREE.Raycaster()
  const pointer = new THREE.Vector2()
  const gate = (event: WheelEvent) => {
    const rect = canvas.getBoundingClientRect()
    controls.enableZoom = false
    if (!rect.width || !rect.height) return
    pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, 1 - (event.clientY - rect.top) / rect.height * 2)
    camera.updateMatrixWorld()
    raycaster.setFromCamera(pointer, camera)
    controls.enableZoom = meshes.some(mesh => {
      if (!mesh.visible) return false
      mesh.updateWorldMatrix(true, false)
      return raycaster.intersectObject(mesh, false).length > 0
    })
  }
  const leave = () => { controls.enableZoom = false }
  canvas.addEventListener('wheel', gate, { capture: true, passive: true })
  canvas.addEventListener('pointerleave', leave)
  return () => {
    canvas.removeEventListener('wheel', gate, true)
    canvas.removeEventListener('pointerleave', leave)
    leave()
  }
}
