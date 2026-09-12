const hero = document.querySelector('#sitewise-landing .sw-coordination');
const word = hero?.querySelector('[data-building-word]');
const detail = hero?.querySelector('.sw-detail-reveal');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

async function animateHeadline() {
  if (!word || !detail || reducedMotion.matches || !word.animate) return;
  await document.fonts.load('600 56px "Manifa Advertising"');
  if (reducedMotion.matches || window.scrollY > hero.clientHeight / 2) return;

  const bounds = hero.getBoundingClientRect();
  const style = getComputedStyle(word);
  const mobile = bounds.width < 800;
  const stage = document.createElement('div');
  stage.className = 'sw-letter-stage';
  stage.setAttribute('aria-hidden', 'true');
  for (const property of ['fontFamily', 'fontSize', 'fontWeight', 'fontFeatureSettings', 'letterSpacing', 'textTransform', 'color']) {
    stage.style[property] = style[property];
  }
  stage.style.lineHeight = '1';
  hero.append(stage);

  // Measure the intact word so the final handoff retains the font's kerning.
  const range = document.createRange();
  const lines = [...hero.querySelectorAll('[data-typed-line]')];
  const typing = typeHeadline(stage, lines, bounds);
  const animations = [...typing.animations];
  lines.forEach(line => { line.style.visibility = 'hidden'; });
  const heights = [0.27, 0.55, 0.36, 0.67, 0.29, 0.58, 0.4, 0.64];
  const scales = [1.65, 1.1, 1.35, 1.8, 1.2, 1.5, 1.15, 1.7];
  for (let index = 0; index < word.textContent.length; index++) {
    range.setStart(word.firstChild, index);
    range.setEnd(word.firstChild, index + 1);
    const target = range.getBoundingClientRect();
    const letter = document.createElement('span');
    letter.className = 'sw-building-letter';
    letter.textContent = word.textContent[index];
    stage.append(letter);
    // A Range measures the glyph line box; align the overlay using its own box.
    const glyph = letter.getBoundingClientRect();
    letter.style.left = `${target.left - bounds.left}px`;
    letter.style.top = `${target.top - bounds.top + (target.height - glyph.height) / 2}px`;
    const startX = bounds.width * (0.08 + index * 0.12) - target.left + bounds.left;
    const startY = (mobile ? 150 + heights[index] * 200 : bounds.height * heights[index]) - target.top + bounds.top;
    const scale = mobile ? 1 + (scales[index] - 1) * 0.35 : scales[index];
    const frames = Array.from({ length: 121 }, (_, step) => {
      const t = step / 120;
      // One counter-swing loses energy as it approaches the typeset position.
      const swing = Math.cos(t * Math.PI * 2) * Math.exp(-4 * t) * (1 - t) ** 2;
      const arc = Math.sin(t * Math.PI) * (1 - t) ** 2;
      return {
        opacity: step === 0 ? 0 : 1,
        transform: `translate(${startX * swing}px, ${startY * swing + arc * (index % 2 ? -65 : 65)}px) scale(${1 + (scale - 1) * swing})`,
      };
    });
    animations.push(letter.animate(frames, { id: 'sw-headline', duration: 2300, delay: typing.duration + index * 24, fill: 'both' }));
  }
  word.style.visibility = 'hidden';
  animations.push(detail.animate([
    { opacity: 0, filter: 'blur(12px)' },
    { opacity: 1, filter: 'blur(0px)' },
  ], { id: 'sw-headline', duration: 800, delay: typing.duration + 2000, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' }));

  function finish() {
    word.style.removeProperty('visibility');
    lines.forEach(line => line.style.removeProperty('visibility'));
    animations.forEach(animation => animation.cancel());
    stage.remove();
    window.removeEventListener('resize', finish);
    window.removeEventListener('pagehide', finish);
    window.removeEventListener('sitewise:motion-pause', onPause);
    reducedMotion.removeEventListener('change', finish);
  }
  function onPause(event) {
    if (event.detail) finish();
  }
  window.addEventListener('resize', finish, { once: true });
  window.addEventListener('pagehide', finish, { once: true });
  window.addEventListener('sitewise:motion-pause', onPause);
  reducedMotion.addEventListener('change', finish, { once: true });
  Promise.all(animations.map(animation => animation.finished)).then(finish, finish);
}

// Font or animation support failures leave the original, readable headline intact.
animateHeadline().catch(() => {});
import { typeHeadline } from './landing-headline-type.js';
