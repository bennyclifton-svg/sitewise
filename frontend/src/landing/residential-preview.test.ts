import { expect, it } from 'vitest'
import { createResidentialPreview } from './residential-preview'
import { detachedLayout } from './detached-layout'

it('filters the residential model and restores the blue cutaway', () => {
  const preview = createResidentialPreview()
  try {
    expect(preview.bounds.isEmpty()).toBe(false)
    preview.select('electrical')
    const visible = preview.meshes.filter(mesh => mesh.visible)
    expect(visible.length).toBeGreaterThan(0)
    expect(visible.every(mesh => mesh.userData.sw_system === 'electrical')).toBe(true)
    preview.select('all')
    expect(preview.meshes.some(mesh => mesh.visible && mesh.userData.sw_system === 'architecture')).toBe(true)
    expect(preview.meshes.filter(mesh => mesh.userData.sw_dwelling === detachedLayout.cutaway && mesh.userData.sw_system === 'architecture').every(mesh => !mesh.visible)).toBe(true)
  } finally {
    preview.dispose()
  }
})
