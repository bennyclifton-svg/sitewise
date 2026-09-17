import * as THREE from 'three'
import { box, type Point } from './terrace-parts'
import { detachedLayout as layout, detachedFacades } from './detached-layout'

/** Street-facing joinery; kept as architecture so the blue cutaway still opens. */
export function addDetachedFacadeDetails(model: THREE.Group, house: number) {
  const variant = detachedFacades[house - 1], gf = layout.ground, ff = layout.upper
  const detail = (name: string, size: Point, at: Point, finish = 'White study model') => {
    const mesh = box(model, size, at, 'architecture', house)
    mesh.name = name
    ;(mesh.material as THREE.Material).name = finish
    return mesh
  }
  const surround = (name: string, left: number, right: number, sill: number, head: number, z: number) => {
    for (const x of [left - .045, right + .045]) detail(`${name} reveal`, [.09, head - sill + .09, .18], [x, (head + sill) / 2, z])
    detail(`${name} head`, [right - left + .18, .09, .20], [(left + right) / 2, head + .045, z + .01])
    detail(`${name} projecting sill`, [right - left + .24, .065, .28], [(left + right) / 2, sill - .035, z + .04])
    detail(`${name} sill drip`, [right - left + .20, .022, .035], [(left + right) / 2, sill - .079, z + .14])
  }

  // Reveal geometry stays outside the clear opening, including the entry threshold.
  surround('Front room window', .38, 1.5, gf + .75, gf + 2.2, -1.045)
  surround('Entry portal', 2.02, 2.94, gf, gf + 2.4, -1.015)
  const starts = variant.windows === 2 ? [4.5, 6.3] : [4.3, 5.65, 7]
  const width = variant.windows === 2 ? .85 : .6
  for (const x of starts) {
    if (house !== 2) surround('Upper window', x, x + width, ff + .6, ff + 2.12, -.865)
    if (house === 1) {
      detail('Weatherboard window hood', [width + .36, .065, .44], [x + width / 2, ff + 2.26, -.72])
      for (const edge of [x - .07, x + width + .07]) detail('Hood bracket', [.045, .18, .24], [edge, ff + 2.14, -.72])
    } else if (house === 3) {
      detail('Continuous window canopy', [width + .28, .10, .52], [x + width / 2, ff + 2.29, -.68])
    } else if (house === 4) {
      detail('Stone window lintel', [width + .36, .18, .24], [x + width / 2, ff + 2.25, -.82], 'Detached stone cladding')
    }
  }

  // Fine soffit boards and a perimeter trim give the porch a finished underside.
  const boardSpacing = [.18, .10, .26, .32][house - 1]
  for (let x = .24; x < 3.4; x += boardSpacing) detail('Porch soffit board', [boardSpacing - .012, .028, .86], [x, ff - .667, -.46])
  for (const x of [.25, 3.34]) detail('Soffit edge trim', [.04, .055, .90], [x, ff - .67, -.46])
  for (const x of [1.05, 2.48]) detail('Recessed porch light', [.12, .012, .12], [x, ff - .688, -.46])
  for (const x of [.14, 3.45]) {
    const capHeight = house === 1 ? ff + 1.02 : house === 4 ? layout.ceiling - .1 : layout.garage + variant.brickBase
    detail('Pier cap with overhang', [.43, .075, .43], [x, capHeight + .02, house === 1 || house === 4 ? 0 : -.12])
    detail('Pier foot course', [.40, .10, .40], [x, .05, house === 1 || house === 4 ? 0 : -.12])
  }
  detail('Balcony drip edge', [3.83, .035, .04], [1.795, ff - .67, .16])

  for (const x of [3.89, 8.82]) detail('Garage deep reveal', [.12, 2.46, .20], [x, layout.garage + 1.23, -1.10])
  detail('Garage head flashing', [5.08, .06, .26], [6.355, layout.garage + 2.45, -1.07])
  // Four joinery patterns replace the repeated sectional-door lines.
  if (house === 1) {
    for (const x of [4.55, 5.75, 6.95, 8.15]) for (const y of [.43, 1.17, 1.91]) {
      for (const dx of [-.49, .49]) detail('Garage shaker stile', [.045, .57, .04], [x + dx, layout.garage + y, -1.20])
      for (const dy of [-.285, .285]) detail('Garage shaker rail', [1.025, .045, .04], [x, layout.garage + y + dy, -1.20])
    }
  } else if (house === 2) {
    for (let x = 4.02; x < 8.72; x += .12) detail('Garage vertical timber slat', [.09, 2.34, .045], [x, layout.garage + 1.19, -1.195])
  } else if (house === 3) {
    for (const y of [.6, 1.2, 1.8]) detail('Garage broad horizontal panel', [4.73, .565, .035], [6.355, layout.garage + y, -1.20])
  } else {
    for (const x of [4.43, 5.39, 6.35, 7.31, 8.27]) detail('Garage flush vertical panel', [.935, 2.34, .035], [x, layout.garage + 1.19, -1.20])
  }

  if (house === 1) {
    for (const y of [.55, 1.55]) for (const x of [2.12, 2.84]) detail('Entry panel stile', [.035, .74, .035], [x, gf + y, -1.09])
    for (const y of [.18, .92, 1.18, 1.92]) detail('Entry panel rail', [.755, .035, .035], [2.48, gf + y, -1.09])
    for (const x of [.37, 3.18]) detail('Balcony post collar', [.22, .085, .22], [x < 1 ? .14 : 3.45, ff + 1.12, 0])
  } else if (house === 2) {
    for (let x = .5; x < 3.2; x += .48) detail('Balcony paired picket', [.035, .96, .045], [x, ff + .53, -.035])
    for (let x = .4; x < 3.3; x += .12) detail('Balcony fascia batten', [.045, .45, .055], [x, ff - .325, .10])
  } else if (house === 3) {
    for (const y of [.34, .65]) detail('Balcony horizontal rail', [3.26, .055, .065], [1.795, ff + y, -.03])
    detail('Balcony floating fascia band', [3.82, .16, .15], [1.795, ff - .31, .14])
    detail('Entry blade canopy', [1.25, .065, .5], [2.48, gf + 2.53, -.86])
  } else {
    for (const x of [.70, 1.795, 2.89]) {
      for (const dx of [-.43, .43]) detail('Balcony framed panel stile', [.055, .88, .065], [x + dx, ff + .53, -.025])
      for (const y of [.09, .97]) detail('Balcony framed panel rail', [.915, .055, .065], [x, ff + y, -.025])
    }
    detail('Balcony stone inset', [2.95, .35, .045], [1.795, ff - .325, .10], 'Detached stone cladding')
    for (const x of [1.89, 3.07]) detail('Stone entry jamb', [.14, 2.53, .22], [x, gf + 1.265, -1.01], 'Detached stone cladding')
  }
  detail('Entry wall light backplate', [.12, .30, .035], [1.77, gf + 1.8, -1.015])
  detail('Entry wall light diffuser', [.075, .21, .09], [1.77, gf + 1.8, -.965])
}
