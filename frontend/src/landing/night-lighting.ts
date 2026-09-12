import * as THREE from 'three'

type LitPart = { mesh: THREE.Mesh; material: THREE.MeshStandardMaterial; glass: boolean; system: string }

export function createNightLighting(scene: THREE.Scene, parts: LitPart[]) {
  const night = { value: 0 }
  const warm = new THREE.Color('#ffe4c4')
  for (const part of parts) {
    if (!part.glass || part.system !== 'architecture') continue
    const isWindow = Boolean(part.mesh.userData.sw_night_window)
    part.material.onBeforeCompile = shader => {
      shader.uniforms.swNight = night
      shader.vertexShader = 'varying vec3 swPosition;\n' + shader.vertexShader
      shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nswPosition = (modelMatrix * vec4(transformed, 1.0)).xyz;')
      shader.fragmentShader = 'varying vec3 swPosition; uniform float swNight;\n' + shader.fragmentShader
      shader.fragmentShader = shader.fragmentShader.replace('#include <emissivemap_fragment>', `
        #include <emissivemap_fragment>
        float dwelling = clamp(floor((swPosition.z + 14.0) / 5.6), 0.0, 4.0);
        float occupied = dwelling == 1.0 ? 0.0 : (dwelling == 3.0 ? 0.85 : 0.6);
        float room = ${isWindow ? '1.0' : 'step(abs(swPosition.x), 5.3) * step(4.1, abs(swPosition.x)) * step(3.2, swPosition.y) * step(swPosition.y, 6.2)'};
        float lower = swPosition.y < 6.2 ? 1.0 : 0.65;
        totalEmissiveRadiance *= occupied * room * lower;
        diffuseColor.a *= mix(1.0, 1.0 + occupied * room, swNight);
      `)
    }
    part.material.customProgramCacheKey = () => `sitewise-occupied-glass-${isWindow}`
    part.material.needsUpdate = true
  }
  const lights: { light: THREE.Light; intensity: number }[] = []
  const fixtures: THREE.Mesh<THREE.SphereGeometry, THREE.MeshStandardMaterial>[] = []
  const add = (light: THREE.Light, intensity: number) => { scene.add(light); lights.push({ light, intensity }) }
  // Five dwellings run along the survey Z axis; the second remains unoccupied.
  for (const [index, z] of [-11.2, -5.6, 0, 5.6, 11.2].entries()) {
    if (index === 1) continue
    const living = new THREE.PointLight(warm, 0, 5, 2)
    living.position.set(3.5, 4.5, z + .8)
    add(living, index === 3 ? 16 : 11)
    const entry = new THREE.SpotLight(warm, 0, 5, .75, 1, 2)
    entry.position.set(-5.1, 2.65, z - 2)
    entry.target.position.set(-6.2, .15, z - 2)
    scene.add(entry.target); add(entry, 18)
    const fixture = new THREE.Mesh(new THREE.SphereGeometry(.055, 8, 6), new THREE.MeshStandardMaterial({ color: '#d8d4c9', emissive: warm, emissiveIntensity: 0 }))
    fixture.position.copy(entry.position); scene.add(fixture); fixtures.push(fixture)
    if (index === 0 || index === 4) {
      const garage = new THREE.PointLight('#fff0d8', 0, 4.5, 2)
      garage.position.set(-2.5, 2.4, z)
      add(garage, 22)
    }
  }
  return {
    apply(amount: number, visible: boolean) {
      night.value = amount
      lights.forEach(({ light, intensity }) => { light.intensity = visible ? amount * intensity : 0 })
      fixtures.forEach(mesh => { mesh.visible = visible; mesh.material.emissiveIntensity = amount * 1.2 })
      for (const part of parts) if (part.glass && part.system === 'architecture') {
        part.material.emissive.copy(warm)
        part.material.emissiveIntensity = visible ? amount * .65 : 0
      }
    },
    dispose() { fixtures.forEach(mesh => { mesh.geometry.dispose(); mesh.material.dispose() }) },
  }
}
