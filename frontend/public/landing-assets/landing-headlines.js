import { revealHeadlineLines } from './landing-headline-reveal.js';
import { playHeadlineMarks } from './landing-headline-marks.js';

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

export async function mountHeadline(root = document) {
  const hero = root.querySelector('#sitewise-landing .sw-coordination') ?? root.querySelector('.sw-coordination');
  const lines = [...(hero?.querySelectorAll('.sw-headline-line') ?? [])];
  if (!hero || !lines.length) return;

  const ready = () => hero.classList.add('is-headline-ready');
  const instant = () => reducedMotion.matches || typeof lines[0].animate !== 'function';
  const clearInline = () => {
    lines.forEach(line => {
      line.removeAttribute('style');
      line.querySelector('.sw-headline-ink')?.removeAttribute('style');
    });
  };

  if (instant()) {
    ready();
    await playHeadlineMarks(hero, { reducedMotion: true });
    return;
  }

  try {
    await document.fonts?.ready;
    if (instant() || window.scrollY > hero.clientHeight / 2) {
      ready();
      await playHeadlineMarks(hero, { reducedMotion: true });
      return;
    }

    const animations = revealHeadlineLines(lines);
    let aborted = false;
    function detach() {
      window.removeEventListener('resize', abort);
      window.removeEventListener('pagehide', abort);
      window.removeEventListener('sitewise:motion-pause', onPause);
      reducedMotion.removeEventListener('change', abort);
    }
    function abort() {
      if (aborted) return;
      aborted = true;
      animations.forEach(animation => animation?.cancel?.());
      clearInline();
      playHeadlineMarks(hero, { reducedMotion: true });
      detach();
    }
    function onPause(event) {
      if (event.detail) abort();
    }

    window.addEventListener('resize', abort, { once: true });
    window.addEventListener('pagehide', abort, { once: true });
    window.addEventListener('sitewise:motion-pause', onPause);
    reducedMotion.addEventListener('change', abort, { once: true });

    await Promise.all(animations.map(animation => animation?.finished).filter(Boolean)).catch(() => {});
    clearInline();
    if (!aborted) {
      await playHeadlineMarks(hero, { reducedMotion: instant() });
      detach();
    }
  } finally {
    ready();
  }
}

mountHeadline().catch(() => {});
