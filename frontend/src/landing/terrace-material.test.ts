import { expect, it } from 'vitest'
import { terracePartAppearance } from './terrace-material'

it('opens only the selected envelope, retaining its interiors and every service', () => {
  expect(terracePartAppearance('architecture', 5, 'all').visible).toBe(false)
  for (const system of ['structure', 'interiors', 'electrical', 'mechanical', 'hydraulic', 'civil', 'landscape']) {
    expect(terracePartAppearance(system, 5, 'all')).toEqual({ visible: true, colour: '#087ac9' })
  }
  for (const dwelling of [0, 1, 2, 3, 4, 6, 7]) {
    expect(terracePartAppearance('architecture', dwelling, 'all')).toEqual({ visible: true, colour: '#FFFFFF' })
  }
})

it('allows architecture inspection and restores the cutaway after layer inspection', () => {
  expect(terracePartAppearance('architecture', 5, 'architecture').visible).toBe(true)
  expect(terracePartAppearance('interiors', 5, 'structure').visible).toBe(false)
  expect(terracePartAppearance('architecture', 5, 'all').visible).toBe(false)
})

it('previews only townhouse five and preserves the surrounding full models', () => {
  for (const dwelling of [0, 1, 2, 3, 4, 6, 7]) {
    expect(terracePartAppearance('architecture', dwelling, 'electrical', true).visible).toBe(true)
    expect(terracePartAppearance('interiors', dwelling, 'electrical', true).visible).toBe(true)
  }
  expect(terracePartAppearance('structure', 5, 'electrical', true).visible).toBe(false)
  expect(terracePartAppearance('electrical', 5, 'electrical', true).visible).toBe(true)
  expect(terracePartAppearance('architecture', 2, 'electrical').visible).toBe(false)
  expect(terracePartAppearance('architecture', 2, 'all').visible).toBe(true)
})

it('previews every townhouse when a filter is already clicked', () => {
  expect(terracePartAppearance('structure', 2, 'hydraulic', true, 'structure').visible).toBe(false)
  expect(terracePartAppearance('hydraulic', 2, 'hydraulic', true, 'structure').visible).toBe(true)
  expect(terracePartAppearance('hydraulic', 5, 'hydraulic', true, 'structure').visible).toBe(true)
  expect(terracePartAppearance('civil', 0, 'hydraulic', false, 'all', ['civil', 'hydraulic']).visible).toBe(true)
})
