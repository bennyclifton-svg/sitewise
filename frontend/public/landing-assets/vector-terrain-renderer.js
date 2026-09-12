import { SITEWISE_THEMES } from '../style-guide/sitewise-colours.js';

const mapColour = hex => hex.slice(1).match(/../g).map(channel => parseInt(channel, 16) / 255);
const mapCanvas = mapColour(SITEWISE_THEMES.light.canvas);
const mapInk = mapColour(SITEWISE_THEMES.light['map-line-interactive']);

const vertexSource = `
  attribute vec4 a_segment;
  attribute vec2 a_corner;
  uniform float u_time;
  uniform float u_aspect;
  uniform vec2 u_resolution;
  uniform float u_stroke;
  uniform vec4 u_tile;
  varying vec2 v_capsule;
  varying float v_tint;
  varying float v_length;
  varying float v_distance;

  float wavePhase(vec2 ground) {
    return ground.x * 0.60 + ground.y * 0.25 - u_time * 0.14;
  }

  vec2 project(vec2 ground) {
    float swell = 0.15 * sin(wavePhase(ground));
    return vec2(1.35 * ground.x / u_aspect, 0.60 * ground.y - 1.35 * (2.3 - swell)) / ground.y;
  }

  void main() {
    float travel = mod(u_time * 0.065, 10.0);
    vec2 start = a_segment.xy * u_tile.xy + u_tile.zw - vec2(0.0, travel);
    vec2 end = a_segment.zw * u_tile.xy + u_tile.zw - vec2(0.0, travel);
    v_capsule = vec2(0.0);
    v_tint = 0.0;
    v_length = 0.0;
    v_distance = 40.0;
    if (max(start.y, end.y) < 1.35 || min(start.y, end.y) > 16.0) {
      gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
      return;
    }
    // Clip before perspective division so a segment cannot explode at the camera.
    if (start.y < 1.35) start = mix(start, end, (1.35 - start.y) / (end.y - start.y));
    if (end.y < 1.35) end = mix(end, start, (1.35 - end.y) / (start.y - end.y));
    vec2 first = project(start);
    vec2 last = project(end);
    vec2 direction = (last - first) * u_resolution * 0.5;
    float lengthPixels = length(direction);
    direction /= max(lengthPixels, 0.0001);
    vec2 normal = vec2(-direction.y, direction.x);
    float radius = u_stroke * 0.5 + 0.8;
    float cap = a_corner.x * 2.0 - 1.0;
    vec2 offset = (direction * cap + normal * a_corner.y) * radius;
    gl_Position = vec4(mix(first, last, a_corner.x) + offset * 2.0 / u_resolution, 0.0, 1.0);
    v_capsule = vec2(a_corner.x * lengthPixels + cap * radius, a_corner.y * radius);
    vec2 ground = mix(start, end, a_corner.x);
    // Line emphasis drifts independently of the physical terrain wave.
    v_tint = ground.x * 0.32 + ground.y * 0.12 - u_time * 0.11;
    v_length = lengthPixels;
    v_distance = mix(start.y, end.y, a_corner.x);
  }
`;

const fragmentSource = `
  #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
  #else
    precision mediump float;
  #endif
  uniform vec3 u_ink;
  uniform float u_stroke;
  varying vec2 v_capsule;
  varying float v_tint;
  varying float v_length;
  varying float v_distance;
  void main() {
    float cap = max(max(-v_capsule.x, v_capsule.x - v_length), 0.0);
    float edge = length(vec2(cap, v_capsule.y));
    float coverage = 1.0 - smoothstep(u_stroke * 0.5 - 0.55, u_stroke * 0.5 + 0.55, edge);
    float distanceFade = 1.0 - smoothstep(4.5, 16.0, v_distance);
    float sweep = 0.5 + 0.5 * sin(v_tint);
    vec3 colour = u_ink;
    gl_FragColor = vec4(colour, coverage * distanceFade * mix(0.19, 0.44, sweep));
  }
`;

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(message || 'Could not compile the vector landscape shader.');
  }
  return shader;
}

function segmentVertices(data) {
  if (data?.version !== 1 || !Array.isArray(data.lines) || !Number.isFinite(data.source?.width) || data.source.width <= 0 || !Number.isFinite(data.source?.height) || data.source.height <= 0) {
    throw new Error('Invalid cadastral vector data.');
  }
  const segments = [];
  let count = 0;
  for (const line of data.lines) {
    if (!Array.isArray(line)) throw new Error('Invalid cadastral polyline.');
    for (const point of line) {
      if (!Array.isArray(point) || point.length !== 2 || point.some(value => !Number.isFinite(value) || value < 0 || value > 1)) {
        throw new Error('Invalid cadastral coordinate.');
      }
      if (++count > 200000) throw new Error('Cadastral vector data exceeds the rendering budget.');
    }
    for (let index = 1; index < line.length; index++) {
      const start = line[index - 1], end = line[index];
      const delta = end[1] - start[1];
      let from = 0, to = 1;
      // Repeating the baked horizon at the camera would magnify compressed fragments.
      if (delta === 0) {
        if (start[1] < 0.42 || start[1] > 0.98) continue;
      } else {
        const a = (0.42 - start[1]) / delta, b = (0.98 - start[1]) / delta;
        from = Math.max(0, Math.min(a, b));
        to = Math.min(1, Math.max(a, b));
        if (from >= to) continue;
      }
      const ground = fraction => {
        const point = fraction === 0 ? start : fraction === 1 ? end : [start[0] + (end[0] - start[0]) * fraction, start[1] + delta * fraction];
        return [(point[0] - 0.5) * 15.996, (0.98 - point[1]) / 0.56 * 5];
      };
      const first = ground(from), last = ground(to);
      if (Math.hypot(last[0] - first[0], last[1] - first[1]) < 0.00001) continue;
      // Move shared source corners; never bend a straight boundary with added vertices.
      segments.push([...first, ...last]);
      if (segments.length > 60000) throw new Error('Cadastral segments exceed the rendering budget.');
    }
  }
  if (!segments.length) throw new Error('Cadastral vector data contains no ground boundaries.');
  const corners = [[0, -1], [1, -1], [0, 1], [0, 1], [1, -1], [1, 1]];
  const vertices = new Float32Array(segments.length * 36);
  let offset = 0;
  for (const segment of segments) {
    for (const corner of corners) {
      vertices.set(segment, offset);
      vertices.set(corner, offset + 4);
      offset += 6;
    }
  }
  return vertices;
}

export function createVectorTerrainRenderer(canvas, data) {
  const vertices = segmentVertices(data);
  const gl = canvas.getContext('webgl', { alpha: false, antialias: true, depth: false, powerPreference: 'low-power' });
  if (!gl) throw new Error('WebGL is unavailable.');
  const shaders = [];
  let program, buffer, segment = -1, corner = -1;
  const dispose = () => {
    for (const shader of shaders) gl.deleteShader(shader);
    if (segment >= 0) gl.disableVertexAttribArray(segment);
    if (corner >= 0) gl.disableVertexAttribArray(corner);
    if (buffer) gl.deleteBuffer(buffer);
    if (program) gl.deleteProgram(program);
  };
  try {
    shaders.push(compile(gl, gl.VERTEX_SHADER, vertexSource));
    shaders.push(compile(gl, gl.FRAGMENT_SHADER, fragmentSource));
    program = gl.createProgram();
    for (const shader of shaders) gl.attachShader(program, shader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program) || 'Could not link the vector landscape shader.');
    gl.useProgram(program);
    buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    if (gl.getError() !== gl.NO_ERROR) throw new Error('Could not upload the cadastral geometry.');
    segment = gl.getAttribLocation(program, 'a_segment');
    corner = gl.getAttribLocation(program, 'a_corner');
    gl.enableVertexAttribArray(segment);
    gl.enableVertexAttribArray(corner);
    gl.vertexAttribPointer(segment, 4, gl.FLOAT, false, 24, 0);
    gl.vertexAttribPointer(corner, 2, gl.FLOAT, false, 24, 16);
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.clearColor(...mapCanvas, 1);
    gl.uniform3f(gl.getUniformLocation(program, 'u_ink'), ...mapInk);
    const uniforms = Object.fromEntries(['time', 'aspect', 'resolution', 'stroke', 'tile'].map(name => [name, gl.getUniformLocation(program, `u_${name}`)]));
    let aspect = 1;
    return {
      resize() {
        const { width, height } = canvas.getBoundingClientRect();
        const ratio = Math.min(canvas.ownerDocument.defaultView.devicePixelRatio || 1, width < 700 ? 1.5 : 2, Math.sqrt(6000000 / Math.max(1, width * height)));
        canvas.width = Math.max(1, Math.round(width * ratio));
        canvas.height = Math.max(1, Math.round(height * ratio));
        aspect = width / Math.max(1, height);
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.uniform1f(uniforms.aspect, aspect);
        gl.uniform2f(uniforms.resolution, canvas.width, canvas.height);
        gl.uniform1f(uniforms.stroke, 0.95 * ratio);
      },
      render(seconds) {
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.uniform1f(uniforms.time, seconds);
        const travel = seconds * 0.065 % 10;
        for (let row = Math.floor(travel / 5); row < Math.ceil((16 + travel) / 5); row++) {
          const far = Math.min(16, (row + 1) * 5 - travel);
          const extent = far * aspect / 1.35;
          const first = Math.ceil((-extent - 15.996 / 2) / 15.996);
          const last = Math.floor((extent + 15.996 / 2) / 15.996);
          for (let column = first; column <= last; column++) {
            const mirrorX = column % 2 !== 0, mirrorZ = row % 2 !== 0;
            gl.uniform4f(uniforms.tile, mirrorX ? -1 : 1, mirrorZ ? -1 : 1, column * 15.996, (row + (mirrorZ ? 1 : 0)) * 5);
            gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 6);
          }
        }
      },
      dispose,
    };
  } catch (error) {
    dispose();
    throw error;
  }
}
