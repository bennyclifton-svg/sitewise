import * as THREE from 'three'
import type { SequenceFrame, Reveal } from './discipline-sequence'

const exposedSystems = ['structure', 'electrical', 'mechanical', 'hydraulic', 'civil', 'interiors']

export function initialDwellingFrame(): SequenceFrame {
  return {
    label: 'Whole project',
    // House slots run from the closest townhouse to the furthest.
    houses: Array.from({ length: 5 }, (_, i) => ({ discipline: i === 1 ? 'exposed' : 'all', amount: i === 1 ? 1 : 0 })),
    shared: { discipline: 'all', amount: 0 },
  }
}

type Part = { mesh: THREE.Mesh; material: THREE.MeshStandardMaterial; memberships: string[]; backdrop: boolean; glass: boolean }
const vertex = `varying vec3 swRevealPosition;\n`
const fragment = `varying vec3 swRevealPosition;
uniform float swOpacity[6]; uniform float swBlue[6]; uniform vec3 swBlueColour;
int swHouse(){
  float y=-swRevealPosition.z;
  if(abs(swRevealPosition.x)>7.0 || y < -15.4 || y > 15.4) return 5;
  if(y < -8.1085) return 0; if(y < -2.366) return 1;
  if(y < 3.3617) return 2; if(y < 9.0892) return 3; return 4;
}
`
const mask = `
  int house=swHouse();
  float visibility=swOpacity[house];
  if(visibility < .001) discard;
`

export function createDwellingReveal(parts: Part[]) {
  const bindings = parts.filter(p => !p.backdrop).map(part => {
    const opacity = { value: [1, 1, 1, 1, 1, 1] }
    const blue = { value: [0, 0, 0, 0, 0, 0] }
    const landscapeHouse = Number(part.mesh.userData.sw_landscape_dwelling || 0) - 1
    const ownedHouse = Number(part.mesh.userData.sw_reveal_dwelling || 0) - 1
    const revealHouse = ownedHouse >= 0 ? ownedHouse : landscapeHouse
    const dwellingOffset = Number(part.mesh.userData.sw_dwelling_y_offset || 0)
    const attach = (material: THREE.Material, colour: boolean) => {
      const previousKey = material.customProgramCacheKey()
      const previous = material.onBeforeCompile.bind(material)
      material.onBeforeCompile = (shader, renderer) => {
        previous(shader, renderer)
        shader.uniforms.swOpacity = opacity; shader.uniforms.swBlue = blue
        shader.uniforms.swBlueColour = { value: new THREE.Color('#087ac9') }
        shader.vertexShader = vertex + shader.vertexShader
        shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>', '#include <project_vertex>\nswRevealPosition=(modelMatrix*vec4(transformed,1.)).xyz;')
        const houseFragment = revealHouse >= 0
          ? fragment.replace('float y=-swRevealPosition.z;', `return ${revealHouse};\n  float y=-swRevealPosition.z;`)
          : fragment.replace('float y=-swRevealPosition.z;', `float y=-swRevealPosition.z-(${dwellingOffset.toFixed(4)});`)
        shader.fragmentShader = houseFragment + shader.fragmentShader
        shader.fragmentShader = shader.fragmentShader.replace('#include <alphatest_fragment>', '#include <alphatest_fragment>\n' + mask + (colour ? '\ndiffuseColor.rgb=mix(diffuseColor.rgb,swBlueColour,swBlue[house]);' : ''))
      }
      material.customProgramCacheKey = () => `dwelling-reveal-v3-${dwellingOffset}-${revealHouse}-${colour}-${previousKey}`
      material.needsUpdate = true
    }
    attach(part.material, true)
    const depth = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking })
    attach(depth, false); part.mesh.customDepthMaterial = depth
    return { part, opacity, blue, depth, revealHouse }
  })
  return {
    apply(frame: SequenceFrame) {
      const slots = [...frame.houses, frame.shared]
      for (const { part, opacity, blue, revealHouse } of bindings) {
        const siteContext = part.memberships.includes('landscape') || Boolean(part.mesh.userData.sw_civil_surface)
        slots.forEach((state: Reveal, i) => {
          const selected = state.discipline === 'all' || (state.discipline === 'exposed'
            ? part.memberships.some(system => exposedSystems.includes(system))
            : part.memberships.includes(state.discipline))
          opacity.value[i] = siteContext || selected ? 1 : 1 - state.amount
          const exposedLandscape = state.discipline === 'exposed' && revealHouse === i
          const selectedCivilSurface = state.discipline === 'civil' && part.memberships.includes('civil')
          blue.value[i] = exposedLandscape || selectedCivilSurface || (!siteContext && selected && !['all', 'architecture'].includes(state.discipline)) ? state.amount : 0
        })
        part.mesh.visible = opacity.value.some(value => value > .001)
        part.material.depthTest = true
        part.material.depthWrite = !part.glass
        part.mesh.renderOrder = 0
      }
    },
    dispose() { bindings.forEach(binding => binding.depth.dispose()) },
  }
}
