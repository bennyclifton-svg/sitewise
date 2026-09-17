export const headlineHand = {
  font: 'Allison',
  color: '#087ac9',
  text: 'in detail.',
  comma: ',',
  rotate: -6,
  commaMs: 140,
  writeMs: 360,
  hiddenClip: 'inset(-0.55em 100% -0.45em -0.2em)',
  openClip: 'inset(-0.55em -0.25em -0.45em -0.2em)',
};

function wait(ms, sleep) {
  return (sleep ?? (delay => new Promise(resolve => setTimeout(resolve, delay))))(ms);
}

export function createHeadlineHand({ drawn = false } = {}) {
  const root = document.createElement('span');
  root.className = 'sw-headline-hand';
  const comma = document.createElement('span');
  comma.className = 'sw-headline-hand-comma';
  comma.dataset.hand = 'comma';
  comma.textContent = headlineHand.comma;
  const words = document.createElement('span');
  words.className = 'sw-headline-hand-words';
  words.dataset.hand = 'words';
  words.textContent = ` ${headlineHand.text}`;
  if (!drawn) {
    comma.style.clipPath = headlineHand.hiddenClip;
    words.style.clipPath = headlineHand.hiddenClip;
  }
  root.append(comma, words);
  return root;
}

export function finishHeadlineHand(slot) {
  if (!slot) return null;
  const hand = createHeadlineHand({ drawn: true });
  slot.replaceChildren(hand);
  slot.hidden = false;
  return hand;
}

export function clearHeadlineHand(slot) {
  if (!slot) return;
  slot.hidden = true;
  slot.replaceChildren();
}

async function draw(run, element, from, to, duration) {
  element.style.clipPath = from;
  const animation = run(element, [
    { clipPath: from },
    { clipPath: to },
  ], {
    id: 'sw-headline',
    duration,
    easing: 'linear',
    fill: 'forwards',
  });
  try {
    if (animation?.finished) await animation.finished;
  } catch {
    return false;
  }
  return true;
}

export async function playHeadlineHand(slot, { animate, sleep, reducedMotion, signal } = {}) {
  if (!slot) return;
  if (reducedMotion || signal?.aborted) {
    finishHeadlineHand(slot);
    return;
  }

  const hand = createHeadlineHand({ drawn: false });
  slot.replaceChildren(hand);
  slot.hidden = false;

  const run = animate ?? ((element, keyframes, options) => element.animate(keyframes, options));
  const comma = hand.querySelector('[data-hand=comma]');
  const words = hand.querySelector('[data-hand=words]');

  const wroteComma = await draw(run, comma, headlineHand.hiddenClip, headlineHand.openClip, headlineHand.commaMs);
  if (!wroteComma || signal?.aborted) {
    finishHeadlineHand(slot);
    return;
  }
  await wait(70, sleep);
  if (signal?.aborted) {
    finishHeadlineHand(slot);
    return;
  }
  const wroteWords = await draw(run, words, headlineHand.hiddenClip, headlineHand.openClip, headlineHand.writeMs);
  if (!wroteWords || signal?.aborted) finishHeadlineHand(slot);
}
