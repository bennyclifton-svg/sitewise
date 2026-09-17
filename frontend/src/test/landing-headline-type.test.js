import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { headlineHand } from '../../public/landing-assets/landing-headline-hand.js';
import { headlineType, playHeadlineType, typeDelay } from '../../public/landing-assets/landing-headline-type.js';

const headlineCss = readFileSync('public/landing-assets/landing-headlines.css', 'utf8');

afterEach(() => {
  document.body.innerHTML = '';
});

function headline() {
  document.body.innerHTML = `
    <h1>
      <span class="sw-headline-sizer">
        <span class="sw-headline-static">Understand the whole</span>
        <span class="sw-headline-suffix">neighborhood, site, and building<span class="sw-headline-hand-slot"> in detail.</span></span>
      </span>
      <span class="sw-headline-live">
        <span class="sw-headline-static">Understand the whole</span>
        <span class="sw-headline-suffix">
          <span class="sw-headline-typed"></span>
          <span class="sw-headline-cursor"></span>
          <span class="sw-headline-hand-slot" hidden></span>
        </span>
      </span>
    </h1>
  `;
  return document.querySelector('h1');
}

function typedText(root) {
  return [...root.querySelectorAll('.sw-headline-live .sw-headline-char')].map(node => node.textContent).join('');
}

function play(root, extras = {}) {
  const calls = [];
  const modes = [];
  return {
    calls,
    modes,
    done: playHeadlineType(root, {
      loop: false,
      sleep: async () => {
        modes.push(root.querySelector('.sw-headline-cursor')?.dataset.mode);
      },
      animate(element, frames, options) {
        calls.push({ element, frames, options });
        return { finished: Promise.resolve(), cancel() {} };
      },
      ...extras,
    }),
  };
}

describe('headline type sequence', () => {
  it('keeps the trailing mark solid and out of the last line box', () => {
    expect(headlineCss).not.toMatch(/animation:\s*sw-headline-cursor/);
    expect(headlineCss).not.toMatch(/@keyframes sw-headline-cursor/);
    expect(headlineCss).toMatch(/\.sw-headline-cursor \{[^}]*margin: 0 0 0 -0\.1\d+em;/);
    expect(headlineCss).toMatch(/\.sw-headline-hand-slot \{[^}]*height: 1em;/);
    expect(headlineCss).toMatch(/\.sw-headline-hand \{[^}]*height: 0;/);
  });

  it('keeps the prefix still and widens the suffix from building out through the neighborhood', () => {
    expect(headlineType.prefix).toBe('Understand the whole');
    expect(headlineType.phrases).toEqual([
      'building',
      'site and building',
      'neighborhood, site, and building',
    ]);
    expect(headlineType.closer).toBe(' in detail.');
    expect(headlineType.final).toBe('Understand the whole neighborhood, site, and building in detail.');
  });

  it('eases longer strings so the middle types faster than the ends', () => {
    expect(typeDelay(16, 32)).toBeLessThan(typeDelay(0, 32));
    expect(typeDelay(16, 32)).toBeLessThan(typeDelay(31, 32));
    expect(typeDelay(16, 32)).toBeLessThan(typeDelay(4, 8));
  });

  it('spins, blurs and slides letters up, then writes the closer by hand', async () => {
    const root = headline();
    const { calls, modes, done } = play(root);
    await done;

    expect(typedText(root)).toBe('neighborhood, site, and building');
    expect(root.querySelector('.sw-headline-typed br')).toBeNull();
    expect(root.querySelector('.sw-headline-static').textContent).toBe('Understand the whole');
    expect(typedText(root)).not.toMatch(/\./);
    expect(root.querySelector('.sw-headline-cursor').hidden).toBe(true);
    expect(root.querySelector('.sw-headline-live .sw-headline-hand')).not.toBeNull();
    expect(root.querySelector('.sw-headline-sizer .sw-headline-hand')).not.toBeNull();
    expect(modes).toContain('ready');
    expect(modes).toContain('type');
    expect(modes).toContain('delete');

    const entering = calls.filter(call => call.frames[0].opacity === 0);
    const leaving = calls.filter(call => call.frames[0].opacity === 1);
    const hand = calls.filter(call => call.frames[0].clipPath);
    expect(entering).toHaveLength('building'.length + 'site and building'.length + 'neighborhood, site, and building'.length);
    expect(leaving).toHaveLength(0);
    expect(hand).toHaveLength(2);
    expect(hand[0].element.getAttribute('data-hand')).toBe('comma');
    expect(hand[0].frames[0].clipPath).toBe(headlineHand.hiddenClip);
    expect(hand[0].frames.at(-1).clipPath).toBe(headlineHand.openClip);
    expect(entering[0].frames[0].filter).toMatch(/blur\(/);
    expect(entering[0].frames[0].transform).toMatch(/rotateY\(/);
    expect(entering[0].frames[0].transform).toMatch(/translateY\(/);
    expect(entering[0].frames[0].transform).not.toMatch(/rotate\(/);
    expect(entering[0].frames.at(-1).transform).toMatch(/translateY\(0/);
    expect(entering[0].options.easing).toMatch(/cubic-bezier/);
    expect(entering.every(call => call.element.classList.contains('sw-headline-char'))).toBe(true);
  });

  it('repeats the sequence after the closer', async () => {
    const root = headline();
    const { done } = play(root, { loop: 2 });
    await done;
    expect(typedText(root)).toBe('neighborhood, site, and building');
    expect(root.querySelector('.sw-headline-live .sw-headline-hand')).not.toBeNull();
    expect(root.querySelector('.sw-headline-cursor').hidden).toBe(true);
  });

  it('clears the handwritten closer instantly before looping backspace', async () => {
    const root = headline();
    const liveHand = root.querySelector('.sw-headline-live .sw-headline-hand-slot');
    let handWasDrawn = false;
    let handPresentWhenDeleteStarted = null;

    await playHeadlineType(root, {
      loop: 2,
      sleep: async () => {
        if (liveHand.querySelector('.sw-headline-hand')) handWasDrawn = true;
        const cursor = root.querySelector('.sw-headline-cursor');
        if (handWasDrawn && cursor?.dataset.mode === 'delete' && handPresentWhenDeleteStarted === null) {
          handPresentWhenDeleteStarted = Boolean(liveHand.querySelector('.sw-headline-hand')) && !liveHand.hidden;
        }
      },
      animate() {
        return { finished: Promise.resolve(), cancel() {} };
      },
    });

    expect(handWasDrawn).toBe(true);
    expect(handPresentWhenDeleteStarted).toBe(false);
  });

  it('shows the finished sentence immediately when motion is reduced', async () => {
    const root = headline();
    const animate = vi.fn();
    await playHeadlineType(root, { reducedMotion: true, animate, sleep: async () => {} });
    expect(animate).not.toHaveBeenCalled();
    expect(typedText(root)).toBe('neighborhood, site, and building');
    expect(root.querySelector('.sw-headline-live .sw-headline-hand')).not.toBeNull();
    expect(root.querySelector('.sw-headline-cursor').hidden).toBe(true);
  });
});
