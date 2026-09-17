import { expect, it } from 'vitest'
import { isSiteBackdrop } from './coordination'

it('hides the static cadastral field and earth plane, not the townhouses', () => {
  expect(isSiteBackdrop('context | V3 | Petrol ground', 'context')).toBe(true)
  expect(isSiteBackdrop('V3 | Context earth plane', 'context')).toBe(true)
  expect(isSiteBackdrop('context | V3 | White map lines', 'context')).toBe(true)
  expect(isSiteBackdrop('V3 | Shared cadastral boundaries', 'context')).toBe(true)
  expect(isSiteBackdrop('architecture | Facade | brick', 'architecture')).toBe(false)
  expect(isSiteBackdrop('V3 | RC ground slab 200mm', 'structure')).toBe(false)
  expect(isSiteBackdrop('V3 | Shared driveway', 'civil')).toBe(false)
  expect(isSiteBackdrop('TH00 | civil | body | Road asphalt', 'civil')).toBe(true)
  expect(isSiteBackdrop('TH00_|_civil_|_body_|_Road_asphalt', 'civil')).toBe(true)
  expect(isSiteBackdrop('TH02 | civil | body | Limestone paving', 'civil')).toBe(false)
})
