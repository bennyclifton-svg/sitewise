import * as THREE from 'three'
import { createResidentialPreview } from './residential-preview'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { batchTerrace } from './terrace-batching'
import { addTelecomAndSolar } from './terrace-energy'
import { addTerraceFoundations } from './terrace-foundations'
import { createTerracePlinth } from './terrace-plinth'
import { addBuildingServices } from './terrace-services'
import { addStreet, varyTrees } from './terrace-street'
import { addAnimatedDetails, mountTerraceAnimation } from './terrace-animation'
import { applyTerraceLife } from './terrace-life'
import { terraceDistance } from './terrace-framing'
import { prepareTerraceMaterial, terracePartAppearance } from './terrace-material'
import { mountModelWheelZoom } from './model-wheel-zoom'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
const systems = {
  all: ['Whole project', '#F7F7F4', 'Drag to orbit · Scroll inside the viewfinder to zoom, elsewhere to explore the page'],
  architecture: ['Architecture', '#F7F7F4', 'Envelope, rooms and glazing'],
  structure: ['Structure', '#D3B793', 'Seven townhouses · Concrete frames · Strip footings · Raked roof framing'],
  electrical: ['Electrical', '#F38F78', 'Seven townhouses · Lighting and GPO circuits · Room switches · Dedicated appliances'],
  mechanical: ['Mechanical', '#DEDF88', 'Seven townhouses · Supply ducts · Extract ventilation · Individual condensers'],
  hydraulic: ['Hydraulic', '#93CEDD', 'Seven townhouses · Hot and cold water · Sanitary drainage · Shared site connections'],
  civil: ['Civil', '#CAD3D4', 'Stormwater pits · Seven house connections · Detention tank · One road outlet'],
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
    || (system === 'civil' && /Road[ _]asphalt/i.test(name))
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
  renderer.shadowMap.autoUpdate = false
  renderer.shadowMap.needsUpdate = true
  renderer.localClippingEnabled = true
  const scene = new THREE.Scene()
  scene.fog = null
  const studio = new RoomEnvironment()
  const pmrem = new THREE.PMREMGenerator(renderer)
  const environment = pmrem.fromScene(studio, .06)
  scene.environment = environment.texture
  scene.environmentIntensity = .04
  studio.dispose(); pmrem.dispose()
  const camera = new THREE.PerspectiveCamera(42, 1, .1, 1000)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enablePan = false
  controls.enableZoom = false
  controls.zoomSpeed = .7
  controls.minDistance = 10
  controls.maxDistance = 300
  controls.minZoom = .5
  controls.maxZoom = 5
  controls.maxPolarAngle = Math.PI * .49
  const sky = new THREE.HemisphereLight('#FFFFFF', '#292929', .13)
  scene.add(sky)
  const key = new THREE.DirectionalLight('#FFFFFF', 3.8)
  key.position.set(-32, 28, -18)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -36, right: 36, top: 36, bottom: -36, near: 1, far: 130 })
  key.shadow.bias = -.0002
  key.shadow.normalBias = .06
  scene.add(key)
  const fill = new THREE.DirectionalLight('#FFFFFF', .06)
  fill.position.set(20, 20, -25)
  scene.add(fill)
  const modelBounds = new THREE.Box3()
  const modelCentre = new THREE.Vector3(24.5, 4, -5)
  let activeView = 'front'
  let visible = true
  const render = () => {
    if (!visible || document.hidden) return
    renderer.render(scene, camera)
    host.dataset.drawCalls = String(renderer.info.render.calls)
    host.dataset.triangles = String(renderer.info.render.triangles)
  }
  function resize() {
    const { width, height } = viewport.getBoundingClientRect()
    if (!width || !height) return
    camera.aspect = width / height
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(9)) * Math.max(1, height / width)))
    camera.clearViewOffset()
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    if (activeView) frameView(activeView)
    render()
  }
  function frameView(view: string) {
    const direction = new THREE.Vector3(...({
      front: [0, .15, 1], rear: [0, .36, -1], side: [1, .3, 0],
      top: [0, 1, .001], perspective: [.48, .32, 1],
    } as Record<string, [number, number, number]>)[view]).normalize()
    camera.up.set(0, view === 'top' ? 0 : 1, view === 'top' ? -1 : 0)
    const masthead = document.querySelector<HTMLElement>('.sw-masthead')
    const margin = masthead ? parseFloat(getComputedStyle(masthead).paddingLeft) : 24
    const widthFraction = Math.min(.94, (1 - 2 * margin / viewport.clientWidth) * 1.1)
    const distance = terraceDistance(modelBounds, modelCentre, direction, camera.up, camera.fov, camera.aspect, window.innerWidth >= 800, widthFraction)
    controls.target.copy(modelCentre)
    camera.position.copy(modelCentre).addScaledVector(direction, distance)
    controls.update()
  }
  frameView('front')
  status.textContent = 'Loading the coordinated project…'
  const decoder = new DRACOLoader().setDecoderPath(new URL(/* @vite-ignore */ './draco/', import.meta.url).href)
  try {
    const loader = new GLTFLoader().setDRACOLoader(decoder)
    const [gltf, car] = await Promise.all([
      loader.loadAsync(new URL(/* @vite-ignore */ './terrace-7.glb', import.meta.url).href),
      loader.loadAsync(new URL(/* @vite-ignore */ './terrace-car.glb', import.meta.url).href),
    ])
    decoder.dispose()
    const residentialCar = car.scene.clone(true)
    applyTerraceLife(gltf.scene, car.scene)
    varyTrees(gltf.scene)
    addTerraceFoundations(gltf.scene)
    addBuildingServices(gltf.scene)
    addStreet(gltf.scene)
    addTelecomAndSolar(gltf.scene)
    addAnimatedDetails(gltf.scene)
    const batching = batchTerrace(gltf.scene, isSiteBackdrop)
    host.dataset.meshesBefore = String(batching.before)
    host.dataset.meshesAfter = String(batching.after)
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
      prepareTerraceMaterial(material)
      const associations: unknown = JSON.parse(String(object.userData.sw_service_systems ?? '[]'))
      const memberships = [system, ...(Array.isArray(associations) ? associations.filter((s): s is string => typeof s === 'string') : [])]
      const glass = Boolean(object.userData.sw_glass) || original.name === 'Glazing'
      object.castShadow = !glass && !backdrop && !object.userData.sw_animatedDetail
      object.receiveShadow = !glass
      if (glass) { material.transparent = true; material.opacity = .13; material.depthWrite = false }
      parts.push({ mesh: object, material, original: material.clone(), system, memberships, glass, backdrop })
    })
    scene.add(gltf.scene)
    const plinth = createTerracePlinth()
    gltf.scene.add(plinth)
    // Buried mains extend beyond the footpath; conceal them without enlarging the site.
    const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), .025)
    const footpathEdges = [
      new THREE.Plane(new THREE.Vector3(1, 0, 0), 2.32),
      new THREE.Plane(new THREE.Vector3(-1, 0, 0), 51.32),
    ]
    // Exclude the removed street block from the fit as well as the rendering.
    for (const part of parts) {
      if (!part.backdrop && part.mesh.userData.sw_fit !== false) modelBounds.union(new THREE.Box3().setFromObject(part.mesh))
    }
    modelBounds.union(new THREE.Box3().setFromObject(plinth))
    modelBounds.getCenter(modelCentre)
    key.position.copy(modelCentre).add(new THREE.Vector3(-25, 40, 35))
    key.target.position.copy(modelCentre)
    scene.add(key.target)
    fill.position.copy(modelCentre).add(new THREE.Vector3(30, 20, -20))
    const terraceBounds = modelBounds.clone()
    const terraceMeshes = parts.filter(part => !part.backdrop).map(part => part.mesh)
    const viewfinder = host.querySelector<HTMLElement>('.sw-model-viewfinder')
    let disposeWheelZoom = mountModelWheelZoom(renderer.domElement, camera, controls, terraceMeshes, viewfinder)
    let residential: ReturnType<typeof createResidentialPreview> | undefined
    let activeModel = 'multi-res'
    host.dataset.activeModel = activeModel
    viewport.append(renderer.domElement)
    renderer.domElement.setAttribute('aria-label', 'Interactive development model. Drag to orbit. Scroll inside the viewfinder to zoom; scroll outside it to move down the page.')
    renderer.domElement.setAttribute('role', 'img')
    host.classList.add('is-live')
    let locked: System = 'all'
    function select(active: System, preview = false) {
      if (activeModel === 'resi') residential?.select(active)
      plinth.visible = activeModel === 'multi-res' && (active === 'all' || (preview && locked === 'all'))
      for (const part of parts) {
        if (part.backdrop) continue
        const edges = part.system === 'civil' && Number(part.mesh.userData.sw_dwelling) === 0 ? footpathEdges : []
        part.material.clippingPlanes = plinth.visible ? [groundPlane, ...edges] : edges
        part.material.clipShadows = true
        const appearance = terracePartAppearance(part.system, Number(part.mesh.userData.sw_dwelling), active, preview, locked, part.memberships)
        const basePreview = preview && locked === 'all' && Number(part.mesh.userData.sw_dwelling) !== 5
        part.mesh.visible = appearance.visible && !(part.mesh.userData.sw_contextOnly && active !== 'all' && !basePreview)
        part.material.color.set(String(part.mesh.userData.sw_colour ?? appearance.colour))
      }
      gltf.scene.traverse(object => { if (object instanceof THREE.Light) object.visible = preview || active === 'all' || active === 'electrical' })
      renderer.shadowMap.needsUpdate = true
      host.dataset.activeSystem = active
      host.dataset.filterScope = activeModel === 'multi-res' && preview && locked === 'all' ? 'townhouse-five' : 'whole-project'
      host.dataset.tourState = 'manual'
      for (const button of buttons) {
        button.setAttribute('aria-pressed', String(button.dataset.system === locked))
        button.classList.toggle('is-preview', button.dataset.system === active)
      }
      status.textContent = active === 'all'
        ? activeModel === 'resi' ? 'Four detached houses. The third house opens to reveal its blue structure, interiors and building services.' : 'Seven terraces. The fifth terrace opens to reveal its blue structure, interiors and building services. Drag to orbit; scroll inside the viewfinder to zoom.'
        : activeModel === 'resi' ? `Four detached houses · ${systems[active][0]}` : systems[active][2]
      window.dispatchEvent(new CustomEvent('sitewise:system', { detail: { label: systems[active][0], color: active === 'all' ? '#FFFFFF' : '#087ac9' } }))
      render()
    }
    const modelButtons = [...host.querySelectorAll<HTMLButtonElement>('[data-model]')]
    for (const button of modelButtons) {
      if (button.dataset.model === 'industrial') continue
      button.disabled = false
      button.addEventListener('click', () => {
        const next = button.dataset.model!
        if (next === activeModel) return
        if (next === 'resi' && !residential) {
          residential = createResidentialPreview(residentialCar)
          scene.add(residential.root)
        }
        activeModel = next
        key.intensity = next === 'resi' ? 3 : 3.8
        sky.intensity = next === 'resi' ? .20 : .13
        fill.intensity = next === 'resi' ? .12 : .06
        scene.environmentIntensity = next === 'resi' ? .07 : .04
        host.dataset.activeModel = next
        gltf.scene.visible = next === 'multi-res'
        if (residential) residential.root.visible = next === 'resi'
        modelBounds.copy(next === 'resi' ? residential!.bounds : terraceBounds)
        modelBounds.getCenter(modelCentre)
        disposeWheelZoom()
        disposeWheelZoom = mountModelWheelZoom(renderer.domElement, camera, controls, next === 'resi' ? residential!.meshes : terraceMeshes, viewfinder)
        locked = 'all'
        activeView = 'front'
        frameView(activeView)
        modelButtons.forEach(item => item.setAttribute('aria-pressed', String(item.dataset.model === next)))
        renderer.domElement.setAttribute('aria-label', next === 'resi' ? 'Four detached houses. Third house is a blue cutaway. Drag to orbit and scroll to zoom.' : 'Seven terraces. Fifth terrace is a blue cutaway. Drag to orbit and scroll to zoom.')
        select('all')
      })
    }
    for (const button of buttons) {
      button.disabled = false
      const system = button.dataset.system as System
      button.addEventListener('pointerenter', event => { if (event.pointerType !== 'touch') select(system, true) })
      button.addEventListener('pointerleave', () => select(locked))
      button.addEventListener('focus', () => select(system, true))
      button.addEventListener('blur', () => select(locked))
      button.addEventListener('click', () => { locked = locked === system ? 'all' : system; select(locked) })
    }
    host.addEventListener('keydown', event => {
      if (event.key === 'Escape') { locked = 'all'; select(locked) }
    })
    controls.addEventListener('change', render)
    controls.addEventListener('start', () => { activeView = '' })
    const focusProject = () => {
      activeView = 'front'
      frameView(activeView)
      render()
    }
    window.addEventListener('sitewise:project-focus', focusProject)
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(viewport)
    const disposeAnimation = mountTerraceAnimation(gltf.scene, host, render, () => { renderer.shadowMap.needsUpdate = true })
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; render() })
    observer.observe(host)
    document.addEventListener('visibilitychange', render)
    window.addEventListener('pagehide', () => {
      window.removeEventListener('sitewise:project-focus', focusProject)
      residential?.dispose()
      disposeAnimation()
      disposeWheelZoom()
      resizeObserver.disconnect(); observer.disconnect(); controls.dispose(); renderer.dispose()
      for (const part of parts) { part.mesh.geometry.dispose(); part.material.dispose(); part.original.dispose() }
      plinth.traverse(object => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose()
          ;(object.material as THREE.Material).dispose()
        }
      })
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

