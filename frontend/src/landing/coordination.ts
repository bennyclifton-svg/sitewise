import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { mountSceneMotion } from './scene-motion'
import { createGarageMotion } from './garage-motion'
import { createRotors } from './rotor-motion'
import { createNightLighting } from './night-lighting'
import { type SequenceFrame } from './discipline-sequence'
import { createDwellingReveal, initialDwellingFrame } from './dwelling-reveal'
import { mountModelWheelZoom } from './model-wheel-zoom'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
const systems = {
  all: ['Whole project', '#F7F7F4', 'Drag to orbit · Scroll over the model to zoom, elsewhere to explore the page'],
  architecture: ['Architecture', '#F7F7F4', 'Envelope, rooms and glazing'],
  structure: ['Structure', '#D3B793', 'Five townhouses · Concrete frames · Strip footings · Eight trusses per dwelling'],
  electrical: ['Electrical', '#F38F78', 'Five townhouses · Lighting and GPO circuits · Room switches · Dedicated appliances'],
  mechanical: ['Mechanical', '#DEDF88', 'Five townhouses · Supply ducts · Extract ventilation · Individual condensers'],
  hydraulic: ['Hydraulic', '#93CEDD', 'Five townhouses · Hot and cold water · Sanitary drainage · Shared site connections'],
  civil: ['Civil', '#CAD3D4', 'Stormwater pits · Five house connections · Detention tank · One road outlet'],
  landscape: ['Landscape', '#9FC79B', 'Rear pergolas · Breakfast terraces · Trees and layered planting'],
  interiors: ['Interiors', '#D6A986', 'Furniture, kitchen joinery and interior fittings'],
} as const
type System = keyof typeof systems
type Part = { mesh: THREE.Mesh; material: THREE.MeshStandardMaterial; original: THREE.MeshStandardMaterial; system: string; memberships: string[]; glass: boolean; backdrop: boolean }
export function isSiteBackdrop(name: string, system: string): boolean {
  return system === 'context'
    || /Petrol[ _]ground/i.test(name)
    || /earth plane/i.test(name)
    || /cadastral/i.test(name)
    || /White map lines/i.test(name)
}
async function start(host: HTMLElement) {
  const viewport = host.querySelector<HTMLElement>('.sw-scene-viewport')!
  const status = host.querySelector<HTMLElement>('[data-scene-status]')!
  const buttons = [...host.querySelectorAll<HTMLButtonElement>('[data-system]')]
  let renderer: THREE.WebGLRenderer
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, logarithmicDepthBuffer: true })
  } catch {
    status.textContent = '3D is unavailable on this device. Showing the project image.'
    return
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75))
  renderer.setClearColor(0x000000, 0)
  renderer.domElement.style.background = 'transparent'
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = .9
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  const scene = new THREE.Scene()
  scene.fog = null
  const studio = new RoomEnvironment()
  const pmrem = new THREE.PMREMGenerator(renderer)
  const environment = pmrem.fromScene(studio, .06)
  scene.environment = environment.texture
  scene.environmentIntensity = .18
  studio.dispose(); pmrem.dispose()
  const camera = new THREE.PerspectiveCamera(42, 1, .1, 1000)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enablePan = false
  controls.enableZoom = false
  controls.zoomSpeed = .7
  controls.minDistance = 10
  controls.maxDistance = 110
  controls.minZoom = .5
  controls.maxZoom = 5
  controls.maxPolarAngle = Math.PI * .49
  const sky = new THREE.HemisphereLight('#FFFFFF', '#444444', .55)
  scene.add(sky)
  const key = new THREE.DirectionalLight('#FFFFFF', 2.4)
  key.position.set(-32, 28, -18)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -36, right: 36, top: 36, bottom: -36, near: 1, far: 130 })
  key.shadow.bias = -.0002
  key.shadow.normalBias = .03
  scene.add(key)
  const fill = new THREE.DirectionalLight('#FFFFFF', .65)
  fill.position.set(20, 20, -25)
  scene.add(fill)
  let visible = true
  const render = () => { if (visible && !document.hidden) renderer.render(scene, camera) }
  function resize() {
    const { width, height } = viewport.getBoundingClientRect()
    if (!width || !height) return
    camera.aspect = width / height
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(21)) * Math.max(1, height / width)))
    // Keep the subject right of the copy while retaining a full-hero drawing surface.
    const desktop = window.innerWidth >= 800
    camera.setViewOffset(width, height, desktop ? -width * .16 : 0, desktop ? 0 : -height * .20, width, height)
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    render()
  }
  function frontDistance() {
    return window.innerWidth >= 800 ? 44 : 30
  }
  function frontDirection(): [number, number, number] {
    const distance = frontDistance()
    return [-distance, distance * .32, distance * .34]
  }
  function frame() {
    controls.maxPolarAngle = Math.PI / 2
    camera.up.set(0, 1, 0)
    controls.target.set(0, 3, 3)
    camera.position.copy(controls.target).add(new THREE.Vector3(...frontDirection()))
    host.querySelectorAll<HTMLButtonElement>('[data-camera-view]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.cameraView === 'front'))
    })
    controls.update()
    render()
  }
  frame()
  status.textContent = 'Loading the coordinated project…'
  const decoder = new DRACOLoader().setDecoderPath(new URL(/* @vite-ignore */ './draco/', import.meta.url).href)
  try {
    const gltf = await new GLTFLoader().setDRACOLoader(decoder).loadAsync(new URL(/* @vite-ignore */ './sitewise-coordination.glb', import.meta.url).href)
    decoder.dispose()
    const parts: Part[] = []
    gltf.scene.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return
      const original = object.material as THREE.MeshStandardMaterial
      if (!original.isMeshStandardMaterial) return
      const material = original.clone()
      object.material = material
      const system = String(object.userData.sw_system ?? 'architecture')
      const backdrop = isSiteBackdrop(object.name, system)
      if (backdrop) object.visible = false
      material.color.set('#FFFFFF')
      material.metalness = 0
      material.roughness = object.userData.sw_glass ? .16 : .38
      const associations: unknown = JSON.parse(String(object.userData.sw_service_systems ?? '[]'))
      const memberships = [system, ...(Array.isArray(associations) ? associations.filter((s): s is string => typeof s === 'string') : [])]
      const glass = Boolean(object.userData.sw_glass)
      object.castShadow = !glass && !backdrop
      object.receiveShadow = !glass
      if (glass) { material.transparent = true; material.opacity = .13; material.depthWrite = false }
      parts.push({ mesh: object, material, original: material.clone(), system, memberships, glass, backdrop })
    })
    scene.add(gltf.scene)
    const disposeWheelZoom = mountModelWheelZoom(renderer.domElement, camera, controls, parts.filter(part => !part.backdrop).map(part => part.mesh))
    const outlines = new THREE.Group()
    const outlineData: number[][] = await fetch(new URL(/* @vite-ignore */ './dwelling-outlines.json', import.meta.url)).then(response => {
      if (!response.ok) throw new Error('Building outlines could not load')
      return response.json()
    })
    const outlineMaterials = outlineData.map(coordinates => {
      const material = new THREE.LineBasicMaterial({ color: '#657587', transparent: true, opacity: 0, depthWrite: false })
      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(coordinates, 3))
      outlines.add(new THREE.LineSegments(geometry, material))
      return material
    })
    scene.add(outlines)
    viewport.append(renderer.domElement)
    renderer.domElement.setAttribute('aria-label', 'Interactive development model. Drag to orbit. Scroll over the model to zoom; scroll outside it to move down the page.')
    renderer.domElement.setAttribute('role', 'img')
    host.classList.add('is-live')
    let locked: System = 'all'
    let nightAmount = 0
    let activeSystem: System = 'all'
    const garage = createGarageMotion(parts)
    const rotors = createRotors(parts)
    const occupiedLighting = createNightLighting(scene, parts)
    const reveal = createDwellingReveal(parts)
    let lastLabel = ''
    function display(frame: SequenceFrame) {
      reveal.apply(frame)
      outlineMaterials.forEach((material, i) => {
        const state = frame.houses[i]
        const opacity = ['all', 'architecture', 'exposed'].includes(state.discipline) ? 0 : .13 * state.amount
        material.opacity = opacity
      })
      const uniform = frame.houses.every(h => h.discipline === frame.houses[0].discipline)
      activeSystem = frame.label === 'Whole project' ? 'all' : uniform ? frame.houses[0].discipline as System : 'all'
      host.dataset.activeSystem = uniform ? activeSystem : 'mixed'
      host.dataset.tourState = 'manual'
      for (const button of buttons) {
        button.setAttribute('aria-pressed', String(button.dataset.system === locked))
        button.classList.toggle('is-preview', button.dataset.system === activeSystem && uniform)
      }
      const label = systems[activeSystem][2]
      if (label !== lastLabel) {
        status.textContent = label
        window.dispatchEvent(new CustomEvent('sitewise:system', { detail: { label: frame.label, color: activeSystem === 'all' ? '#FFFFFF' : '#087ac9' } }))
        lastLabel = label
      }
      occupiedLighting.apply(nightAmount, frame.houses.every(h => h.amount < .001 || h.discipline === 'architecture'))
    }
    function select(active: System) {
      if (active === 'all') {
        display(initialDwellingFrame())
        render()
        return
      }
      const state = { discipline: active, amount: 1 }
      display({ label: systems[active][0], houses: Array.from({ length: 5 }, () => state), shared: state })
      render()
    }
    for (const button of buttons) {
      button.disabled = false
      const system = button.dataset.system as System
      button.addEventListener('click', () => { locked = locked === system ? 'all' : system; select(locked) })
    }
    const layers = host.querySelector<HTMLDetailsElement>('.sw-model-explore')
    host.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return
      if (layers?.open) {
        layers.open = false
        layers.querySelector<HTMLElement>('summary')?.focus()
      } else {
        locked = 'all'
        select(locked)
      }
    })
    controls.addEventListener('change', render)
    mountSceneMotion({host,camera,controls,render,
      garage: progress => { if (activeSystem === 'all') garage(progress) },
      ambient: elapsed => { if (activeSystem === 'all') rotors(elapsed) },
    })
    const views = [...host.querySelectorAll<HTMLButtonElement>('[data-camera-view]')]
    const directions: Record<string, [number, number, number]> = {
      top: [0, 46, .001], front: frontDirection(), side: [0, 0, 46], rear: [46, 0, 0], perspective: [-31, 22, 31],
    }
    for (const button of views) {
      button.disabled = false
      button.addEventListener('click', () => {
        if (button.getAttribute('aria-pressed') === 'true') return
        const view = button.dataset.cameraView!
        controls.maxPolarAngle = Math.PI / 2
        controls.target.set(0, 3, 3)
        // The row follows world Z; +Z contains the road and reads to the right.
        camera.up.set(view === 'top' ? 1 : 0, view === 'top' ? 0 : 1, 0)
        camera.position.copy(controls.target).add(new THREE.Vector3(...directions[view]))
        controls.update()
        views.forEach(b => b.setAttribute('aria-pressed', String(b === button)))
        render()
      })
    }
    controls.addEventListener('start', () => views.forEach(b => b.setAttribute('aria-pressed', 'false')))
    const sun = host.querySelector<HTMLInputElement>('[data-sun-time]')!
    const time = host.querySelector<HTMLOutputElement>('[data-sun-label]')!
    function updateSun() {
      const hour = Number(sun?.value ?? 14)
      const angle = (hour - 6) / 12 * Math.PI
      const elevation = Math.max(0, Math.sin(angle))
      nightAmount = 1 - THREE.MathUtils.smoothstep(elevation, 0, .22)
      key.position.set(Math.cos(angle) * 48, Math.max(2, elevation * 52), -25)
      key.intensity = .15 + elevation * 3.4
      key.color.set('#FFFFFF')
      sky.intensity = .10 + elevation * .14
      fill.intensity = .06
      scene.environmentIntensity = .02 + elevation * .05
      occupiedLighting.apply(nightAmount, activeSystem === 'all' || activeSystem === 'architecture')
      const minutes = Math.round(hour * 60)
      const label = `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
      if (time) time.value = label
      sun?.setAttribute('aria-valuetext', label)
      render()
    }
    if (sun) {
      sun.disabled = false
      sun.addEventListener('input', updateSun)
    }
    updateSun()
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(viewport)
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; render() })
    observer.observe(host)
    document.addEventListener('visibilitychange', render)
    window.addEventListener('pagehide', () => {
      disposeWheelZoom()
      resizeObserver.disconnect(); observer.disconnect(); occupiedLighting.dispose(); controls.dispose(); renderer.dispose()
      for (const part of parts) { part.mesh.geometry.dispose(); part.material.dispose(); part.original.dispose() }
      outlines.children.forEach(line => (line as THREE.LineSegments).geometry.dispose())
      outlineMaterials.forEach(material => material.dispose())
      reveal.dispose()
      environment.dispose()
    }, { once: true })
    resize()
    select('all')
    render()
  } catch (error) {
    console.error('Coordination model failed to load', error)
    status.textContent = 'The model could not load. Reload the page to try again.'
    controls.dispose()
    decoder.dispose()
    renderer.dispose()
  }
}
const host = document.querySelector<HTMLElement>('.sw-coordination-model')
if (host) void start(host)
