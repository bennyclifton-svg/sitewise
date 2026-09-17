import { clearHeadlineHand, finishHeadlineHand, playHeadlineHand } from './landing-headline-hand.js';

export const headlineType = {
  prefix: 'Understand the whole',
  phrases: [
    'building',
    'site and building',
    'neighborhood, site, and building',
  ],
  closer: ' in detail.',
  typeMs: 78,
  deleteMs: 18,
  holdMs: 1800,
  blinkMs: 1400,
  readyMs: 180,
  char: {
    duration: 460,
    easing: 'cubic-bezier(.45, 0, .15, 1)',
    rotateY: '-80deg',
    perspective: '1.2em',
    lift: '0.22em',
    blur: '8px',
  },
};

headlineType.final = `${headlineType.prefix} ${headlineType.phrases.at(-1).replace(/\n/g, '')}${headlineType.closer}`;

export function typeDelay(index, length, base = headlineType.typeMs) {
  if (length <= 1) return base;
  const t = index / (length - 1);
  const rush = Math.sin(t * Math.PI);
  const depth = Math.min(0.62, 0.26 + length * 0.012);
  return Math.max(28, Math.round(base * (1 - depth * rush)));
}

function letter(ch) {
  const span = document.createElement('span');
  span.className = ch === ' ' ? 'sw-headline-char is-space' : 'sw-headline-char';
  span.textContent = ch;
  return span;
}

function lastChar(typed) {
  const chars = typed.querySelectorAll('.sw-headline-char');
  return chars[chars.length - 1] ?? null;
}

function appendChar(typed, ch) {
  if (ch === '\n') {
    typed.append(document.createElement('br'));
    return null;
  }
  const span = letter(ch);
  if (ch === ' ') {
    typed.append(span);
    return span;
  }
  let word = typed.lastElementChild;
  if (!word || word.className !== 'sw-headline-word') {
    word = document.createElement('span');
    word.className = 'sw-headline-word';
    typed.append(word);
  }
  word.append(span);
  return span;
}

function renderSuffix(typed, text) {
  typed.replaceChildren();
  for (const ch of text) appendChar(typed, ch);
}

function pose(char, { yaw, lift }) {
  return `perspective(${char.perspective}) rotateY(${yaw}) translateY(${lift})`;
}

function frames(char) {
  return [
    {
      opacity: 0,
      filter: `blur(${char.blur})`,
      transform: pose(char, { yaw: char.rotateY, lift: char.lift }),
    },
    {
      opacity: 1,
      filter: 'blur(0px)',
      transform: pose(char, { yaw: '0deg', lift: '0em' }),
    },
  ];
}

function wait(ms, sleep) {
  return (sleep ?? (delay => new Promise(resolve => setTimeout(resolve, delay))))(ms);
}

function repeatsFrom(loop) {
  if (loop === true || loop === undefined) return Infinity;
  if (loop === false) return 1;
  return Number(loop);
}

export async function playHeadlineType(headline, { animate, sleep, reducedMotion, signal, loop } = {}) {
  const typed = headline.querySelector('.sw-headline-typed');
  const cursor = headline.querySelector('.sw-headline-cursor');
  const liveHand = headline.querySelector('.sw-headline-live .sw-headline-hand-slot');
  const sizerHand = headline.querySelector('.sw-headline-sizer .sw-headline-hand-slot');
  if (!typed) return;

  finishHeadlineHand(sizerHand);
  const lastPhrase = headlineType.phrases.at(-1);
  const setCursor = mode => {
    if (cursor) cursor.dataset.mode = mode;
  };
  const attachHand = () => {
    if (liveHand && liveHand.parentElement !== typed) typed.append(liveHand);
  };
  const finish = () => {
    if (liveHand && liveHand.parentElement === typed) typed.after(liveHand);
    renderSuffix(typed, lastPhrase);
    attachHand();
    finishHeadlineHand(liveHand);
    if (cursor) {
      cursor.hidden = true;
      cursor.dataset.mode = 'type';
    }
  };

  if (reducedMotion || signal?.aborted) {
    finish();
    return;
  }

  const run = animate ?? ((element, keyframes, options) => element.animate(keyframes, options));
  const aborted = () => Boolean(signal?.aborted);
  const repeats = repeatsFrom(loop);

  async function typeText(text) {
    setCursor('ready');
    await wait(headlineType.readyMs, sleep);
    if (aborted()) return;
    setCursor('type');
    for (const [index, ch] of [...text].entries()) {
      if (aborted()) return;
      const span = appendChar(typed, ch);
      if (span) {
        run(span, frames(headlineType.char), {
          id: 'sw-headline',
          duration: headlineType.char.duration,
          easing: headlineType.char.easing,
          fill: 'both',
        });
      }
      await wait(typeDelay(index, text.length), sleep);
    }
  }

  async function deleteChars(count) {
    setCursor('delete');
    for (let i = 0; i < count; i += 1) {
      if (aborted()) return;
      const last = lastChar(typed);
      if (!last) break;
      const word = last.parentElement;
      last.remove();
      if (word !== typed && !word.childElementCount) word.remove();
      if (typed.lastChild?.nodeName === 'BR') typed.lastChild.remove();
      await wait(headlineType.deleteMs, sleep);
    }
  }

  for (let cycle = 0; cycle < repeats; cycle += 1) {
    if (liveHand && liveHand.parentElement === typed) typed.after(liveHand);
    typed.replaceChildren();
    clearHeadlineHand(liveHand);
    if (cursor) cursor.hidden = false;

    for (const [index, phrase] of headlineType.phrases.entries()) {
      if (index) await deleteChars(headlineType.phrases[index - 1].length);
      if (aborted()) return finish();
      await typeText(phrase);
      if (aborted()) return finish();
      await wait(headlineType.holdMs, sleep);
    }

    if (aborted()) return finish();
    await wait(headlineType.blinkMs, sleep);
    if (aborted()) return finish();
    if (cursor) cursor.hidden = true;
    attachHand();
    await playHeadlineHand(liveHand, { animate: run, sleep, signal });
    if (aborted()) return finish();
    await wait(headlineType.holdMs, sleep);
    if (aborted()) return finish();

    if (cycle + 1 < repeats) {
      clearHeadlineHand(liveHand);
      await deleteChars(typed.querySelectorAll('.sw-headline-char').length);
      if (aborted()) return finish();
    }
  }
}
