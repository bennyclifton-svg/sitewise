import { VERT, FRAG } from './cloud-shader-source.js';

export function mountClouds(host) {
  const canvas = document.createElement('canvas');
  canvas.className = 'sw-cloud-shader';
  canvas.setAttribute('aria-hidden', 'true');
  const gl = canvas.getContext('webgl', { alpha: false, antialias: false });
  if (!gl) return () => {};
  const shaders = [];
  const program = gl.createProgram();
  const buffer = gl.createBuffer();
  const release = () => {
    shaders.forEach(shader => gl.deleteShader(shader));
    gl.deleteProgram(program);
    gl.deleteBuffer(buffer);
    canvas.remove();
  };
  if (!program || !buffer) { release(); return () => {}; }
  for (const [type, source] of [[gl.VERTEX_SHADER, VERT], [gl.FRAGMENT_SHADER, FRAG]]) {
    const shader = gl.createShader(type);
    if (!shader) { release(); return () => {}; }
    shaders.push(shader);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) { release(); return () => {}; }
    gl.attachShader(program, shader);
  }
  gl.bindAttribLocation(program, 0, 'a_pos');
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) { release(); return () => {}; }
  gl.useProgram(program);
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const uniform = name => gl.getUniformLocation(program, name);
  const time = uniform('u_time');
  const res = uniform('u_res');
  gl.uniform1f(uniform('u_count'), 6);
  gl.uniform3f(uniform('u_cloud'), 0.984, 0.973, 0.949);
  gl.uniform3f(uniform('u_skyTop'), 0.30, 0.57, 0.80);
  gl.uniform3f(uniform('u_skyBottom'), 0.92, 0.95, 0.97);
  // The sky occupies only the top third and fades into the cadastral sea.
  host.prepend(canvas);
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  let frame = 0, elapsed = 0, last = 0, visible = true, paused = false, lost = false;
  const draw = () => {
    gl.uniform1f(time, elapsed);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };
  const tick = now => {
    if (now - last >= 1000 / 30) {
      const speed = Number(host.dataset.cloudSpeed ?? 0.35);
      elapsed += Math.min((now - last) / 1000, 0.1) * (Number.isFinite(speed) ? Math.max(0, speed) : 0.35);
      last = now;
      draw();
    }
    frame = requestAnimationFrame(tick);
  };
  const sync = () => {
    cancelAnimationFrame(frame);
    if (lost) return;
    draw();
    if (!motion.matches && visible && !document.hidden && !paused) {
      last = performance.now();
      frame = requestAnimationFrame(tick);
    }
  };
  const resize = new ResizeObserver(() => {
    // A half-resolution field keeps the second animated backdrop inexpensive.
    canvas.width = Math.max(1, Math.round(canvas.clientWidth * 0.5));
    canvas.height = Math.max(1, Math.round(canvas.clientHeight * 0.5));
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.uniform2f(res, canvas.width, canvas.height);
    sync();
  });
  const intersection = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
  const pause = event => { paused = Boolean(event.detail); sync(); };
  const contextLost = event => { event.preventDefault(); lost = true; cancelAnimationFrame(frame); canvas.style.visibility = 'hidden'; };
  canvas.addEventListener('webglcontextlost', contextLost);
  resize.observe(canvas);
  intersection.observe(host);
  motion.addEventListener('change', sync);
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('sitewise:motion-pause', pause);
  return () => {
    cancelAnimationFrame(frame);
    resize.disconnect();
    intersection.disconnect();
    motion.removeEventListener('change', sync);
    document.removeEventListener('visibilitychange', sync);
    window.removeEventListener('sitewise:motion-pause', pause);
    release();
  };
}

const hero = document.querySelector('.sw-coordination');
if (hero) {
  let dispose = mountClouds(hero);
  window.addEventListener('pagehide', () => dispose());
  window.addEventListener('pageshow', event => { if (event.persisted) dispose = mountClouds(hero); });
}
