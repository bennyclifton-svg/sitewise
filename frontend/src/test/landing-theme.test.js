import { readFileSync } from 'node:fs';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mountTabletTheme } from '../../public/landing-assets/landing-theme.js';
import { mountLandingDemo } from '../../public/landing-assets/landing-sequence.js';

const html = readFileSync('public/landing.html', 'utf8');
let root, surround, toggle, cleanup, cleanupDemo;
const themeLabel = mode => `Switch tablet to ${mode} mode`;

beforeEach(() => {
  document.body.innerHTML = new DOMParser().parseFromString(html, 'text/html').body.innerHTML;
  root = document.getElementById('sitewise-landing');
  surround = root.querySelector('.sw-surround');
  toggle = surround.querySelector('[data-theme-toggle]');
});

afterEach(() => {
  cleanup?.(); cleanup = undefined;
  cleanupDemo?.(); cleanupDemo = undefined;
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});

describe('landing tablet theme', () => {
  it('ships a dark tablet and defaults to dark when mounting without an initial theme', () => {
    expect(surround.dataset.theme).toBe('dark');
    surround.removeAttribute('data-theme');
    cleanup = mountTabletTheme(surround);
    expect(surround.dataset.theme).toBe('dark');
    expect(toggle).toHaveAttribute('type', 'button');
    expect(toggle).toHaveAccessibleName(themeLabel('light'));
    expect(toggle).toHaveAttribute('title', themeLabel('light'));
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect(surround.querySelector('[data-nav-brand]').getAttribute('src')).toMatch(/sitewise-lockup-dark\.png$/);
  });

  it('uses a near-black tablet canvas and neutral panels without changing the light page', () => {
    const page = new DOMParser().parseFromString(html, 'text/html');
    const styles = [...page.querySelectorAll('link[rel="stylesheet"][href^="./"]')].map(link => {
      const style = document.createElement('style');
      const path = link.getAttribute('href').slice(2).split('?')[0];
      style.textContent = readFileSync(`public/${path}`, 'utf8');
      document.head.append(style);
      return style;
    });
    // jsdom keeps var() in computed backgrounds; follow the actual cascaded aliases.
    const background = element => {
      const style = getComputedStyle(element);
      let value = style.background;
      for (let depth = 0; depth < 8 && value.startsWith('var('); depth += 1) {
        value = style.getPropertyValue(value.slice(4, -1)).trim();
      }
      return value.toUpperCase();
    };
    const panels = ['.sw-nav', '.sw-repository', '.sw-console'].map(selector => surround.querySelector(selector));
    try {
      cleanup = mountTabletTheme(surround);
      expect(background(surround.querySelector('.sw-workspace'))).toBe('#0A0A0A');
      expect(panels.map(background)).toEqual(['#171717', '#171717', '#171717']);
      expect(background(document.body)).toBe('#F9F7F3');
      toggle.click();
      expect(background(surround.querySelector('.sw-workspace'))).toBe('#FDFCFA');
      expect(panels.map(background)).toEqual(['#F1EDE6', '#F1EDE6', '#F1EDE6']);
      expect(background(document.body)).toBe('#F9F7F3');
    } finally {
      for (const style of styles) style.remove();
    }
  });

  it('toggles with a native button click, Enter, and Space while preserving focus and labels', async () => {
    cleanup = mountTabletTheme(surround);
    const user = userEvent.setup();
    await user.click(toggle);
    expect(surround.dataset.theme).toBe('light');
    expect(toggle).toHaveAccessibleName(themeLabel('dark'));
    expect(toggle).toHaveAttribute('title', themeLabel('dark'));
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(surround.querySelector('[data-nav-brand]').getAttribute('src')).toMatch(/sitewise-lockup-light\.png$/);
    await user.keyboard('{Enter}');
    expect(surround.dataset.theme).toBe('dark');
    expect(toggle).toHaveAccessibleName(themeLabel('light'));
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await user.keyboard(' ');
    expect(surround.dataset.theme).toBe('light');
    await user.click(toggle);
    expect(surround.dataset.theme).toBe('dark');
    expect(toggle).toHaveFocus();
  });

  it.each(['cost', 'program'])('changes only the tablet theme while the %s demonstration continues', key => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance'] });
    let visibility;
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
    vi.stubGlobal('IntersectionObserver', class {
      constructor(callback) { visibility = callback; }
      observe() {}
      disconnect() {}
    });
    const outer = ['.sw-masthead', '.sw-coordination', '.sw-coordination-plan'].map(selector => document.querySelector(selector));
    const outerMarkup = outer.map(element => element.outerHTML);
    const outerTheme = [document.documentElement.getAttribute('data-theme'), document.documentElement.style.cssText, root.getAttribute('data-theme'), root.style.cssText];
    cleanup = mountTabletTheme(surround);
    cleanupDemo = mountLandingDemo(root);
    visibility([{ isIntersecting: true }]);
    root.querySelector(`.sw-nav [data-scene="${key}"]`).click();
    vi.advanceTimersByTime(7400);
    const content = root.querySelector(`[data-scene-content="${key}"]`);
    const view = content.querySelector('[data-document]');
    const built = () => content.querySelectorAll('[data-build-row].is-built').length;
    const progress = built();
    const prompt = root.querySelector('[data-prompt-live]').textContent;
    expect(progress).toBeGreaterThan(0);
    view.scrollTop = 137;
    toggle.click();
    expect(surround.dataset.theme).toBe('light');
    expect(root.dataset.activeScene).toBe(key);
    expect(root.querySelector(`[data-scene-content="${key}"]`)).toBe(content);
    expect(built()).toBe(progress);
    expect(view.scrollTop).toBe(137);
    expect(root.querySelector('[data-prompt-live]').textContent).toBe(prompt);
    expect(root.querySelector('[data-play]')).toHaveTextContent('Pause scene');
    vi.advanceTimersByTime(1000);
    expect(built()).toBeGreaterThan(progress);
    expect(outer.map(element => element.outerHTML)).toEqual(outerMarkup);
    expect([document.documentElement.getAttribute('data-theme'), document.documentElement.style.cssText, root.getAttribute('data-theme'), root.style.cssText]).toEqual(outerTheme);
  });

  it('removes its listener and restores the previous tablet, button and logo state on cleanup', () => {
    surround.dataset.theme = 'light';
    toggle.setAttribute('aria-label', 'Original control');
    toggle.removeAttribute('aria-pressed');
    toggle.removeAttribute('title');
    toggle.setAttribute('type', 'submit');
    const brand = surround.querySelector('[data-nav-brand]');
    brand.setAttribute('src', '/original-logo.png');
    const before = surround.outerHTML;
    cleanup = mountTabletTheme(surround);
    toggle.click();
    cleanup(); cleanup = undefined;
    expect(surround.outerHTML).toBe(before);
    toggle.click();
    expect(surround.outerHTML).toBe(before);
  });

  it('leaves a tablet without a theme control untouched', () => {
    toggle.remove();
    const before = surround.outerHTML;
    cleanup = mountTabletTheme(surround);
    cleanup(); cleanup = undefined;
    expect(surround.outerHTML).toBe(before);
  });
});
