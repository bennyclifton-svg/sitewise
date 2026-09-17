export const promptMotion = {
  wordMs: 22,
  appearMs: 240,
  appearEase: 'cubic-bezier(.16, 1, .3, 1)',
  appearLift: '6px',
  retractStaggerMs: 11,
  retractMs: 160,
  retractEase: 'cubic-bezier(.7, 0, .92, .2)',
  sentencePause: 3.5,
  commaPause: 1.75,
  jitter: 0.15,
};

export function splitPromptWords(text) {
  return text.match(/\S+\s*/g) ?? (text ? [text] : []);
}

export function promptWordDelay(token, {
  base = promptMotion.wordMs,
  random = Math.random,
  sentencePause = promptMotion.sentencePause,
  commaPause = promptMotion.commaPause,
  jitter = promptMotion.jitter,
} = {}) {
  const word = token.trimEnd();
  let delay = base;
  if (/[.?!]["')\]]?$/.test(word)) delay *= sentencePause;
  else if (/[,;:]["')\]]?$/.test(word)) delay *= commaPause;
  return Math.max(1, Math.round(delay * (1 + (random() * 2 - 1) * jitter)));
}

function noopAnim() {
  return { finished: Promise.resolve(), cancel() {} };
}

function runAnimate(animate, element, keyframes, options) {
  const run = animate ?? ((el, kf, opt) => (typeof el.animate === 'function' ? el.animate(kf, opt) : noopAnim()));
  try {
    return run(element, keyframes, options) ?? noopAnim();
  } catch {
    return noopAnim();
  }
}

function appearFrames(lift) {
  return [
    { opacity: 0, transform: `translateY(${lift})` },
    { opacity: 1, transform: 'translateY(0)' },
  ];
}

function retractFrames(lift) {
  return [
    { opacity: 1, transform: 'translateY(0)' },
    { opacity: 0, transform: `translateY(${lift})` },
  ];
}

function ensureWords(field) {
  if (field.dataset.swWords === '1') return [...field.querySelectorAll('.sw-prompt-word')];
  const text = field.textContent;
  field.replaceChildren();
  for (const token of splitPromptWords(text)) {
    const span = document.createElement('span');
    span.className = 'sw-prompt-word is-pending';
    span.textContent = token;
    field.append(span);
  }
  field.dataset.swWords = '1';
  return [...field.querySelectorAll('.sw-prompt-word')];
}

function revealWords(words) {
  for (const word of words) {
    word.classList.remove('is-pending', 'is-retracting');
    word.style.opacity = '';
    word.style.transform = '';
  }
}

export function mountPromptExplorer(root, options = {}) {
  const {
    animate,
    sleep,
    random = Math.random,
    reducedMotion,
  } = options;

  const live = () => document.querySelector('.sw-prompt-explorer') || root;
  const previewOf = current => current.querySelector('.sw-prompt-preview');
  const prefersReduced = () => (
    reducedMotion
    ?? window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  const sizePreview = () => {
    const current = live();
    const preview = previewOf(current);
    current.style.minHeight = window.matchMedia('(min-width: 900px)').matches && preview
      ? `${preview.getBoundingClientRect().height}px`
      : '';
  };

  let playId = 0;
  const timers = new Set();
  const animations = new Set();

  const stopMotion = () => {
    playId += 1;
    for (const id of timers) clearTimeout(id);
    timers.clear();
    for (const anim of animations) {
      try { anim.cancel(); } catch { /* already finished */ }
    }
    animations.clear();
  };

  const waitMs = async (ms, token) => {
    if (sleep) {
      await sleep(ms);
      return token === playId;
    }
    await new Promise(resolve => {
      const id = setTimeout(() => {
        timers.delete(id);
        resolve();
      }, ms);
      timers.add(id);
    });
    return token === playId;
  };

  const play = async (element, keyframes, timing) => {
    const animation = runAnimate(animate, element, keyframes, timing);
    animations.add(animation);
    try {
      if (animation?.finished) await animation.finished;
    } catch {
      // cancelled
    } finally {
      animations.delete(animation);
    }
  };

  const playField = async (field, token) => {
    if (!field || prefersReduced()) return;
    const words = ensureWords(field);
    for (const word of words) {
      word.classList.add('is-pending');
      word.classList.remove('is-retracting');
    }
    for (let i = 0; i < words.length; i += 1) {
      if (token !== playId) return;
      const word = words[i];
      word.classList.remove('is-pending');
      play(word, appearFrames(promptMotion.appearLift), {
        duration: promptMotion.appearMs,
        easing: promptMotion.appearEase,
        fill: 'forwards',
      });
      if (i < words.length - 1) {
        const ok = await waitMs(promptWordDelay(word.textContent, { random }), token);
        if (!ok) return;
      }
    }
  };

  const retractField = async (field, token) => {
    if (!field || prefersReduced()) return;
    const words = [...field.querySelectorAll('.sw-prompt-word:not(.is-pending)')];
    if (!words.length) return;
    for (let i = words.length - 1; i >= 0; i -= 1) {
      if (token !== playId) return;
      const word = words[i];
      word.classList.add('is-retracting');
      play(word, retractFrames(promptMotion.appearLift), {
        duration: promptMotion.retractMs,
        easing: promptMotion.retractEase,
        fill: 'forwards',
      });
      if (i > 0) {
        const ok = await waitMs(promptMotion.retractStaggerMs, token);
        if (!ok) return;
      }
    }
    if (token === playId) await waitMs(promptMotion.retractMs, token);
    if (token !== playId) return;
    for (const word of words) {
      word.classList.add('is-pending');
      word.classList.remove('is-retracting');
    }
  };

  const paintChrome = (current, category, promptId) => {
    current.querySelectorAll('.sw-prompt-nav button[data-sw-category]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.getAttribute('data-sw-category') === category));
    });
    current.querySelectorAll('.sw-prompt-switch').forEach(group => {
      const active = group.getAttribute('data-sw-category') === category;
      group.hidden = !active;
      group.querySelectorAll('button[data-sw-prompt]').forEach(button => {
        button.setAttribute('aria-pressed', String(active && button.getAttribute('data-sw-prompt') === promptId));
      });
    });
  };

  const showPanel = (current, promptId) => {
    current.querySelectorAll('.sw-prompt-panel').forEach(panel => {
      panel.hidden = panel.getAttribute('data-sw-panel') !== promptId;
    });
    sizePreview();
  };

  const show = (category, promptId) => {
    const current = live();
    const outgoing = current.querySelector('.sw-prompt-panel:not([hidden])');
    paintChrome(current, category, promptId);
    if (outgoing?.getAttribute('data-sw-panel') === promptId) return;

    if (prefersReduced()) {
      stopMotion();
      showPanel(current, promptId);
      const field = current.querySelector('.sw-prompt-panel:not([hidden]) .sw-example-field');
      if (field?.dataset.swWords === '1') revealWords(field.querySelectorAll('.sw-prompt-word'));
      return;
    }

    stopMotion();
    const token = playId;
    const incomingField = current.querySelector(`.sw-prompt-panel[data-sw-panel="${promptId}"] .sw-example-field`);
    const outgoingField = outgoing?.querySelector('.sw-example-field');

    (async () => {
      if (outgoingField) await retractField(outgoingField, token);
      if (token !== playId) return;
      showPanel(current, promptId);
      await playField(incomingField, token);
    })();
  };

  const onClick = event => {
    const origin = event.target instanceof Element ? event.target : event.target.parentElement;
    const current = origin?.closest('.sw-prompt-explorer');
    if (!current) return;
    const categoryButton = origin.closest('.sw-prompt-nav button[data-sw-category]');
    if (categoryButton) {
      const category = categoryButton.getAttribute('data-sw-category');
      const first = current.querySelector(`.sw-prompt-switch[data-sw-category="${category}"] button[data-sw-prompt]`);
      show(category, first.getAttribute('data-sw-prompt'));
      return;
    }
    const promptButton = origin.closest('.sw-prompt-switch button[data-sw-prompt]');
    if (promptButton) {
      show(promptButton.closest('.sw-prompt-switch').getAttribute('data-sw-category'), promptButton.getAttribute('data-sw-prompt'));
      return;
    }
    const mode = origin.closest('[data-example-mode]');
    if (!mode || !current.contains(mode)) return;
    mode.closest('.sw-example-depth').querySelectorAll('button').forEach(button => {
      button.setAttribute('aria-pressed', String(button === mode));
    });
  };

  document.addEventListener('click', onClick, true);
  const observer = new ResizeObserver(sizePreview);
  const preview = previewOf(live());
  if (preview) observer.observe(preview);
  sizePreview();

  const current = live();
  let visibility;
  if (prefersReduced()) {
    current.classList.add('is-prompt-ready');
  } else {
    current.querySelectorAll('.sw-example-field').forEach(ensureWords);
    current.classList.add('is-prompt-ready');
    const startVisible = () => {
      playField(current.querySelector('.sw-prompt-panel:not([hidden]) .sw-example-field'), playId);
    };
    // Tests inject animate/sleep and need an immediate play. In the page, wait
    // until the explorer is on screen so offscreen WAAPI does not freeze at 0.
    if (typeof IntersectionObserver === 'function' && !animate && !sleep) {
      visibility = new IntersectionObserver(([entry]) => {
        if (!entry?.isIntersecting) return;
        startVisible();
        visibility.disconnect();
      }, { threshold: 0.2 });
      visibility.observe(current);
    } else {
      startVisible();
    }
  }

  return () => {
    stopMotion();
    visibility?.disconnect();
    document.removeEventListener('click', onClick, true);
    observer.disconnect();
  };
}

const explorer = document.querySelector('.sw-prompt-explorer');
if (explorer) mountPromptExplorer(explorer);
