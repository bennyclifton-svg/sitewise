import * as THREE from 'three'
import { isTerraceBrick, prepareTerraceBrick } from './terrace-brick'

export const cutawayDwelling = 5

/** A white study model keeps the exposed dwelling's blue systems legible. */
export function prepareTerraceMaterial(material: THREE.MeshStandardMaterial) {
  material.color.set('#FFFFFF')
  material.metalness = 0
  material.roughness = .48
  if (isTerraceBrick(material)) prepareTerraceBrick(material)
}

export function terracePartAppearance(system: string, dwelling: number, active: string, preview = false, locked = 'all', memberships = [system]) {
  const cutaway = dwelling === cutawayDwelling
  const effective = preview && locked === 'all' && !cutaway ? 'all' : active
  return {
    visible: effective === 'all' ? !(cutaway && system === 'architecture') : memberships.includes(effective),
    colour: cutaway ? '#087ac9' : '#FFFFFF',
  }
}
