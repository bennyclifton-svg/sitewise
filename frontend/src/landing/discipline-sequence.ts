export type Reveal = { discipline: string; amount: number }
export type SequenceFrame = { label: string; houses: Reveal[]; shared: Reveal }
export const disciplines = ['structure', 'electrical', 'mechanical', 'hydraulic', 'interiors']
const all = (): Reveal => ({ discipline: 'all', amount: 0 })
const whole = (): SequenceFrame => ({ label: 'Whole project', houses: Array.from({ length: 5 }, all), shared: all() })
const stages = [...disciplines, 'civil', 'landscape']
const holdSeconds = 2
const wholeSeconds = 1
export const sequenceDuration = wholeSeconds + stages.length * holdSeconds

export function sequenceFrame(seconds: number): SequenceFrame {
  const time = ((seconds % sequenceDuration) + sequenceDuration) % sequenceDuration
  if (time < wholeSeconds) return whole()
  const stage = stages[Math.floor((time - wholeSeconds) / holdSeconds)]
  return {
    label: stage[0].toUpperCase() + stage.slice(1),
    houses: Array.from({ length: 5 }, () => ({ discipline: stage, amount: 1 })),
    shared: { discipline: stage, amount: 1 },
  }
}

/** Time advances only when the existing visible, unpaused scene loop ticks. */
export function createSequenceClock() {
  let time = 0, idle = 0
  const holds = new Set<string>()
  return {
    hold(reason: string) { holds.add(reason); idle = 6; time = 0 },
    release(reason: string) { holds.delete(reason); idle = 6 },
    interact() { idle = 6; time = 0 },
    tick(delta: number) {
      if (holds.size) return null
      if (idle > 0) { idle = Math.max(0, idle - delta); return null }
      time += delta
      return sequenceFrame(time)
    },
    reset() { time = 0; idle = 0; holds.clear() },
  }
}
