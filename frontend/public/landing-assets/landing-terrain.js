import { createTerrainRenderer } from './terrain-renderer.js';
import { createVectorTerrainRenderer } from './vector-terrain-renderer.js';

export function mountTerrain(backdrop, toggle) {
  const doc = backdrop.ownerDocument, win = doc.defaultView;
  const source = backdrop.querySelector('img');
  const canvas = doc.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  backdrop.append(canvas);
  const preference = win.matchMedia('(prefers-reduced-motion: reduce)');
  const request = new win.AbortController();
  let renderer, frame = 0, last = null, sinceDraw = 0, elapsed = 0, ready = false, userPaused = false, pageAway = false;
  let vectorData = null, contextLost = false;

  function unavailable(error) {
    renderer?.dispose(); renderer = undefined; ready = false;
    backdrop.dataset.renderer = 'fallback';
    if (vectorData) {
      vectorData = null;
      console.warn('Vector landscape unavailable; using the original map.', error);
      initialise();
    } else {
      console.warn('Landscape animation unavailable; showing the original map.', error);
    }
    sync();
  }

  function tick(now) {
    frame = win.requestAnimationFrame(tick);
    const delta = last === null ? 0 : Math.min(now - last, 100);
    last = now;
    elapsed += delta / 1000;
    sinceDraw += delta;
    if (sinceDraw < 1000 / 30) return;
    // Retain the fractional frame so a 60 Hz display does not fall to 20 fps.
    sinceDraw %= 1000 / 30;
    try { renderer.render(elapsed); } catch (error) { unavailable(error); }
  }

  function sync() {
    win.cancelAnimationFrame(frame);
    frame = 0; last = null; sinceDraw = 0;
    const paused = !ready || userPaused || preference.matches || doc.hidden || pageAway;
    doc.documentElement.dataset.landscapePaused = String(paused);
    toggle.hidden = !ready || preference.matches;
    toggle.textContent = userPaused ? 'Resume landscape' : 'Pause landscape';
    toggle.setAttribute('aria-pressed', String(userPaused));
    if (!paused) frame = win.requestAnimationFrame(tick);
  }

  function resize() {
    if (!ready) return;
    try { renderer.resize(); renderer.render(elapsed); } catch (error) { unavailable(error); }
  }

  function initialise() {
    if (request.signal.aborted || contextLost || ready || !vectorData && !source.naturalWidth) return;
    try {
      renderer = vectorData ? createVectorTerrainRenderer(canvas, vectorData) : createTerrainRenderer(canvas, source);
      renderer.resize();
      renderer.render(elapsed);
      ready = true;
      backdrop.dataset.renderer = 'webgl';
    } catch (error) {
      unavailable(error);
      return;
    }
    sync();
  }

  async function loadVectors() {
    try {
      const response = await win.fetch(new URL('./cadastral-lines.json', import.meta.url), { signal: request.signal });
      if (!response.ok) throw new Error(`Cadastral map request failed (${response.status}).`);
      const data = await response.json();
      if (request.signal.aborted) return;
      vectorData = data;
      if (contextLost) return;
      renderer?.dispose(); renderer = undefined; ready = false;
      initialise();
    } catch (error) {
      if (!request.signal.aborted) console.warn('Cadastral vector map unavailable; retaining the original map.', error);
    }
  }

  const observer = new win.ResizeObserver(resize);
  observer.observe(backdrop);
  const onToggle = () => { userPaused = !userPaused; sync(); };
  const onPageHide = () => { pageAway = true; sync(); };
  const onPageShow = () => { pageAway = false; sync(); };
  const onLost = event => {
    event.preventDefault();
    ready = false; contextLost = true;
    renderer?.dispose(); renderer = undefined;
    backdrop.dataset.renderer = 'fallback';
    sync();
  };
  const onRestored = () => { contextLost = false; initialise(); };
  toggle.addEventListener('click', onToggle);
  doc.addEventListener('visibilitychange', sync);
  preference.addEventListener('change', sync);
  win.addEventListener('pagehide', onPageHide);
  win.addEventListener('pageshow', onPageShow);
  canvas.addEventListener('webglcontextlost', onLost);
  canvas.addEventListener('webglcontextrestored', onRestored);
  source.addEventListener('load', initialise);
  initialise();
  loadVectors();
  return () => {
    request.abort();
    ready = false; sync(); observer.disconnect();
    toggle.removeEventListener('click', onToggle);
    doc.removeEventListener('visibilitychange', sync);
    preference.removeEventListener('change', sync);
    win.removeEventListener('pagehide', onPageHide);
    win.removeEventListener('pageshow', onPageShow);
    canvas.removeEventListener('webglcontextlost', onLost);
    canvas.removeEventListener('webglcontextrestored', onRestored);
    source.removeEventListener('load', initialise);
    renderer?.dispose(); canvas.remove();
    delete backdrop.dataset.renderer;
  };
}

const backdrop = document.querySelector('.sw-cadastral-backdrop');
const toggle = document.querySelector('[data-landscape-toggle]');
if (backdrop && toggle) mountTerrain(backdrop, toggle);
