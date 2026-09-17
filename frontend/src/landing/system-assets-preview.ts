import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const host = document.querySelector<HTMLElement>('#asset-view')!
const status = document.querySelector<HTMLElement>('#asset-status')!
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
renderer.toneMapping = THREE.ACESFilmicToneMapping
host.append(renderer.domElement)
renderer.domElement.setAttribute('aria-label', '3D asset preview. Drag to rotate and scroll to zoom.')
const scene = new THREE.Scene()
scene.add(new THREE.HemisphereLight('#ffffff', '#b3aca1', 2))
const key = new THREE.DirectionalLight('#ffffff', 3)
key.position.set(-3, 6, 4)
scene.add(key)
const camera = new THREE.PerspectiveCamera(35, 1, .01, 100)
const controls = new OrbitControls(camera, renderer.domElement)
controls.enablePan = false
const render = () => renderer.render(scene, camera)
controls.addEventListener('change', render)
const loader = new GLTFLoader()
let current: THREE.Group | undefined
let request = 0
function dispose(model: THREE.Group) {
  model.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    object.geometry.dispose()
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) material.dispose()
  })
}
async function select(button: HTMLButtonElement) {
  const id = ++request
  status.textContent = `Loading ${button.dataset.label}…`
  try {
    const { scene: model } = await loader.loadAsync(`/landing-assets/system-3d/${button.dataset.asset}.glb`)
    if (id !== request) { dispose(model); return }
    if (current) { scene.remove(current); dispose(current) }
    current = model
    scene.add(model)
    const bounds = new THREE.Box3().setFromObject(model)
    const centre = bounds.getCenter(new THREE.Vector3())
    const size = bounds.getSize(new THREE.Vector3()).length()
    camera.position.copy(centre).add(new THREE.Vector3(.7, 1.5, 1.6).normalize().multiplyScalar(size * 1.65))
    controls.target.copy(centre)
    controls.minDistance = size * .6
    controls.maxDistance = size * 4
    controls.update()
    document.querySelectorAll<HTMLButtonElement>('[data-asset]').forEach(item => item.setAttribute('aria-pressed', String(item === button)))
    status.textContent = `${button.dataset.label} · Drag to rotate · Scroll to zoom`
    render()
  } catch {
    if (id === request) status.textContent = 'Could not load this asset. Select it again to retry.'
  }
}
const resize = new ResizeObserver(() => {
  const { width, height } = host.getBoundingClientRect()
  renderer.setSize(width, height)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  render()
})
resize.observe(host)
const buttons = [...document.querySelectorAll<HTMLButtonElement>('[data-asset]')]
buttons.forEach(button => button.addEventListener('click', () => void select(button)))
void select(buttons[0])
window.addEventListener('pagehide', () => {
  request++
  if (current) dispose(current)
  resize.disconnect()
  controls.dispose()
  renderer.dispose()
}, { once: true })
