import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { createDetachedScene } from './detached-scene'
import { detachedLayout } from './detached-layout'
import { batchDetached, prepareDetachedMaterial } from './detached-material'
import { terraceDistance } from './terrace-framing'
import { mountModelWheelZoom } from './model-wheel-zoom'

const host = document.querySelector<HTMLElement>('[data-detached-viewer]')!
const status = document.querySelector<HTMLElement>('[role="status"]')!
try {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.localClippingEnabled = true
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = .9
  host.append(renderer.domElement)
  renderer.domElement.setAttribute('aria-label', 'Four detached houses. Third house is a blue cutaway. Drag to orbit and scroll to zoom.')
  renderer.domElement.setAttribute('role', 'img')
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(35, 1, .1, 500)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = false; controls.enableZoom = false; controls.maxPolarAngle = Math.PI * .49
  controls.minDistance = 8; controls.maxDistance = 150
  const pmrem = new THREE.PMREMGenerator(renderer), room = new RoomEnvironment()
  const environment = pmrem.fromScene(room, .04)
  room.dispose(); pmrem.dispose(); scene.environment = environment.texture; scene.environmentIntensity = .07
  scene.add(new THREE.HemisphereLight('#FFFFFF', '#292929', .20))
  const sun = new THREE.DirectionalLight('#FFFFFF', 3)
  sun.position.set(-2, 40, 20); sun.target.position.set(23, 0, -6)
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048)
  Object.assign(sun.shadow.camera, { left: -40, right: 40, top: 35, bottom: -35, far: 120 })
  sun.shadow.bias = -.0004; sun.shadow.normalBias = .025
  scene.add(sun, sun.target)
  const decoder = new DRACOLoader().setDecoderPath('/landing-assets/coordination/draco/')
  const car = await new GLTFLoader().setDRACOLoader(decoder).loadAsync('/landing-assets/coordination/terrace-car.glb')
  decoder.dispose()
  const { model, plinth } = createDetachedScene(car.scene)
  const counts = batchDetached(model)
  host.dataset.meshesBefore = String(counts.before); host.dataset.meshesAfter = String(counts.after)
  const meshes: THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>[] = []
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh) || !(object.material instanceof THREE.MeshStandardMaterial)) return
    prepareDetachedMaterial(object.material)
    const blue = object.userData.sw_dwelling === detachedLayout.cutaway
    object.material.color.set(blue ? '#087ac9' : '#FFFFFF')
    if (object.userData.sw_glass) {
      object.material.color.set(blue ? '#087ac9' : '#7f929f')
      object.material.roughness = .2
      object.material.transparent = true; object.material.opacity = .58; object.material.depthWrite = false
    }
    object.castShadow = !object.userData.sw_glass; object.receiveShadow = true
    meshes.push(object as THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>)
  })
  scene.add(model, plinth)
  const bounds = new THREE.Box3().setFromObject(model), centre = bounds.getCenter(new THREE.Vector3())
  let fitted = true
  const render = () => {
    renderer.render(scene, camera)
    host.dataset.drawCalls = String(renderer.info.render.calls)
    host.dataset.triangles = String(renderer.info.render.triangles)
  }
  function frame(view = 'street') {
    const direction = new THREE.Vector3(...(view === 'plan' ? [0, 1, .001] : view === 'front' ? [0, .1, 1] : [.48, .38, 1]) as [number, number, number]).normalize()
    const distance = terraceDistance(bounds, centre, direction, camera.up, camera.fov, camera.aspect, false, .9)
    controls.target.copy(centre); camera.position.copy(centre).addScaledVector(direction, distance); controls.update(); render()
  }
  const resize = () => {
    camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix()
    camera.zoom = camera.aspect > 1.4 ? 1.25 : 1; camera.updateProjectionMatrix()
    renderer.setSize(host.clientWidth, host.clientHeight)
    if (fitted) frame()
    else render()
  }
  controls.addEventListener('start', () => { fitted = false })
  controls.addEventListener('change', render)
  const wheelDispose = mountModelWheelZoom(renderer.domElement, camera, controls, meshes)
  const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), .025)
  let active = 'all'
  const filters = [...document.querySelectorAll<HTMLButtonElement>('[data-system]')]
  const select = (system: string) => {
    active = system; plinth.visible = system === 'all'
    for (const mesh of meshes) {
      const cutaway = mesh.userData.sw_dwelling === detachedLayout.cutaway
      mesh.visible = system === 'all' ? !(cutaway && mesh.userData.sw_system === 'architecture') : mesh.userData.sw_system === system
      mesh.material.clippingPlanes = system === 'all' ? [ground] : []
    }
    filters.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.system === system)))
    status.textContent = system === 'all' ? 'Four detached houses. House three reveals structure, interiors and services.' : `${system[0].toUpperCase()}${system.slice(1)} across four houses.`
    render()
  }
  filters.forEach(button => button.addEventListener('click', () => select(active === button.dataset.system ? 'all' : button.dataset.system!)))
  document.querySelectorAll<HTMLButtonElement>('[data-view]').forEach(button => button.addEventListener('click', () => frame(button.dataset.view)))
  const observer = new ResizeObserver(resize); observer.observe(host)
  window.addEventListener('pagehide', () => {
    observer.disconnect(); wheelDispose(); controls.dispose(); environment.dispose()
    scene.traverse(object => {
      if (object instanceof THREE.Mesh) { object.geometry.dispose(); if (!Array.isArray(object.material)) object.material.dispose() }
    })
    renderer.dispose()
  }, { once: true })
  resize(); select('all')
} catch (error) {
  status.textContent = 'The detached study could not load. Please reload to try again.'
  console.error(error)
}
