import type * as THREE from 'three'

export const isTerraceBrick = (material: THREE.Material) => /^Warm brick \d+$/.test(material.name)

/** The GLB carries brick material names, but Blender's procedural courses are not exported. */
export function prepareTerraceBrick(material: THREE.MeshStandardMaterial) {
  material.roughness = .85
  material.onBeforeCompile = shader => {
    const varying = 'varying vec3 swBrickPosition;\nvarying vec3 swBrickNormal;\n'
    shader.vertexShader = varying + shader.vertexShader.replace('#include <project_vertex>', `
      #include <project_vertex>
      swBrickPosition = (modelMatrix * vec4(transformed, 1.0)).xyz;
      swBrickNormal = normalize(mat3(modelMatrix) * normal);
    `)
    shader.fragmentShader = varying + shader.fragmentShader.replace('#include <color_fragment>', `
      #include <color_fragment>
      vec3 brickAxis = abs(normalize(swBrickNormal));
      vec2 brickUv = brickAxis.x > brickAxis.z ? swBrickPosition.zy : swBrickPosition.xy;
      if (brickAxis.y > max(brickAxis.x, brickAxis.z)) brickUv = swBrickPosition.xz;
      // Nominal 230 x 76 mm running bond, aligned in metres across wall returns.
      float brickRow = floor(brickUv.y / .076);
      vec2 brickCell = vec2(brickUv.x + mod(brickRow, 2.0) * .115, brickUv.y);
      vec2 brickModule = vec2(.23, .076);
      vec2 brickDistance = abs(mod(brickCell + brickModule * .5, brickModule) - brickModule * .5);
      vec2 brickFootprint = max(fwidth(brickUv), vec2(.0001));
      vec2 brickEdge = smoothstep(vec2(.004) - brickFootprint, vec2(.004) + brickFootprint, brickDistance);
      float brickFace = brickEdge.x * brickEdge.y;
      float brickDetail = 1.0 - smoothstep(.025, .076, max(brickFootprint.x, brickFootprint.y));
      diffuseColor.rgb *= mix(.94, mix(.62, 1.0, brickFace), brickDetail);
    `).replace('#include <normal_fragment_maps>', `
      #include <normal_fragment_maps>
      // Recess the mortar in the lighting as well as the colour.
      float brickHeight = .0015 * brickFace * brickDetail;
      vec3 brickDx = dFdx(-vViewPosition), brickDy = dFdy(-vViewPosition);
      vec3 brickCrossX = cross(brickDy, normal), brickCrossY = cross(normal, brickDx);
      float brickDet = dot(brickDx, brickCrossX) * faceDirection;
      vec3 brickGradient = sign(brickDet) * (dFdx(brickHeight) * brickCrossX + dFdy(brickHeight) * brickCrossY);
      normal = normalize(max(abs(brickDet), .00000001) * normal - brickGradient);
    `)
  }
  material.customProgramCacheKey = () => 'terrace-white-brick-v1'
}
