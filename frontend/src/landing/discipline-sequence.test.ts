import { expect, it } from 'vitest'
import { createSequenceClock, disciplines, sequenceDuration, sequenceFrame } from './discipline-sequence'

it('switches all houses together and holds each discipline for two seconds', () => {
  expect(sequenceFrame(.99).houses.every(h => h.amount === 0)).toBe(true)
  const stages = [...disciplines, 'civil', 'landscape']
  stages.forEach((discipline, i) => {
    for (const time of [1 + i * 2, 2.99 + i * 2]) {
      const frame = sequenceFrame(time)
      expect([...frame.houses, frame.shared].every(h => h.discipline === discipline && h.amount === 1)).toBe(true)
    }
  })
  expect(sequenceFrame(sequenceDuration)).toEqual(sequenceFrame(0))
})

it('cuts directly between disciplines without intermediate whole-model or blended frames', () => {
  for (let time = 1; time < sequenceDuration; time += .017) {
    const frame = sequenceFrame(time)
    const slots = [...frame.houses, frame.shared]
    expect(new Set(slots.map(h => h.discipline)).size).toBe(1)
    expect(slots.every(h => h.amount === 1 && h.discipline !== 'all')).toBe(true)
  }
})

it('waits for interaction to end and six seconds of idle time before restarting', () => {
  const clock = createSequenceClock()
  expect(clock.tick(1.1)?.houses[0].amount).toBe(1)
  clock.hold('orbit')
  expect(clock.tick(20)).toBeNull()
  clock.release('orbit')
  expect(clock.tick(5)).toBeNull()
  expect(clock.tick(1)).toBeNull()
  expect(clock.tick(.1)?.label).toBe('Whole project')
  clock.interact()
  expect(clock.tick(1)).toBeNull()
  clock.reset()
  expect(clock.tick(0)?.label).toBe('Whole project')
})
