import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import { createDwellingReveal, initialDwellingFrame } from './dwelling-reveal'

describe('initial exposed townhouse', () => {
  it('keeps owned buried services blue while allowing slabs and ground to occlude them', () => {
    const mesh = new THREE.Mesh()
    mesh.userData.sw_reveal_dwelling = 2
    mesh.userData.sw_underground = true
    const part = { mesh, material: new THREE.MeshStandardMaterial(), memberships: ['electrical'], backdrop: false, glass: false }
    const reveal = createDwellingReveal([part])
    reveal.apply(initialDwellingFrame())
    const shader = { uniforms: {}, vertexShader: '', fragmentShader: '' } as THREE.WebGLProgramParametersWithUniforms
    part.material.onBeforeCompile(shader, {} as THREE.WebGLRenderer)
    expect(shader.fragmentShader).toContain('return 1;')
    expect(shader.uniforms.swBlue.value).toEqual([0, 1, 0, 0, 0, 0])
    expect(part.material.depthTest).toBe(true)
    expect(part.material.depthWrite).toBe(true)
    expect(mesh.renderOrder).toBe(0)
    const frame = initialDwellingFrame()
    frame.houses[1] = { discipline: 'all', amount: 0 }
    reveal.apply(frame)
    expect(part.material.depthTest).toBe(true)
    expect(part.material.depthWrite).toBe(true)
    reveal.dispose()
  })
  it('keeps house selection aligned when the site model moves the dwelling group', () => {
    const mesh = new THREE.Mesh()
    mesh.userData.sw_dwelling_y_offset = -2.5
    const part = { mesh, material: new THREE.MeshStandardMaterial(), memberships: ['structure'], backdrop: false, glass: false }
    const reveal = createDwellingReveal([part])
    const shader = { uniforms: {}, vertexShader: '', fragmentShader: '' } as THREE.WebGLProgramParametersWithUniforms
    part.material.onBeforeCompile(shader, {} as THREE.WebGLRenderer)
    expect(shader.fragmentShader).toContain('float y=-swRevealPosition.z-(-2.5000);')
    expect(part.material.customProgramCacheKey()).toContain('dwelling-reveal-v3--2.5')
    reveal.dispose()
  })
  it('highlights Civil paving while retaining it as context in other disciplines', () => {
    const mesh = new THREE.Mesh()
    mesh.userData.sw_civil_surface = true
    const part = { mesh, material: new THREE.MeshStandardMaterial(), memberships: ['civil'], backdrop: false, glass: false }
    const reveal = createDwellingReveal([part])
    const frame = initialDwellingFrame()
    frame.houses[0] = { discipline: 'civil', amount: 1 }
    frame.houses[2] = { discipline: 'mechanical', amount: 1 }
    frame.shared = { discipline: 'civil', amount: 1 }
    reveal.apply(frame)
    const shader = { uniforms: {}, vertexShader: '', fragmentShader: '' } as THREE.WebGLProgramParametersWithUniforms
    part.material.onBeforeCompile(shader, {} as THREE.WebGLRenderer)
    expect(shader.uniforms.swBlue.value).toEqual([1, 0, 0, 0, 0, 1])
    expect(shader.uniforms.swOpacity.value).toEqual([1, 1, 1, 1, 1, 1])
    reveal.dispose()
  })
  it('colours only the owned rear landscape in the exposed view', () => {
    const parts = [0, 2].map(owner => {
      const mesh = new THREE.Mesh()
      mesh.userData.sw_landscape_dwelling = owner
      return { mesh, material: new THREE.MeshStandardMaterial(), memberships: ['landscape'], backdrop: false, glass: false }
    })
    const reveal = createDwellingReveal(parts)
    reveal.apply(initialDwellingFrame())
    parts.forEach((part, index) => {
      const shader = { uniforms: {}, vertexShader: '', fragmentShader: '' } as THREE.WebGLProgramParametersWithUniforms
      part.material.onBeforeCompile(shader, {} as THREE.WebGLRenderer)
      expect(shader.uniforms.swBlue.value).toEqual([0, index, 0, 0, 0, 0])
      expect(shader.uniforms.swOpacity.value).toEqual([1, 1, 1, 1, 1, 1])
    })
    reveal.dispose()
  })
  it('removes only the second house architecture and keeps its interiors, services and site', () => {
    const systems = ['architecture', 'interiors', 'structure', 'electrical', 'mechanical', 'hydraulic', 'civil', 'landscape']
    const parts = systems.map(system => ({
      mesh: new THREE.Mesh(), material: new THREE.MeshStandardMaterial(),
      memberships: [system], backdrop: false, glass: false,
    }))
    const reveal = createDwellingReveal(parts)
    reveal.apply(initialDwellingFrame())
    parts.forEach((part, index) => {
      const shader = { uniforms: {}, vertexShader: '', fragmentShader: '' } as THREE.WebGLProgramParametersWithUniforms
      part.material.onBeforeCompile(shader, {} as THREE.WebGLRenderer)
      expect(shader.uniforms.swOpacity.value).toEqual([1, index === 0 ? 0 : 1, 1, 1, 1, 1])
      expect(shader.uniforms.swBlue.value).toEqual([0, index > 0 && index < 7 ? 1 : 0, 0, 0, 0, 0])
    })
    reveal.dispose()
  })
})
