import * as THREE from 'three'

/** Keep the public footpath flush with the lot's side boundaries. */
export function createTerracePlinth() {
  const outline = new THREE.Shape()
  outline.moveTo(-2.32, -20.55)
  outline.lineTo(51.32, -20.55)
  outline.lineTo(51.32, 6.15)
  outline.lineTo(-2.32, 6.15)
  outline.closePath()
  const plinth = new THREE.Group()
  plinth.name = 'Ivory site plinth with blue foundation strip'
  for (const [top, bottom, colour] of [
    [-.025, -1.3875, '#F4F1EA'],
    [-1.3875, -1.5625, '#087ac9'],
  ] as const) {
    const geometry = new THREE.ExtrudeGeometry(outline, { depth: top - bottom, bevelEnabled: false })
    geometry.rotateX(Math.PI / 2)
    geometry.translate(0, top, 0)
    const material = new THREE.MeshStandardMaterial({ color: colour, roughness: .65, metalness: 0 })
    const mesh = new THREE.Mesh(geometry, material)
    mesh.castShadow = true
    mesh.receiveShadow = true
    plinth.add(mesh)
  }
  return plinth
}
