import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createTerrainRenderer } from '../../public/landing-assets/terrain-renderer.js';
import { createVectorTerrainRenderer } from '../../public/landing-assets/vector-terrain-renderer.js';
import { mountTerrain } from '../../public/landing-assets/landing-terrain.js';

vi.mock('../../public/landing-assets/terrain-renderer.js', () => ({ createTerrainRenderer: vi.fn() }));
vi.mock('../../public/landing-assets/vector-terrain-renderer.js', () => ({ createVectorTerrainRenderer: vi.fn() }));

let backdrop, toggle, source, renderer, vectorRenderer, cleanup, preference, observer, hidden, resolveFetch, rejectFetch;
const vectorMap = { version: 1, source: { width: 5504, height: 3072 }, lines: [[[0.1, 0.2], [0.3, 0.4]]] };
const timeRendered = target => target.render.mock.lastCall[0];
const advance = milliseconds => vi.advanceTimersByTime(milliseconds);

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance'] });
  document.body.innerHTML = '<div class="sw-cadastral-backdrop"><img src="/map.webp" alt=""></div><button data-landscape-toggle hidden></button>';
  backdrop = document.querySelector('.sw-cadastral-backdrop');
  toggle = document.querySelector('[data-landscape-toggle]');
  source = backdrop.querySelector('img');
  Object.defineProperty(source, 'naturalWidth', { configurable: true, value: 2200 });
  hidden = false;
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
  preference = new EventTarget();
  preference.matches = false;
  vi.stubGlobal('matchMedia', () => preference);
  vi.stubGlobal('requestAnimationFrame', callback => setTimeout(() => callback(performance.now()), 16));
  vi.stubGlobal('cancelAnimationFrame', clearTimeout);
  vi.stubGlobal('fetch', vi.fn(() => new Promise((resolve, reject) => { resolveFetch = resolve; rejectFetch = reject; })));
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback) { this.callback = callback; this.disconnect = vi.fn(); observer = this; }
    observe() {}
  });
  renderer = { resize: vi.fn(), render: vi.fn(), dispose: vi.fn() };
  vectorRenderer = { resize: vi.fn(), render: vi.fn(), dispose: vi.fn() };
  vi.mocked(createTerrainRenderer).mockReset().mockReturnValue(renderer);
  vi.mocked(createVectorTerrainRenderer).mockReset().mockReturnValue(vectorRenderer);
});

afterEach(() => {
  cleanup?.();
  cleanup = undefined;
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete document.hidden;
  delete document.documentElement.dataset.landscapePaused;
  document.body.innerHTML = '';
});

function mount() { cleanup = mountTerrain(backdrop, toggle); }
async function vectorsReady() {
  resolveFetch({ ok: true, json: async () => vectorMap });
  await vi.advanceTimersByTimeAsync(0);
}
function changePreference(matches) {
  preference.matches = matches;
  preference.dispatchEvent(new Event('change'));
}
function changeVisibility(value) {
  hidden = value;
  document.dispatchEvent(new Event('visibilitychange'));
}

describe('landing landscape lifecycle', () => {
  it('upgrades to vector lines without resetting landscape time or an explicit pause', async () => {
    expect(fetch).not.toHaveBeenCalled();
    mount();
    expect(createTerrainRenderer).toHaveBeenCalledOnce();
    expect(createVectorTerrainRenderer).not.toHaveBeenCalled();
    expect(fetch.mock.calls[0][0].pathname).toMatch(/\/cadastral-lines\.json$/);
    advance(320);
    toggle.click();
    const beforeUpgrade = timeRendered(renderer);
    await vectorsReady();
    expect(renderer.dispose).toHaveBeenCalledOnce();
    expect(createVectorTerrainRenderer).toHaveBeenCalledExactlyOnceWith(backdrop.querySelector('canvas'), vectorMap);
    expect(vectorRenderer.render).toHaveBeenCalledExactlyOnceWith(beforeUpgrade);
    expect(backdrop.dataset.renderer).toBe('webgl');
    expect(toggle).toHaveTextContent('Resume landscape');
    expect(vi.getTimerCount()).toBe(0);
    advance(30000);
    expect(vectorRenderer.render).toHaveBeenCalledOnce();
    toggle.click();
    advance(160);
    expect(timeRendered(vectorRenderer)).toBeGreaterThan(beforeUpgrade);
    expect(timeRendered(vectorRenderer) - beforeUpgrade).toBeLessThan(0.2);
    cleanup(); cleanup = undefined;
    expect(vectorRenderer.dispose).toHaveBeenCalledOnce();
    expect(renderer.dispose).toHaveBeenCalledOnce();
  });

  it.each(['network', 'http', 'json'])('retains the running raster if the vector request has a %s failure', async failure => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    mount();
    if (failure === 'network') rejectFetch(new Error('Offline'));
    else resolveFetch({ ok: failure !== 'http', status: 404, json: async () => { throw new Error('Invalid JSON'); } });
    await vi.advanceTimersByTimeAsync(0);
    expect(createVectorTerrainRenderer).not.toHaveBeenCalled();
    expect(renderer.dispose).not.toHaveBeenCalled();
    expect(backdrop.dataset.renderer).toBe('webgl');
    advance(160);
    expect(timeRendered(renderer)).toBeGreaterThan(0);
    expect(vi.getTimerCount()).toBe(1);
  });

  it.each(['create', 'render', 'resize'])('restores the raster at the current time if the vector renderer fails during %s', async failure => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    mount(); advance(320); toggle.click();
    const beforeUpgrade = timeRendered(renderer);
    const restored = { resize: vi.fn(), render: vi.fn(), dispose: vi.fn() };
    vi.mocked(createTerrainRenderer).mockReturnValue(restored);
    if (failure === 'create') vi.mocked(createVectorTerrainRenderer).mockImplementation(() => { throw new Error('Shader compile failed'); });
    await vectorsReady();
    if (failure === 'render') {
      vectorRenderer.render.mockImplementation(() => { throw new Error('Render failed'); });
      toggle.click(); advance(64);
    } else if (failure === 'resize') {
      vectorRenderer.resize.mockImplementation(() => { throw new Error('Resize failed'); });
      observer.callback();
    }
    expect(createTerrainRenderer).toHaveBeenCalledTimes(2);
    expect(renderer.dispose).toHaveBeenCalledOnce();
    if (failure !== 'create') expect(vectorRenderer.dispose).toHaveBeenCalledOnce();
    expect(timeRendered(restored)).toBeGreaterThanOrEqual(beforeUpgrade);
    expect(timeRendered(restored) - beforeUpgrade).toBeLessThan(0.05);
    expect(backdrop.dataset.renderer).toBe('webgl');
    expect(vi.getTimerCount()).toBe(failure === 'render' ? 1 : 0);
  });

  it('defers a pending vector upgrade during context loss and restores vector rendering after subsequent loss', async () => {
    mount(); advance(320);
    const canvas = backdrop.querySelector('canvas');
    const beforeLoss = timeRendered(renderer);
    canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
    await vectorsReady();
    expect(createVectorTerrainRenderer).not.toHaveBeenCalled();
    expect(backdrop.dataset.renderer).toBe('fallback');
    expect(vi.getTimerCount()).toBe(0);
    canvas.dispatchEvent(new Event('webglcontextrestored'));
    expect(vectorRenderer.render).toHaveBeenCalledExactlyOnceWith(beforeLoss);
    advance(160);
    const beforeSecondLoss = timeRendered(vectorRenderer);
    canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
    const restored = { resize: vi.fn(), render: vi.fn(), dispose: vi.fn() };
    vi.mocked(createVectorTerrainRenderer).mockReturnValue(restored);
    canvas.dispatchEvent(new Event('webglcontextrestored'));
    expect(createVectorTerrainRenderer).toHaveBeenCalledTimes(2);
    expect(restored.render).toHaveBeenCalledExactlyOnceWith(beforeSecondLoss);
    expect(createTerrainRenderer).toHaveBeenCalledOnce();
  });

  it.each(['resolve', 'reject'])('aborts vector loading and ignores a late %s after unmount', async outcome => {
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => {});
    mount();
    const signal = fetch.mock.calls[0][1].signal;
    expect(signal.aborted).toBe(false);
    cleanup(); cleanup = undefined;
    expect(signal.aborted).toBe(true);
    if (outcome === 'resolve') await vectorsReady();
    else { rejectFetch(new DOMException('Aborted', 'AbortError')); await vi.advanceTimersByTimeAsync(0); }
    expect(createVectorTerrainRenderer).not.toHaveBeenCalled();
    expect(warning).not.toHaveBeenCalled();
    expect(backdrop.querySelector('canvas')).toBeNull();
    expect(backdrop.dataset.renderer).toBeUndefined();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('sustains about 30 terrain frames per second without slowing the elapsed landscape time', () => {
    mount();
    renderer.render.mockClear();
    advance(5000);
    // Discarding every fractional RAF interval would produce only about 104 frames.
    expect(renderer.render.mock.calls.length).toBeGreaterThanOrEqual(148);
    expect(renderer.render.mock.calls.length).toBeLessThanOrEqual(150);
    expect(timeRendered(renderer)).toBeGreaterThan(4.94);
    expect(timeRendered(renderer)).toBeLessThanOrEqual(5);
  });

  it('pauses terrain time and resumes from the same position after a long pause', () => {
    mount();
    advance(320);
    const beforePause = timeRendered(renderer);
    expect(beforePause).toBeGreaterThan(0);
    toggle.click();
    expect(toggle).toHaveTextContent('Resume landscape');
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect(document.documentElement.dataset.landscapePaused).toBe('true');
    const renderCount = renderer.render.mock.calls.length;
    advance(60000);
    expect(renderer.render).toHaveBeenCalledTimes(renderCount);
    expect(vi.getTimerCount()).toBe(0);
    observer.callback();
    expect(timeRendered(renderer)).toBe(beforePause);
    toggle.click();
    expect(toggle).toHaveTextContent('Pause landscape');
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    advance(160);
    expect(timeRendered(renderer)).toBeGreaterThan(beforePause);
    expect(timeRendered(renderer) - beforePause).toBeLessThan(0.2);
  });

  it('stops scheduling when the document is hidden without counting hidden time', () => {
    mount();
    advance(320);
    const beforeHide = timeRendered(renderer);
    changeVisibility(true);
    const renderCount = renderer.render.mock.calls.length;
    expect(vi.getTimerCount()).toBe(0);
    advance(30000);
    expect(renderer.render).toHaveBeenCalledTimes(renderCount);
    changeVisibility(false);
    advance(160);
    expect(timeRendered(renderer)).toBeGreaterThan(beforeHide);
    expect(timeRendered(renderer) - beforeHide).toBeLessThan(0.2);
  });

  it('preserves an explicit pause when visibility and page navigation change', () => {
    mount();
    advance(160);
    toggle.click();
    changeVisibility(true);
    changeVisibility(false);
    window.dispatchEvent(new Event('pagehide'));
    window.dispatchEvent(new Event('pageshow'));
    expect(vi.getTimerCount()).toBe(0);
    expect(toggle).toHaveTextContent('Resume landscape');
    toggle.click();
    window.dispatchEvent(new Event('pagehide'));
    expect(vi.getTimerCount()).toBe(0);
    window.dispatchEvent(new Event('pageshow'));
    expect(vi.getTimerCount()).toBe(1);
  });

  it('renders a still without scheduling animation for reduced motion, including preference changes', () => {
    preference.matches = true;
    mount();
    expect(backdrop.dataset.renderer).toBe('webgl');
    expect(renderer.render).toHaveBeenCalledExactlyOnceWith(0);
    expect(toggle.hidden).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
    observer.callback();
    expect(timeRendered(renderer)).toBe(0);
    changePreference(false);
    expect(toggle.hidden).toBe(false);
    advance(320);
    expect(timeRendered(renderer)).toBeGreaterThan(0);
    changePreference(true);
    const renderCount = renderer.render.mock.calls.length;
    advance(30000);
    expect(renderer.render).toHaveBeenCalledTimes(renderCount);
    expect(vi.getTimerCount()).toBe(0);
    expect(toggle.hidden).toBe(true);
  });

  it('retains the original image and hides the motion control when WebGL is unavailable', () => {
    vi.mocked(createTerrainRenderer).mockImplementation(() => { throw new Error('WebGL is unavailable.'); });
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    mount();
    expect(backdrop.dataset.renderer).toBe('fallback');
    expect(backdrop.querySelector('img')).toBe(source);
    expect(source).toHaveAttribute('src', '/map.webp');
    expect(toggle.hidden).toBe(true);
    expect(document.documentElement.dataset.landscapePaused).toBe('true');
    expect(vi.getTimerCount()).toBe(0);
  });

  it('falls back on context loss and restores the terrain at its previous position', () => {
    mount();
    advance(320);
    const canvas = backdrop.querySelector('canvas');
    const beforeLoss = timeRendered(renderer);
    const lost = new Event('webglcontextlost', { cancelable: true });
    canvas.dispatchEvent(lost);
    expect(lost.defaultPrevented).toBe(true);
    expect(backdrop.dataset.renderer).toBe('fallback');
    expect(backdrop.querySelector('img')).toBe(source);
    expect(toggle.hidden).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
    advance(60000);
    const restored = { resize: vi.fn(), render: vi.fn(), dispose: vi.fn() };
    vi.mocked(createTerrainRenderer).mockReturnValue(restored);
    canvas.dispatchEvent(new Event('webglcontextrestored'));
    expect(createTerrainRenderer).toHaveBeenCalledTimes(2);
    expect(restored.render).toHaveBeenCalledExactlyOnceWith(beforeLoss);
    expect(backdrop.dataset.renderer).toBe('webgl');
    expect(toggle.hidden).toBe(false);
    advance(160);
    expect(timeRendered(restored)).toBeGreaterThan(beforeLoss);
    expect(timeRendered(restored) - beforeLoss).toBeLessThan(0.2);
  });

  it('waits for the source image and initializes it only once', () => {
    Object.defineProperty(source, 'naturalWidth', { configurable: true, value: 0 });
    mount();
    expect(createTerrainRenderer).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
    Object.defineProperty(source, 'naturalWidth', { configurable: true, value: 2200 });
    source.dispatchEvent(new Event('load'));
    source.dispatchEvent(new Event('load'));
    expect(createTerrainRenderer).toHaveBeenCalledExactlyOnceWith(backdrop.querySelector('canvas'), source);
    expect(backdrop.dataset.renderer).toBe('webgl');
  });

  it('removes listeners, scheduling, canvas and renderer resources when unmounted', () => {
    mount();
    const canvas = backdrop.querySelector('canvas');
    cleanup();
    cleanup = undefined;
    expect(renderer.dispose).toHaveBeenCalledOnce();
    expect(observer.disconnect).toHaveBeenCalledOnce();
    expect(backdrop.querySelector('canvas')).toBeNull();
    expect(backdrop.querySelector('img')).toBe(source);
    expect(backdrop.dataset.renderer).toBeUndefined();
    toggle.click();
    changeVisibility(false);
    changePreference(false);
    window.dispatchEvent(new Event('pageshow'));
    source.dispatchEvent(new Event('load'));
    canvas.dispatchEvent(new Event('webglcontextrestored'));
    expect(createTerrainRenderer).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });
});
