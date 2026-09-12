import { afterEach, describe, expect, it } from 'vitest';
import { playHeadlineMarks } from '../../public/landing-assets/landing-headline-marks.js';

afterEach(() => {
  document.body.innerHTML = '';
});

function hero() {
  document.body.innerHTML = `
    <section class="sw-coordination">
      <h1>
        <span class="sw-headline-line"><span class="sw-headline-ink"><span class="sw-headline-type">whole building</span></span></span>
      </h1>
    </section>
  `;
  return document.querySelector('.sw-coordination');
}

describe('headline marks', () => {
  it('only applies a wash and does not write site or draw marks', async () => {
    const root = hero();
    await playHeadlineMarks(root);
    expect(root.classList.contains('is-headline-washed')).toBe(true);
    expect(root.querySelector('.sw-headline-hand')).toBeNull();
    expect(root.querySelector('.sw-headline-scribble')).toBeNull();
    expect(root.querySelector('.sw-headline-squiggle')).toBeNull();
  });

  it('still washes when motion is reduced', async () => {
    const root = hero();
    await playHeadlineMarks(root, { reducedMotion: true });
    expect(root.classList.contains('is-headline-washed')).toBe(true);
  });
});
