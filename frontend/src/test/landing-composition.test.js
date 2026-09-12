import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mountComposition } from '../../public/landing-assets/landing-composition.js';

let opening, demo, preference, observer, width, cleanup;
const zoom = () => opening.style.getPropertyValue('--sw-device-zoom');

beforeEach(() => {
  document.body.innerHTML = '<section class="sw-opening"><div class="sw-demo"><div class="sw-device-scale"></div></div></section>';
  opening = document.querySelector('.sw-opening');
  demo = opening.querySelector('.sw-demo');
  width = 640;
  Object.defineProperty(demo, 'clientWidth', { configurable: true, get: () => width });
  preference = new EventTarget();
  preference.matches = true;
  vi.stubGlobal('matchMedia', vi.fn(() => preference));
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback) { this.callback = callback; this.observe = vi.fn(); this.disconnect = vi.fn(); observer = this; }
  });
});

afterEach(() => {
  cleanup?.(); cleanup = undefined;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});

describe('landing console composition', () => {
  it('fits the complete desktop device to its available width and updates on resize', () => {
    cleanup = mountComposition(opening);
    expect(matchMedia).toHaveBeenCalledExactlyOnceWith('(min-width: 900px)');
    expect(observer.observe).toHaveBeenCalledExactlyOnceWith(demo);
    expect(opening.dataset.composition).toBe('scaled');
    expect(Number(zoom())).toBe(0.5);
    width = 960;
    observer.callback();
    expect(Number(zoom())).toBe(0.75);
    expect(opening.dataset.composition).toBe('scaled');
  });

  it('returns to responsive flow below the desktop breakpoint or while the demo has no width', () => {
    preference.matches = false;
    cleanup = mountComposition(opening);
    expect(zoom()).toBe('');
    expect(opening.dataset.composition).toBeUndefined();
    preference.matches = true;
    preference.dispatchEvent(new Event('change'));
    expect(Number(zoom())).toBe(0.5);
    width = 0;
    observer.callback();
    expect(zoom()).toBe('');
    expect(opening.dataset.composition).toBeUndefined();
    width = 800;
    observer.callback();
    expect(Number(zoom())).toBe(0.625);
    preference.matches = false;
    preference.dispatchEvent(new Event('change'));
    expect(zoom()).toBe('');
    expect(opening.dataset.composition).toBeUndefined();
  });

  it.each([false, true])('cleans up listeners and restores prior inline state (existing: %s)', existing => {
    if (existing) {
      opening.style.setProperty('--sw-device-zoom', '0.8');
      opening.dataset.composition = 'preview';
    }
    const removeListener = vi.spyOn(preference, 'removeEventListener');
    cleanup = mountComposition(opening);
    cleanup(); cleanup = undefined;
    expect(observer.disconnect).toHaveBeenCalledOnce();
    expect(removeListener).toHaveBeenCalledWith('change', expect.any(Function));
    expect(zoom()).toBe(existing ? '0.8' : '');
    expect(opening.dataset.composition).toBe(existing ? 'preview' : undefined);
    width = 1000;
    preference.dispatchEvent(new Event('change'));
    expect(zoom()).toBe(existing ? '0.8' : '');
    expect(opening.dataset.composition).toBe(existing ? 'preview' : undefined);
  });

  it('does not install a scaler when the console wrapper is absent', () => {
    opening.querySelector('.sw-device-scale').remove();
    cleanup = mountComposition(opening);
    expect(matchMedia).not.toHaveBeenCalled();
    expect(opening.dataset.composition).toBeUndefined();
    expect(zoom()).toBe('');
  });
});
