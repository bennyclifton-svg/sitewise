const PROMPTS = [
  "Select all basement documents and transmit to head contractor.",
  "Create a 30-line cost plan, cover authority fees, consultant costs, construction and contingency, budget 12 million construction.",
  "Evaluate EOT3 draft assessment and update program.",
  "Evaluate the electrical tender, prepare recommendation.",
  "Process all invoices received this month. Update the invoice list and the cost plan.",
  "Create a program with 20 activities covering planning, design, procurement, and construction. Total duration 24 months.",
  "Create a RFP for architecture, structural, civil, town planning, BCA, AC/PCA. Keep to two pages each.",
  "Prepare tender packs, then research and shortlist three subcontractors for the civil works, formwork, reinforcement fixing, concrete supply/place and scaffold.",
  "Evaluate tender submissions from civil subcontractors, prepare a 1 page recommendation.",
  "Evaluate the RFI from Council (in the inbox), prepare correspondence to all relevant consultants seeking their advice and action.",
];

const HOLD_MS = 1500;
const SLIDE = {
  duration: 720,
  easing: "cubic-bezier(0.55, 0.02, 0.18, 1)",
};

const stage = document.querySelector(".lp-device__stage");
const historyEl = document.querySelector("[data-prompt-history]");
const liveEl = document.querySelector("[data-prompt-live]");
const liveField = document.querySelector(".lp-console__field");
const liveTyped = document.querySelector(".lp-console__typed");
const caret = document.querySelector(".lp-prompt__caret");

if (!stage || !historyEl || !liveEl || !liveField || !liveTyped || !caret) {
  // Overlay is optional proof; the tablet image still stands without it.
} else {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let index = 0;
  let running = false;
  let visible = false;
  let timer = 0;
  const animations = new Set();

  function wait(ms) {
    return new Promise((resolve) => {
      timer = window.setTimeout(resolve, ms);
    });
  }

  function wordDelay(word) {
    const punct = /[.,]$/.test(word) ? 70 : 0;
    return Math.max(72, Math.min(170, 56 + word.length * 11 + punct));
  }

  function typeWords(text) {
    const words = text.split(/\s+/);
    return new Promise((resolve) => {
      let n = 0;
      const tick = () => {
        if (!running) {
          resolve();
          return;
        }
        n += 1;
        liveEl.textContent = words.slice(0, n).join(" ");
        if (n >= words.length) {
          resolve();
          return;
        }
        timer = window.setTimeout(tick, wordDelay(words[n - 1]));
      };
      liveEl.textContent = "";
      tick();
    });
  }

  function playAnim(el, keyframes, options) {
    const anim = el.animate(keyframes, { ...options, fill: "forwards" });
    animations.add(anim);
    return anim.finished.finally(() => {
      animations.delete(anim);
    });
  }

  function stopTimers() {
    window.clearTimeout(timer);
    for (const anim of animations) anim.cancel();
    animations.clear();
  }

  function makeLine(text) {
    const line = document.createElement("p");
    line.className = "lp-prompt__line";
    line.textContent = text;
    return line;
  }

  async function promote(text) {
    const older = historyEl.firstElementChild;
    const olderTop = older ? older.getBoundingClientRect().top : 0;
    const line = makeLine(text);
    historyEl.appendChild(line);

    const from = liveField.getBoundingClientRect();
    const to = line.getBoundingClientRect();
    const dy = from.top - to.top;
    const olderJump = older ? olderTop - older.getBoundingClientRect().top : 0;

    const movers = [
      playAnim(
        line,
        [
          { transform: `translateY(${dy}px)`, opacity: 1 },
          { transform: `translateY(${dy * 0.45}px)`, opacity: 0.78 },
          { transform: "translateY(0)", opacity: 0.5 },
        ],
        SLIDE,
      ),
      playAnim(
        liveTyped,
        [
          { transform: "translateY(0)", opacity: 1 },
          { transform: "translateY(-38%)", opacity: 0.4 },
          { transform: "translateY(-110%)", opacity: 0 },
        ],
        SLIDE,
      ),
    ];

    if (older) {
      const rise = older.getBoundingClientRect().height + 14;
      movers.push(
        playAnim(
          older,
          [
            { transform: `translateY(${olderJump}px)`, opacity: 0.5 },
            { transform: `translateY(${olderJump - rise * 0.55}px)`, opacity: 0.22 },
            { transform: `translateY(${olderJump - rise * 1.4}px)`, opacity: 0 },
          ],
          SLIDE,
        ),
      );
    }

    try {
      await Promise.all(movers);
    } catch {
      // cancelled when the tablet leaves view
    }

    if (older) older.remove();
    liveTyped.getAnimations().forEach((anim) => anim.cancel());
    liveEl.textContent = "";
    liveTyped.style.transform = "";
    liveTyped.style.opacity = "";
  }

  async function play() {
    while (running) {
      caret.hidden = false;
      const text = PROMPTS[index];
      if (liveEl.textContent !== text) {
        await typeWords(text);
        if (!running) return;
      }
      await wait(HOLD_MS);
      if (!running) return;
      caret.hidden = true;
      await promote(text);
      if (!running) return;
      index = (index + 1) % PROMPTS.length;
    }
  }

  function start() {
    if (running || reduced) return;
    running = true;
    stopTimers();
    historyEl.replaceChildren();
    liveEl.textContent = "";
    liveTyped.style.transform = "";
    liveTyped.style.opacity = "";
    play();
  }

  function pause() {
    running = false;
    stopTimers();
    caret.hidden = true;
    historyEl.replaceChildren();
    liveEl.textContent = PROMPTS[index];
    liveTyped.style.transform = "";
    liveTyped.style.opacity = "";
  }

  function sync() {
    const on = visible && !document.hidden;
    if (on) start();
    else if (running) pause();
  }

  if (reduced) {
    caret.hidden = true;
    liveEl.textContent = PROMPTS[0];
  } else {
    caret.hidden = false;
    liveEl.textContent = "";
    const io = new IntersectionObserver(
      ([entry]) => {
        visible = Boolean(entry?.isIntersecting);
        sync();
      },
      { threshold: 0.35 },
    );
    io.observe(stage);
    document.addEventListener("visibilitychange", sync);
  }
}
