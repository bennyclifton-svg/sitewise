import { playHeadlineType } from './landing-headline-type.js';
import { playHeadlineMarks } from './landing-headline-marks.js';

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

export async function mountHeadline(root = document) {
  const hero = root.querySelector('#sitewise-landing .sw-coordination') ?? root.querySelector('.sw-coordination');
  const headline = hero?.querySelector('#sw-hero-title') ?? hero?.querySelector('h1');
  if (!hero || !headline) return;

  const ready = () => hero.classList.add('is-headline-ready');
  const instant = () => reducedMotion.matches || typeof headline.animate !== 'function';

  try {
    await document.fonts?.ready;
  } catch {
    // Keep the closer readable even if the font enumerator is missing.
  }

  if (instant()) {
    await playHeadlineType(headline, { reducedMotion: true });
    ready();
    await playHeadlineMarks(hero, { reducedMotion: true });
    return;
  }

  try {
    if (instant() || window.scrollY > hero.clientHeight / 2) {
      await playHeadlineType(headline, { reducedMotion: true });
      ready();
      await playHeadlineMarks(hero, { reducedMotion: true });
      return;
    }

    const controller = new AbortController();
    function detach() {
      window.removeEventListener('resize', abort);
      window.removeEventListener('pagehide', abort);
      window.removeEventListener('sitewise:motion-pause', onPause);
      reducedMotion.removeEventListener('change', abort);
    }
    function abort() {
      if (controller.signal.aborted) return;
      controller.abort();
      detach();
    }
    function onPause(event) {
      if (event.detail) abort();
    }

    window.addEventListener('resize', abort, { once: true });
    window.addEventListener('pagehide', abort, { once: true });
    window.addEventListener('sitewise:motion-pause', onPause);
    reducedMotion.addEventListener('change', abort, { once: true });

    await playHeadlineMarks(hero, { reducedMotion: false });
    await playHeadlineType(headline, { signal: controller.signal });
    if (!controller.signal.aborted) detach();
  } finally {
    ready();
  }
}

mountHeadline().catch(() => {});
