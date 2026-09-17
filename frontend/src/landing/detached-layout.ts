/** Dimensions in metres, transcribed from L09 CC Plans sheets 2–8. */
export const detachedLayout = {
  count: 4, cutaway: 3, lotWidth: 11.65, lotDepth: 26.002,
  width: 9.23, depth: 15.72, frontSetback: 4.5,
  ground: .31, garage: .224, upper: 3.38, ceiling: 5.83, ridge: 7.881,
  areas: { ground: 82.77, upper: 92.43, garage: 33.18, alfresco: 10.69, balcony: 3.18, porch: 3.59 },
} as const

export type HouseRoom = { name: string; floor: number; x: number; depth: number; width: number; length: number; wet?: boolean }
// X runs left-to-right when facing the house; depth runs away from the street.
export const detachedRooms: HouseRoom[] = [
  { name: 'Multi', floor: 0, x: .24, depth: 1.24, width: 3.11, length: 3.67 },
  { name: 'Garage', floor: 0, x: 3.35, depth: 1.36, width: 5.64, length: 5.5 },
  { name: 'Stairs', floor: 0, x: .24, depth: 4.44, width: 2.09, length: 2.9 },
  { name: 'Laundry', floor: 0, x: .24, depth: 7.43, width: 2.08, length: 1.83, wet: true },
  { name: 'Dining', floor: 0, x: .24, depth: 9.35, width: 3.11, length: 3.41 },
  { name: 'WC', floor: 0, x: 5.45, depth: 7.09, width: 1.77, length: 1.24, wet: true },
  { name: 'Kitchen', floor: 0, x: 3.6, depth: 8.42, width: 3.47, length: 3.49 },
  { name: 'Walk-in pantry', floor: 0, x: 7.16, depth: 7.09, width: 1.83, length: 2.44 },
  { name: 'Family', floor: 0, x: 3.6, depth: 11.99, width: 4.07, length: 3.49 },
  { name: 'Bed 1', floor: 1, x: .15, depth: 1.11, width: 3.78, length: 4.76 },
  { name: 'Ensuite', floor: 1, x: 5.1, depth: 1.11, width: 2.75, length: 2.8, wet: true },
  { name: 'Walk-in robe', floor: 1, x: 4.02, depth: 1.11, width: .99, length: 2.8 },
  { name: 'Bed 2', floor: 1, x: 4.53, depth: 4.0, width: 3.32, length: 3.0 },
  { name: 'Sitting', floor: 1, x: .15, depth: 7.32, width: 3.78, length: 2.15 },
  { name: 'Bath', floor: 1, x: 4.53, depth: 7.09, width: 3.32, length: 2.19, wet: true },
  { name: 'Bed 3', floor: 1, x: .15, depth: 9.56, width: 3.78, length: 3.0 },
  { name: 'Bed 4', floor: 1, x: 4.53, depth: 9.37, width: 3.32, length: 3.01 },
]

export const detachedFacades = [
  { name: 'Weatherboard pair', windows: 2, finish: 'cladding', slats: false, railSpacing: .16, railWidth: .025, entryFins: 0, brickBase: .65, fascia: 'plain', letterbox: 'pillar' },
  { name: 'Fine battens', windows: 3, finish: 'cladding', slats: true, railSpacing: .10, railWidth: .035, entryFins: 3, brickBase: .85, fascia: 'framed', letterbox: 'slot' },
  { name: 'Rendered pair', windows: 2, finish: 'render', slats: false, railSpacing: .20, railWidth: .035, entryFins: 0, brickBase: .30, fascia: 'double', letterbox: 'pier' },
  { name: 'Masonry base', windows: 3, finish: 'render', slats: false, railSpacing: .13, railWidth: .02, entryFins: 2, brickBase: .95, fascia: 'framed', letterbox: 'wide' },
] as const
