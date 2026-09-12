import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { mountSceneMotion } from './scene-motion'
import { createGarageMotion } from './garage-motion'
import { createRotors } from './rotor-motion'
import { createNightLighting } from './night-lighting'

const systems = {
  all: ['Whole project', '#F7F7F4', 'Drag to orbit · Scroll or pinch to zoom'],
  architecture: ['Architecture', '#F7F7F4', 'Envelope, rooms and glazing'],
  structure: ['Structure', '#D3B793', 'Perimeter strip footing · Roof bearing beams · Eight evenly spaced trusses'],
  electrical: ['Electrical', '#F38F78', 'Three lighting circuits · Three GPO circuits · Room switches · Dedicated appliances'],
  mechanical: ['Mechanical', '#DEDF88', 'Two upper-floor supplies · Two lower-floor drops · Outdoor condenser'],
  hydraulic: ['Hydraulic', '#93CEDD', 'Potable water supply · Sanitary drainage'],
  civil: ['Civil', '#CAD3D4', 'Stormwater pits · Five house connections · Detention tank · One road outlet'],
  landscape: ['Landscape', '#9FC79B', 'Rear pergolas · Breakfast terraces · Trees and layered planting'],
  interiors: ['Interiors', '#D6A986', 'Furniture, kitchen joinery and interior fittings'],
} as const
type System = keyof typeof systems
type Part = { mesh: THREE.Mesh; material: THREE.MeshStandardMaterial; original: THREE.MeshStandardMaterial; system: string; memberships: string[]; glass: boolean }

async function start(host: HTMLElement) {
  const viewport = host.querySelector<HTMLElement>('.sw-scene-viewport')!
  const status = host.querySelector<HTMLElement>('[data-scene-status]')!
  const buttons = [...host.querySelectorAll<HTMLButtonElement>('[data-system]')]
  let renderer: THREE.WebGLRenderer
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, logarithmicDepthBuffer: true })
  } catch {
    status.textContent = '3D is unavailable on this device. Showing the project image.'
    return
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75))
  renderer.setClearColor('#071c39')
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = .88
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  const scene = new THREE.Scene()
  scene.fog = new THREE.Fog('#071c39', 100, 320)
  const camera = new THREE.OrthographicCamera(-30, 30, 30, -30, .1, 1000)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enablePan = false
  controls.enableZoom = true
  controls.zoomSpeed = .7
  controls.minDistance = 10
  controls.maxDistance = 110
  controls.minZoom = .5
  controls.maxZoom = 5
  controls.maxPolarAngle = Math.PI * .49
  const sky = new THREE.HemisphereLight('#F5F6F7', '#30343A', .65)
  scene.add(sky)
  const key = new THREE.DirectionalLight('#FFFFFF', 2.4)
  key.position.set(-32, 28, -18)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -36, right: 36, top: 36, bottom: -36, near: 1, far: 130 })
  key.shadow.bias = -.0002
  key.shadow.normalBias = .03
  scene.add(key)
  const fill = new THREE.DirectionalLight('#F0F3F6', .25)
  fill.position.set(20, 20, -25)
  scene.add(fill)
  let visible = true
  const render = () => { if (visible && !document.hidden) renderer.render(scene, camera) }
  function resize() {
    const { width, height } = viewport.getBoundingClientRect()
    if (!width || !height) return
    const halfHeight = Math.max(28, 28 * height / width)
    camera.left = -halfHeight * width / height
    camera.right = halfHeight * width / height
    camera.top = halfHeight
    camera.bottom = -halfHeight
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    render()
  }
  function frame() {
    camera.position.set(-49, 29, 49)
    controls.target.set(0, 1, 3)
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
      if (/Petrol[ _]ground/i.test(object.name)) material.color.set('#102c51')
      object.material = material
      const system = String(object.userData.sw_system ?? 'architecture')
      if (system !== 'context' && object.userData.sw_motion !== 'car' && !/^(Facade|Garden) \|/.test(original.name)) {
        material.color.set('#F7F7F4')
      }
      const associations: unknown = JSON.parse(String(object.userData.sw_service_systems ?? '[]'))
      const memberships = [system, ...(Array.isArray(associations) ? associations.filter((s): s is string => typeof s === 'string') : [])]
      const glass = Boolean(object.userData.sw_glass)
      object.castShadow = !glass && system !== 'context'
      object.receiveShadow = !glass
      if (glass) { material.transparent = true; material.opacity = .13; material.depthWrite = false }
      parts.push({ mesh: object, material, original: material.clone(), system, memberships, glass })
    })
    scene.add(gltf.scene)
    const outlines = new THREE.Group()
    const outlineMaterial = new THREE.LineBasicMaterial({ color: '#a9b1ba', transparent: true, opacity: .035, depthWrite: false })
    // Only the building envelopes provide context; tile and joinery edges overwhelm services.
    for (const [south, north] of [[-13.764,-9.193],[-6.993,-2.423],[-2.309,2.262],[4.462,9.032],[9.146,13.717]]) {
      const points: THREE.Vector3[] = []
      const edge = (a: number[], b: number[]) => points.push(new THREE.Vector3(...a), new THREE.Vector3(...b))
      for (const z of [-south,-north]) {
        edge([-4.8,0,z],[-4.8,8.45,z]); edge([4.7,0,z],[4.7,8.45,z])
        edge([-4.8,8.45,z],[.18,9.6,z]); edge([.18,9.6,z],[4.7,8.45,z])
        edge([-4.8,0,z],[4.7,0,z])
      }
      for (const [x,y] of [[-4.8,0],[4.7,0],[-4.8,8.45],[4.7,8.45],[.18,9.6]]) edge([x,y,-south],[x,y,-north])
      outlines.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(points), outlineMaterial))
    }
    scene.add(outlines)
    viewport.append(renderer.domElement)
    renderer.domElement.setAttribute('aria-label', 'Interactive development model. Drag to orbit, scroll or pinch to zoom.')
    renderer.domElement.setAttribute('role', 'img')
    host.classList.add('is-live')
    let locked: System = 'all'
    let nightAmount = 0
    let activeSystem: System = 'all'
    function select(active: System) {
      activeSystem = active
      outlines.visible = active !== 'all' && active !== 'architecture'
      for (const part of parts) {
        const { material, original, mesh } = part
        material.copy(original)
        const selected = part.memberships.includes(active)
        mesh.visible = active === 'all' || selected || part.system === 'context'
        mesh.castShadow = (active === 'all' || selected) && !part.glass && part.system !== 'context'
        mesh.receiveShadow = (active === 'all' || selected) && !part.glass
        if (active !== 'all') {
          material.transparent = !selected || part.glass
          material.opacity = selected ? (part.glass ? .3 : 1) : .003
          material.depthWrite = selected && !part.glass
          if (selected) {
            if (active !== 'architecture') material.color.set(systems[active][1])
            material.emissive.set(systems[active][1])
            material.emissiveIntensity = active === 'architecture' ? 0 : .04
          }
        }
        mesh.renderOrder = selected ? 2 : 0
        if (active === 'civil' && mesh.userData.sw_civil_surface) {
          material.transparent = true
          mesh.visible = false
          material.opacity = .12
          material.depthWrite = false
          mesh.castShadow = false
          mesh.receiveShadow = false
          mesh.renderOrder = 0
        }
        material.needsUpdate = true
      }
      for (const button of buttons) {
        button.setAttribute('aria-pressed', String(button.dataset.system === locked))
        button.classList.toggle('is-preview', button.dataset.system === active)
      }
      host.dataset.activeSystem = active
      window.dispatchEvent(new CustomEvent('sitewise:system', { detail: { label: systems[active][0], color: systems[active][1] } }))
      status.textContent = systems[active][2]
      occupiedLighting.apply(nightAmount, active === 'all' || active === 'architecture')
      render()
    }
    for (const button of buttons) {
      button.disabled = false
      const system = button.dataset.system as System
      button.addEventListener('pointerenter', event => { if (event.pointerType === 'mouse') select(system) })
      button.addEventListener('pointerleave', () => select(locked))
      button.addEventListener('focus', () => select(system))
      button.addEventListener('blur', () => select(locked))
      button.addEventListener('click', () => { locked = system; select(locked) })
    }
    host.addEventListener('keydown', event => { if (event.key === 'Escape') { locked = 'all'; select(locked) } })
    controls.addEventListener('change', render)
    const garage = createGarageMotion(parts)
    const ambient = createRotors(parts)
    const occupiedLighting = createNightLighting(scene, parts)
    mountSceneMotion({host,camera,controls,render,garage,ambient})
    const views = [...host.querySelectorAll<HTMLButtonElement>('[data-camera-view]')]
    const directions: Record<string, [number, number, number]> = {
      top: [0, 70, .001], front: [-70, 0, 0], side: [0, 0, 70], rear: [70, 0, 0], isometric: [-49, 35, 49],
    }
    for (const button of views) {
      button.disabled = false
      button.addEventListener('click', () => {
        const view = button.dataset.cameraView!
        controls.maxPolarAngle = Math.PI / 2
        controls.target.set(0, 3, 3)
        camera.up.set(0, 1, 0)
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
      const hour = Number(sun.value)
      const angle = (hour - 6) / 12 * Math.PI
      const elevation = Math.max(0, Math.sin(angle))
      nightAmount = 1 - THREE.MathUtils.smoothstep(elevation, 0, .22)
      key.position.set(Math.cos(angle) * 48, Math.max(2, elevation * 52), -25)
      key.intensity = .15 + elevation * 2.15
      key.color.set('#F1ECE6').lerp(new THREE.Color('#FFFFFF'), elevation)
      sky.intensity = .38 + elevation * .35
      fill.intensity = .18
      occupiedLighting.apply(nightAmount, activeSystem === 'all' || activeSystem === 'architecture')
      const minutes = Math.round(hour * 60)
      time.value = `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
      sun.setAttribute('aria-valuetext', time.value)
      render()
    }
    sun.disabled = false
    sun.addEventListener('input', updateSun)
    updateSun()
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(viewport)
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; render() })
    observer.observe(host)
    document.addEventListener('visibilitychange', render)
    window.addEventListener('pagehide', () => {
      resizeObserver.disconnect(); observer.disconnect(); occupiedLighting.dispose(); controls.dispose(); renderer.dispose()
      for (const part of parts) { part.mesh.geometry.dispose(); part.material.dispose(); part.original.dispose() }
      outlines.children.forEach(line => (line as THREE.LineSegments).geometry.dispose())
      outlineMaterial.dispose()
    }, { once: true })
    resize()
    select('all')
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
