import { SITEWISE_THEMES } from '../style-guide/sitewise-colours.js';

const mapColour = hex => hex.slice(1).match(/../g).map(channel => parseInt(channel, 16) / 255);
const mapCanvas = mapColour(SITEWISE_THEMES.light.canvas);
const mapInk = mapColour(SITEWISE_THEMES.light['map-line-interactive']);

const vertexSource = `
  attribute vec2 a_grid;
  uniform float u_time;
  uniform float u_aspect;
  varying vec2 v_ground;
  varying float v_tint;
  varying float v_distance;
  void main() {
    float z = 1.35 + 38.0 * pow(a_grid.y, 1.8);
    float x = a_grid.x * (z + 1.0) * u_aspect / 1.35 * 1.18;
    float travel = u_time * 0.065;
    float phase = x * 0.60 + z * 0.25 - u_time * 0.14;
    float swell = 0.15 * sin(phase);
    // A real height displacement lifts the cadastral lines with the ground.
    gl_Position = vec4(1.35 * x / u_aspect, 0.60 * z - 1.35 * (2.3 - swell), 0.0, z);
    // Keep texture coordinates small during long sessions; the mirrored period is 10.
    v_ground = vec2(x, z + mod(travel, 10.0));
    v_tint = x * 0.32 + z * 0.12 - u_time * 0.11;
    v_distance = z;
  }
`;

const fragmentSource = `
  #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
  #else
    precision mediump float;
  #endif
  uniform vec3 u_ink;
  uniform vec3 u_canvas;
  uniform sampler2D u_map;
  uniform vec2 u_mapScale;
  uniform vec2 u_mapOffset;
  varying vec2 v_ground;
  varying float v_tint;
  varying float v_distance;
  float mirror(float p) { return 1.0 - abs(mod(p, 2.0) - 1.0); }
  void main() {
    // Sample the readable foreground, excluding the still's compressed horizon.
    // Mirror at tile edges to keep boundary samples continuous without a camera reset.
    vec2 uv = vec2(mirror(v_ground.x / 15.996 + 0.5), 1.0 - mirror(v_ground.y / 5.0));
    vec3 source = texture2D(u_map, uv * u_mapScale + u_mapOffset).rgb;
    float line = smoothstep(0.065, 0.72, dot(source, vec3(0.2126, 0.7152, 0.0722)));
    float distanceFade = 1.0 - smoothstep(4.5, 16.0, v_distance);
    float sweep = 0.5 + 0.5 * sin(v_tint);
    vec3 colour = u_ink;
    float ink = line * distanceFade * mix(0.19, 0.44, sweep);
    gl_FragColor = vec4(mix(u_canvas, colour, ink), 1.0);
  }
`;

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(message || 'Could not compile the landscape shader.');
  }
  return shader;
}

function mesh(columns, rows) {
  const vertices = new Float32Array((columns + 1) * (rows + 1) * 2);
  const indices = new Uint16Array(columns * rows * 6);
  let vertex = 0, index = 0;
  for (let row = 0; row <= rows; row++) {
    for (let column = 0; column <= columns; column++) {
      vertices[vertex++] = column / columns * 2 - 1;
      vertices[vertex++] = row / rows;
      if (row < rows && column < columns) {
        const a = row * (columns + 1) + column, b = a + columns + 1;
        indices.set([a, b, a + 1, a + 1, b, b + 1], index);
        index += 6;
      }
    }
  }
  return { vertices, indices };
}

function groundTexture(canvas, source, maxSize) {
  const cropTop = Math.round(source.naturalHeight * 0.42);
  const cropHeight = Math.round(source.naturalHeight * 0.98) - cropTop;
  const scale = Math.min(1, maxSize / source.naturalWidth, maxSize / cropHeight);
  const width = Math.max(1, Math.round(source.naturalWidth * scale));
  const height = Math.max(1, Math.round(cropHeight * scale));
  const sampling = canvas.ownerDocument.createElement('canvas');
  sampling.width = 2 ** Math.ceil(Math.log2(width));
  sampling.height = 2 ** Math.ceil(Math.log2(height));
  const context = sampling.getContext('2d');
  if (!context) throw new Error('Could not prepare the landscape texture.');
  context.imageSmoothingQuality = 'high';
  context.drawImage(source, 0, cropTop, source.naturalWidth, cropHeight, 0, 0, width, height);
  // Edge padding enables mipmaps without stretching the source to a power of two.
  if (sampling.width > width) context.drawImage(sampling, width - 1, 0, 1, height, width, 0, sampling.width - width, height);
  if (sampling.height > height) context.drawImage(sampling, 0, height - 1, sampling.width, 1, 0, height, sampling.width, sampling.height - height);
  return { sampling, width, height };
}

export function createTerrainRenderer(canvas, source) {
  const gl = canvas.getContext('webgl', { alpha: false, antialias: true, depth: false, powerPreference: 'low-power' });
  if (!gl) throw new Error('WebGL is unavailable.');
  const vertex = compile(gl, gl.VERTEX_SHADER, vertexSource);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(message || 'Could not link the landscape shader.');
  }
  gl.useProgram(program);
  gl.disable(gl.BLEND);
  gl.disable(gl.DEPTH_TEST);
  gl.disable(gl.CULL_FACE);
  const { vertices, indices } = mesh(80, 100);
  const vertexBuffer = gl.createBuffer(), indexBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, 'a_grid');
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
  const texture = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const mobile = canvas.getBoundingClientRect().width < 700;
  const maxSize = Math.min(gl.getParameter(gl.MAX_TEXTURE_SIZE), mobile ? 2048 : 4096);
  const { sampling, width, height } = groundTexture(canvas, source, maxSize);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, sampling);
  gl.generateMipmap(gl.TEXTURE_2D);
  const anisotropy = gl.getExtension('EXT_texture_filter_anisotropic');
  if (anisotropy) {
    gl.texParameterf(gl.TEXTURE_2D, anisotropy.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(8, gl.getParameter(anisotropy.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));
  }
  gl.uniform1i(gl.getUniformLocation(program, 'u_map'), 0);
  gl.uniform2f(gl.getUniformLocation(program, 'u_mapScale'), (width - 1) / sampling.width, (height - 1) / sampling.height);
  gl.uniform2f(gl.getUniformLocation(program, 'u_mapOffset'), 0.5 / sampling.width, 0.5 / sampling.height);
  const time = gl.getUniformLocation(program, 'u_time');
  const aspect = gl.getUniformLocation(program, 'u_aspect');
  gl.clearColor(...mapCanvas, 1);
  gl.uniform3f(gl.getUniformLocation(program, 'u_ink'), ...mapInk);
  gl.uniform3f(gl.getUniformLocation(program, 'u_canvas'), ...mapCanvas);

  return {
    resize() {
      const { width, height } = canvas.getBoundingClientRect();
      const ratio = Math.min(canvas.ownerDocument.defaultView.devicePixelRatio || 1, width < 700 ? 1.5 : 2, Math.sqrt(6000000 / Math.max(1, width * height)));
      canvas.width = Math.max(1, Math.round(width * ratio));
      canvas.height = Math.max(1, Math.round(height * ratio));
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform1f(aspect, width / Math.max(1, height));
    },
    render(seconds) {
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform1f(time, seconds);
      gl.drawElements(gl.TRIANGLES, indices.length, gl.UNSIGNED_SHORT, 0);
    },
    dispose() {
      gl.deleteTexture(texture);
      gl.deleteBuffer(vertexBuffer);
      gl.deleteBuffer(indexBuffer);
      gl.deleteProgram(program);
    },
  };
}
