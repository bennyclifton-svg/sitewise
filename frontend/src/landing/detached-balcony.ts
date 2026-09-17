import * as THREE from 'three'
import { box, type Point } from './terrace-parts'
import { detachedLayout as layout } from './detached-layout'

export function openDetachedBalcony(home: THREE.Group) {
  const upper = layout.upper
  const slider = home.children.find(object => object.name === 'Upper front glazing' && object.position.x < 3) as THREE.Mesh
  slider.scale.x = .5
  slider.position.x = .92
  slider.name = 'Balcony fixed glass panel'
  const open = slider.clone()
  open.geometry = slider.geometry.clone()
  open.material = (slider.material as THREE.Material).clone()
  open.position.z -= .055
  open.name = 'Balcony sliding panel fully open'
  home.add(open)
  for (const x of [.33, 1.51]) box(home, [.035, 2.1, .035], [x, upper + 1.07, -1.015], 'architecture', 2).name = 'Open slider stile'
  for (const y of [upper + .02, upper + 2.12]) box(home, [2.4, .025, .10], [1.52, y, -.99], 'architecture', 2).name = 'Balcony sliding door track'
  box(home, [.025, .22, .055], [1.46, upper + 1.08, -.97], 'architecture', 2).name = 'Sliding door pull'
  for (const object of [...home.children]) {
    if (!['Balcony baluster', 'Balcony side baluster', 'Balcony paired picket'].includes(object.name)) continue
    home.remove(object)
    const mesh = object as THREE.Mesh
    mesh.geometry.dispose(); (mesh.material as THREE.Material).dispose()
  }
  const glass = (size: Point, at: Point) => {
    const pane = box(home, size, at, 'architecture', 2)
    pane.name = 'Balcony glass balustrade'; pane.userData.sw_glass = true
    ;(pane.material as THREE.Material).name = 'Glazing'
  }
  for (let i = 0; i < 3; i++) glass([1.055, .9, .018], [.72 + i * 1.075, upper + .535, -.07])
  for (const x of [.14, 3.45]) glass([.018, .9, .83], [x, upper + .535, -.52])
  for (const x of [.27, 1.25, 2.32, 3.3]) box(home, [.045, .13, .05], [x, upper + .10, -.07], 'architecture', 2).name = 'Glass balustrade fixing'
}
