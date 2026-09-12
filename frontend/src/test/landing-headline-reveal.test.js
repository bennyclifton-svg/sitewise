import { afterEach, describe, expect, it, vi } from 'vitest';
import { headlineReveal, revealHeadlineLines } from '../../public/landing-assets/landing-headline-reveal.js';

afterEach(() => {
  document.body.innerHTML = '';
});

function lines() {
  document.body.innerHTML = `
    <h1>
      <span class="sw-headline-line"><span class="sw-headline-ink">Understand the</span></span>
      <span class="sw-headline-line"><span class="sw-headline-ink">whole building</span></span>
      <span class="sw-headline-line"><span class="sw-headline-ink">in detail.</span></span>
    </h1>
  `;
  return [...document.querySelectorAll('.sw-headline-line')];
}

describe('headline reveal', () => {
  it('uses one shared slide-up and bottom-led fade on every line', () => {
    const calls = [];
    revealHeadlineLines(lines(), {
      animate(element, frames, options) {
        calls.push({ element, frames, options });
        return { finished: Promise.resolve(), cancel() {} };
      },
    });

    expect(calls).toHaveLength(6);
    const lineDelays = [...document.querySelectorAll('.sw-headline-line')].map(line => (
      calls.find(call => call.element === line)?.options.delay
    ));
    expect(lineDelays[0]).toBe(0);
    expect(lineDelays[1]).toBe(headlineReveal.stagger);
    expect(lineDelays[2]).toBe(headlineReveal.stagger * 2);
    expect(headlineReveal.stagger).toBeGreaterThan(0);
    expect(calls.filter(call => call.element.classList.contains('sw-headline-ink')).map(call => call.options.delay)).toEqual(lineDelays);

    const mask = calls.find(call => call.element.classList.contains('sw-headline-line'));
    const slide = calls.find(call => call.element.classList.contains('sw-headline-ink'));
    expect(slide.options.duration).toBe(headlineReveal.duration);
    expect(mask.options.duration).toBe(headlineReveal.mask.duration);
    expect(mask.options.duration).toBeGreaterThan(slide.options.duration);
    const bezier = headlineReveal.mask.easing.match(/[\d.]+/g).map(Number);
    expect(bezier[0]).toBeGreaterThan(0.5);
    expect(bezier[3]).toBeLessThan(0.5);
    expect(mask.frames[0].maskPosition).toBe(headlineReveal.mask.from);
    expect(mask.frames.at(-1).maskPosition).toBe(headlineReveal.mask.to);
    expect(headlineReveal.mask.image).toMatch(/to top/);
    expect(headlineReveal.mask.feather).toBeGreaterThan(0.45);
    expect(slide.frames[0].transform).toBe(`translateY(${headlineReveal.shift})`);
    expect(slide.frames.at(-1).transform).toBe('translateY(0)');
  });

  it('does not type, blink a cursor, or scatter letters', () => {
    revealHeadlineLines(lines(), {
      animate() { return { finished: Promise.resolve(), cancel() {} }; },
    });
    expect(document.querySelector('.sw-type-cursor')).toBeNull();
    expect(document.querySelector('.sw-typed-copy')).toBeNull();
    expect(document.querySelector('.sw-building-letter')).toBeNull();
  });

  it('leaves the typeset lines alone when motion is reduced', () => {
    const animate = vi.fn();
    expect(revealHeadlineLines(lines(), { animate, reducedMotion: true })).toEqual([]);
    expect(animate).not.toHaveBeenCalled();
  });
});
