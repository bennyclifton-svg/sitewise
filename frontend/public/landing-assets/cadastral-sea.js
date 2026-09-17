const COS30 = Math.sqrt(3) / 2;
export const VIEW_BOUNDS = { minX: -580, maxX: 720, minY: -620, maxY: 620 };
export const GROUND_TILT = 0.22;
const SPACING = 8;
const INK = [218 / 255, 214 / 255, 208 / 255];
const CANVAS = [249 / 255, 247 / 255, 243 / 255];
export const LINE_ALPHA = 0.7;
export const WAVE_AMP = 1.3;
export const WAVE_FREQ = 4 / 3;
export const EDGE_BAND = 0.045;
export const FIELD_YAW = Math.PI / 2;
export const CREST_LO = -6 * WAVE_AMP;
export const CREST_HI = 8 * WAVE_AMP;
export const BLUR_SPREAD = 2.1;
export const BLUR_MIX = 0.52;

export function waveHeight(x, y, time, freq = WAVE_FREQ, amp = WAVE_AMP) {
  return amp * (
    11 * Math.sin(x * 0.01 * freq + y * 0.004 * freq - time * 0.72)
    + 6.5 * Math.sin(-x * 0.0065 * freq + y * 0.011 * freq - time * 1.05)
    + 2.4 * Math.sin(x * 0.015 * freq - y * 0.008 * freq + time * 1.4)
  );
}

export function rotateGround(x, y, angle = FIELD_YAW) {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [x * cosine - y * sine, x * sine + y * cosine];
}

export function crestWeight(height, lo = CREST_LO, hi = CREST_HI) {
  if (height <= lo) return 0;
  if (height >= hi) return 1;
  return (height - lo) / (hi - lo);
}

export function projectIsometric(x, y, z) {
  const depth = (VIEW_BOUNDS.maxY - y) / (VIEW_BOUNDS.maxY - VIEW_BOUNDS.minY);
  const persp = 1 / (1 + Math.max(0, depth) * 0.65);
  return {
    x: (x - y) * COS30 * persp,
    y: ((x + y) * GROUND_TILT - z) * persp,
  };
}

export function subdivideSegment(start, end, spacing = SPACING) {
  const length = Math.hypot(end[0] - start[0], end[1] - start[1]);
  if (length <= spacing) return [start, end];
  const points = [start];
  for (let travelled = spacing; travelled < length; travelled += spacing) {
    const t = travelled / length;
    points.push([start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t]);
  }
  points.push(end);
  return points;
}

function inView([x, y], bounds = VIEW_BOUNDS) {
  return x >= bounds.minX && x <= bounds.maxX && y >= bounds.minY && y <= bounds.maxY;
}

export function extractSegments(data, bounds = VIEW_BOUNDS, spacing = SPACING, yaw = FIELD_YAW) {
  const segments = [];
  for (const edge of data.boundaries ?? []) {
    const [rawStart, rawEnd] = edge.points ?? [];
    if (!rawStart || !rawEnd) continue;
    const start = rotateGround(rawStart[0], rawStart[1], yaw);
    const end = rotateGround(rawEnd[0], rawEnd[1], yaw);
    if (!inView(start, bounds) && !inView(end, bounds)) continue;
    const points = subdivideSegment(start, end, spacing);
    for (let index = 1; index < points.length; index++) {
      segments.push([points[index - 1][0], points[index - 1][1], points[index][0], points[index][1]]);
    }
  }
  return segments;
}

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(message || 'Could not compile the cadastral sea shader.');
  }
  return shader;
}

function link(gl, vertex, fragment) {
  const program = gl.createProgram();
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(message || 'Could not link the cadastral sea shader.');
  }
  return program;
}

function isoBounds(segments) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  const consider = (x, y) => {
    const point = projectIsometric(x, y, 0);
    minX = Math.min(minX, point.x);
    maxX = Math.max(maxX, point.x);
    minY = Math.min(minY, point.y);
    maxY = Math.max(maxY, point.y);
  };
  for (const [x1, y1, x2, y2] of segments) {
    consider(x1, y1);
    consider(x2, y2);
  }
  return { minX, maxX, minY, maxY };
}

// Height-fit puts the far edge at clip Y = 1/3. Zoom would send that
// horizon off the top; FIELD_SHIFT_Y pulls it back so the top third stays sky.
export const GROUND_ZOOM = 2.05;
export const FIELD_SHIFT_X = 0;
export const HORIZON_CLIP = 1 / 3;
export const FIELD_SHIFT_Y = HORIZON_CLIP - (4 / 3) * GROUND_ZOOM + 1;
export const FIELD_TURN = 0.28;

export function fitGroundFrame(bounds, aspect, zoom = 1, shiftX = 0, shiftY = 0) {
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  const cx = (bounds.minX + bounds.maxX) / 2;
  const scale = ((4 / 3) / height) * zoom;
  return [scale / aspect, -scale, -cx * scale / aspect + shiftX, -1 - bounds.maxY * -scale + shiftY];
}

export function turnFittedPoint(x, y, angle = FIELD_TURN, pivotX = 0, pivotY = -1) {
  const dx = x - pivotX;
  const dy = y - pivotY;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return { x: pivotX + dx * cosine - dy * sine, y: pivotY + dx * sine + dy * cosine };
}

function makeTarget(gl, width, height) {
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const framebuffer = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
  if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) {
    gl.deleteTexture(texture);
    gl.deleteFramebuffer(framebuffer);
    throw new Error('Could not allocate the cadastral sea buffer.');
  }
  return { texture, framebuffer };
}

const lineVertex = `
  attribute vec4 a_segment;
  attribute vec2 a_corner;
  uniform float u_time;
  uniform vec2 u_resolution;
  uniform float u_stroke;
  uniform vec4 u_fit;
  uniform float u_turn;
  uniform float u_waveFreq;
  uniform vec2 u_focus;
  varying vec2 v_capsule;
  varying float v_length;
  varying float v_depth;
  varying float v_height;
  varying vec2 v_clip;

  float height(vec2 p) {
    return ${WAVE_AMP.toFixed(2)} * (
      11.0 * sin(p.x * 0.01 * u_waveFreq + p.y * 0.004 * u_waveFreq - u_time * 0.72)
      + 6.5 * sin(-p.x * 0.0065 * u_waveFreq + p.y * 0.011 * u_waveFreq - u_time * 1.05)
      + 2.4 * sin(p.x * 0.015 * u_waveFreq - p.y * 0.008 * u_waveFreq + u_time * 1.4)
    );
  }

  vec3 project(vec2 ground) {
    float z = height(ground);
    float depth = clamp((u_focus.x - ground.y) / (u_focus.x - u_focus.y), 0.0, 1.0);
    float persp = 1.0 / (1.0 + depth * 0.65);
    vec2 iso = vec2((ground.x - ground.y) * 0.86602540378, (ground.x + ground.y) * 0.22 - z) * persp;
    vec2 fitted = iso * u_fit.xy + u_fit.zw;
    vec2 pivot = vec2(0.0, -1.0);
    vec2 delta = fitted - pivot;
    float cosine = cos(u_turn);
    float sine = sin(u_turn);
    return vec3(pivot + vec2(delta.x * cosine - delta.y * sine, delta.x * sine + delta.y * cosine), z);
  }

  void main() {
    vec3 start3 = project(a_segment.xy);
    vec3 end3 = project(a_segment.zw);
    vec2 start = start3.xy;
    vec2 end = end3.xy;
    vec2 direction = (end - start) * u_resolution * 0.5;
    float lengthPixels = length(direction);
    direction /= max(lengthPixels, 0.0001);
    vec2 normal = vec2(-direction.y, direction.x);
    float depth = clamp((u_focus.x - mix(a_segment.y, a_segment.w, a_corner.x)) / (u_focus.x - u_focus.y), 0.0, 1.0);
    float radius = u_stroke * mix(0.55, 1.15, depth) + 1.1;
    float cap = a_corner.x * 2.0 - 1.0;
    vec2 offset = (direction * cap + normal * a_corner.y) * radius;
    gl_Position = vec4(mix(start, end, a_corner.x) + offset * 2.0 / u_resolution, 0.0, 1.0);
    v_capsule = vec2(a_corner.x * lengthPixels + cap * radius, a_corner.y * radius);
    v_length = lengthPixels;
    v_depth = depth;
    v_height = mix(start3.z, end3.z, a_corner.x);
    v_clip = gl_Position.xy;
  }
`;

const lineFragment = `
  #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
  #else
    precision mediump float;
  #endif
  uniform vec3 u_ink;
  uniform vec2 u_resolution;
  uniform float u_stroke;
  uniform float u_focusLimit;
  uniform float u_edgeFade;
  uniform float u_edgeBand;
  uniform float u_crestLo;
  uniform float u_crestHi;
  uniform float u_crestGate;
  uniform float u_horizon;
  varying vec2 v_capsule;
  varying float v_length;
  varying float v_depth;
  varying float v_height;
  varying vec2 v_clip;
  void main() {
    float keep = 1.0 - smoothstep(u_focusLimit - 0.12, u_focusLimit + 0.04, v_depth);
    keep *= mix(1.0, smoothstep(u_crestLo, u_crestHi, v_height), u_crestGate);
    float pageY = gl_FragCoord.y / max(u_resolution.y, 1.0) * 2.0 - 1.0;
    keep *= 1.0 - smoothstep(u_horizon - 0.05, u_horizon, pageY);
    if (keep < 0.01) discard;
    float cap = max(max(-v_capsule.x, v_capsule.x - v_length), 0.0);
    float edge = length(vec2(cap, v_capsule.y));
    float coverage = 1.0 - smoothstep(u_stroke * 0.5 - 0.55, u_stroke * 0.5 + 0.55, edge);
    float fade = mix(0.92, 0.28, v_depth);
    float frame = 1.0 - 2.0 * u_edgeBand;
    float rim = max(smoothstep(frame, 1.0, abs(v_clip.x)), smoothstep(frame, 1.0, abs(v_clip.y)));
    float sharp = 1.0 - rim * u_edgeFade;
    gl_FragColor = vec4(u_ink, coverage * fade * keep * sharp * ${LINE_ALPHA.toFixed(2)});
  }
`;

const blitVertex = `
  attribute vec2 a_pos;
  varying vec2 v_uv;
  void main() {
    v_uv = a_pos * 0.5 + 0.5;
    gl_Position = vec4(a_pos, 0.0, 1.0);
  }
`;

const blurFragment = `
  #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
  #else
    precision mediump float;
  #endif
  uniform sampler2D u_image;
  uniform vec2 u_texel;
  varying vec2 v_uv;
  void main() {
    vec4 colour = texture2D(u_image, v_uv) * 0.227027;
    colour += texture2D(u_image, v_uv + u_texel * 1.384615) * 0.316216;
    colour += texture2D(u_image, v_uv - u_texel * 1.384615) * 0.316216;
    colour += texture2D(u_image, v_uv + u_texel * 3.230769) * 0.070270;
    colour += texture2D(u_image, v_uv - u_texel * 3.230769) * 0.070270;
    gl_FragColor = colour;
  }
`;

const copyFragment = `
  #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
  #else
    precision mediump float;
  #endif
  uniform sampler2D u_image;
  varying vec2 v_uv;
  void main() {
    gl_FragColor = texture2D(u_image, v_uv);
  }
`;

const mixFragment = `
  #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
  #else
    precision mediump float;
  #endif
  uniform sampler2D u_image;
  uniform sampler2D u_sharp;
  uniform float u_blurMix;
  uniform vec3 u_canvas;
  uniform float u_horizon;
  varying vec2 v_uv;
  void main() {
    vec4 colour = mix(texture2D(u_sharp, v_uv), texture2D(u_image, v_uv), u_blurMix);
    float sky = smoothstep(u_horizon - 0.05, u_horizon, v_uv.y * 2.0 - 1.0);
    gl_FragColor = mix(colour, vec4(u_canvas, 1.0), sky);
  }
`;

export function createCadastralSeaRenderer(canvas, data) {
  const segments = extractSegments(data);
  if (!segments.length) throw new Error('Cadastral sea has no visible boundaries.');
  const gl = canvas.getContext('webgl', { alpha: false, antialias: false, depth: false, powerPreference: 'low-power' });
  if (!gl) throw new Error('WebGL is unavailable.');
  const shaders = [];
  const textures = [];
  const framebuffers = [];
  let lineProgram, blitProgram, blurProgram, mixProgram, lineBuffer, quadBuffer, targets = [];
  const dispose = () => {
    for (const shader of shaders) gl.deleteShader(shader);
    for (const texture of textures) gl.deleteTexture(texture);
    for (const framebuffer of framebuffers) gl.deleteFramebuffer(framebuffer);
    if (lineBuffer) gl.deleteBuffer(lineBuffer);
    if (quadBuffer) gl.deleteBuffer(quadBuffer);
    if (lineProgram) gl.deleteProgram(lineProgram);
    if (blitProgram) gl.deleteProgram(blitProgram);
    if (blurProgram) gl.deleteProgram(blurProgram);
    if (mixProgram) gl.deleteProgram(mixProgram);
  };
  try {
    const lineVert = compile(gl, gl.VERTEX_SHADER, lineVertex);
    const lineFrag = compile(gl, gl.FRAGMENT_SHADER, lineFragment);
    const blitVert = compile(gl, gl.VERTEX_SHADER, blitVertex);
    const blurFrag = compile(gl, gl.FRAGMENT_SHADER, blurFragment);
    const copyFrag = compile(gl, gl.FRAGMENT_SHADER, copyFragment);
    const mixFrag = compile(gl, gl.FRAGMENT_SHADER, mixFragment);
    shaders.push(lineVert, lineFrag, blitVert, blurFrag, copyFrag, mixFrag);
    lineProgram = link(gl, lineVert, lineFrag);
    blurProgram = link(gl, blitVert, blurFrag);
    blitProgram = link(gl, blitVert, copyFrag);
    mixProgram = link(gl, blitVert, mixFrag);

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
    lineBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, lineBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    quadBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);

    const bounds = isoBounds(segments);
    const lineCount = vertices.length / 6;
    const lineUniforms = {};
    const bindLine = () => {
      gl.useProgram(lineProgram);
      gl.bindBuffer(gl.ARRAY_BUFFER, lineBuffer);
      const segment = gl.getAttribLocation(lineProgram, 'a_segment');
      const corner = gl.getAttribLocation(lineProgram, 'a_corner');
      gl.enableVertexAttribArray(segment);
      gl.enableVertexAttribArray(corner);
      gl.vertexAttribPointer(segment, 4, gl.FLOAT, false, 24, 0);
      gl.vertexAttribPointer(corner, 2, gl.FLOAT, false, 24, 16);
    };
    const bindQuad = program => {
      gl.useProgram(program);
      gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);
      const pos = gl.getAttribLocation(program, 'a_pos');
      gl.enableVertexAttribArray(pos);
      gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);
    };

    gl.useProgram(lineProgram);
    for (const name of ['time', 'resolution', 'stroke', 'fit', 'turn', 'waveFreq', 'focus', 'ink', 'focusLimit', 'edgeFade', 'edgeBand', 'crestLo', 'crestHi', 'crestGate', 'horizon']) {
      lineUniforms[name] = gl.getUniformLocation(lineProgram, `u_${name}`);
    }
    gl.uniform3f(lineUniforms.ink, ...INK);
    gl.uniform1f(lineUniforms.turn, FIELD_TURN);
    gl.uniform1f(lineUniforms.waveFreq, WAVE_FREQ);
    gl.uniform1f(lineUniforms.edgeBand, EDGE_BAND);
    gl.uniform1f(lineUniforms.crestLo, CREST_LO);
    gl.uniform1f(lineUniforms.crestHi, CREST_HI);
    gl.uniform1f(lineUniforms.horizon, HORIZON_CLIP);
    gl.uniform2f(lineUniforms.focus, VIEW_BOUNDS.maxY, VIEW_BOUNDS.minY);
    gl.useProgram(mixProgram);
    gl.uniform3f(gl.getUniformLocation(mixProgram, 'u_canvas'), ...CANVAS);
    gl.uniform1f(gl.getUniformLocation(mixProgram, 'u_horizon'), HORIZON_CLIP);
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.clearColor(...CANVAS, 1);

    let aspect = 1, stroke = 1;
    const rebuildTargets = (width, height) => {
      for (const texture of textures) gl.deleteTexture(texture);
      for (const framebuffer of framebuffers) gl.deleteFramebuffer(framebuffer);
      textures.length = 0;
      framebuffers.length = 0;
      targets = [makeTarget(gl, width, height), makeTarget(gl, width, height), makeTarget(gl, width, height)];
      for (const target of targets) {
        textures.push(target.texture);
        framebuffers.push(target.framebuffer);
      }
    };
    const drawLines = (limit, seconds, edgeFade = 0, crestGate = 0) => {
      bindLine();
      gl.uniform1f(lineUniforms.time, seconds);
      gl.uniform1f(lineUniforms.focusLimit, limit);
      gl.uniform1f(lineUniforms.edgeFade, edgeFade);
      gl.uniform1f(lineUniforms.crestGate, crestGate);
      gl.drawArrays(gl.TRIANGLES, 0, lineCount);
    };
    const blit = (program, texture, texelX, texelY) => {
      bindQuad(program);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.uniform1i(gl.getUniformLocation(program, 'u_image'), 0);
      if (program === blurProgram) gl.uniform2f(gl.getUniformLocation(program, 'u_texel'), texelX, texelY);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    };

    return {
      resize() {
        const { width, height } = canvas.getBoundingClientRect();
        const ratio = Math.min(canvas.ownerDocument.defaultView.devicePixelRatio || 1, 2);
        canvas.width = Math.max(1, Math.round(width * ratio));
        canvas.height = Math.max(1, Math.round(height * ratio));
        aspect = Math.max(width, 1) / Math.max(height, 1);
        stroke = 1.05 * ratio;
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.useProgram(lineProgram);
        gl.uniform2f(lineUniforms.resolution, canvas.width, canvas.height);
        gl.uniform1f(lineUniforms.stroke, stroke);
        gl.uniform4f(lineUniforms.fit, ...fitGroundFrame(bounds, aspect, GROUND_ZOOM, FIELD_SHIFT_X, FIELD_SHIFT_Y));
        rebuildTargets(canvas.width, canvas.height);
      },
      render(seconds) {
        const { width, height } = canvas;
        const [scene, blurX, blurY] = targets;
        gl.bindFramebuffer(gl.FRAMEBUFFER, scene.framebuffer);
        gl.viewport(0, 0, width, height);
        gl.clear(gl.COLOR_BUFFER_BIT);
        drawLines(1.1, seconds);

        gl.bindFramebuffer(gl.FRAMEBUFFER, blurX.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        blit(blurProgram, scene.texture, BLUR_SPREAD / width, 0);

        gl.bindFramebuffer(gl.FRAMEBUFFER, blurY.framebuffer);
        gl.clear(gl.COLOR_BUFFER_BIT);
        blit(blurProgram, blurX.texture, 0, BLUR_SPREAD / height);

        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, width, height);
        gl.clear(gl.COLOR_BUFFER_BIT);
        bindQuad(mixProgram);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, blurY.texture);
        gl.uniform1i(gl.getUniformLocation(mixProgram, 'u_image'), 0);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, scene.texture);
        gl.uniform1i(gl.getUniformLocation(mixProgram, 'u_sharp'), 1);
        gl.uniform1f(gl.getUniformLocation(mixProgram, 'u_blurMix'), BLUR_MIX);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        drawLines(0.55, seconds, 1, 1);
      },
      dispose,
    };
  } catch (error) {
    dispose();
    throw error;
  }
}

export function mountCadastralSea(host, data, createRenderer = createCadastralSeaRenderer) {
  const doc = host.ownerDocument;
  const win = doc.defaultView;
  const canvas = doc.createElement('canvas');
  canvas.className = 'sw-cadastral-sea';
  canvas.setAttribute('aria-hidden', 'true');
  let renderer;
  try {
    renderer = createRenderer(canvas, data);
  } catch {
    return null;
  }
  host.prepend(canvas);
  host.classList.add('has-sea');
  let frame = 0, last = null, elapsed = 0;
  const resize = () => {
    renderer.resize();
    renderer.render(elapsed);
  };
  renderer.resize();
  renderer.render(0);
  const observer = typeof win.ResizeObserver === 'function' ? new win.ResizeObserver(resize) : null;
  observer?.observe(host);
  function tick(now) {
    elapsed += last === null ? 0 : Math.min((now - last) / 1000, 0.1);
    last = now;
    renderer.render(elapsed);
    frame = win.requestAnimationFrame(tick);
  }
  return {
    sync(paused, reduced) {
      win.cancelAnimationFrame(frame);
      frame = 0;
      last = null;
      if (reduced) {
        elapsed = 0;
        renderer.render(0);
      }
      if (!paused && !reduced) frame = win.requestAnimationFrame(tick);
    },
    dispose() {
      win.cancelAnimationFrame(frame);
      observer?.disconnect();
      renderer.dispose();
      canvas.remove();
      host.classList.remove('has-sea');
    },
  };
}
