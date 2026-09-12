import { installControlScenes, setProgrammeScale } from './landing-controls.js';

function layoutTop(element) {
  let top = element.offsetTop;
  for (let parent = element.offsetParent; parent; parent = parent.offsetParent) {
    top += parent.offsetTop + parent.clientTop;
  }
  return top;
}

export function mountLandingDemo(root, { playAll = false, initialScene = 'pmp', repeatScene = false } = {}) {
  const doc = root.ownerDocument;
  const win = doc.defaultView;
  const find = selector => root.querySelector(selector);
  const prompt = find('[data-prompt-live]');
  const scenes = {
    pmp: { label: 'Project plan', title: 'Project management plan', content: find('[data-plan-content]'), create: prompt.textContent.trim(), update: 'Read the latest project documents. Update the project management plan.', sources: ['brief', 'handover', 'dp', 'title', 'planning', 'ground', 'preda', 'qs'] },
    ...installControlScenes(root),
  };
  const order = ['pmp', 'cost', 'program', 'procurement'];
  let sceneKey = 'pmp', scene = scenes.pmp;
  let documentView = scene.content.querySelector('[data-document]');
  let sections = [...documentView.querySelectorAll('.sw-pmp-section')];
  let request = scene.create, steps = [];
  const playButton = find('[data-play]');
  const resultButton = find('[data-show-result]');
  const motion = win.matchMedia('(prefers-reduced-motion: reduce)');
  const state = { index: 0, timer: null, due: 0, remaining: 0, running: false, done: false, visible: false, userPaused: false, runId: 0, autoScrollTarget: null, autoScrollUntil: 0 };
  const sources = Object.fromEntries([...root.querySelectorAll('[data-file]')].map(row => [row.dataset.file, [row.dataset.sourceTitle, row.dataset.sourceExcerpt]]));
  const sceneFind = selector => scene.content.querySelector(selector);
  const output = key => find(`[data-file="${key}"]`);
  const setStage = label => { find('[data-stage-label]').textContent = label; };
  const updateMode = () => find('[data-play-all]').setAttribute('aria-pressed', String(playAll));

  function showPlan() {
    root.removeAttribute('data-prompt-typing');
    scene.content.removeAttribute('inert');
    scene.content.removeAttribute('aria-hidden');
  }
  function highlight(key, accumulate = false) {
    root.querySelectorAll('[data-file]').forEach(row => {
      const selected = row.dataset.file === key || (accumulate && row.classList.contains('is-active'));
      row.classList.toggle('is-active', selected);
      row.querySelector('.sw-source').setAttribute('aria-pressed', String(selected));
    });
  }
  function revealHeading(section) {
    section.removeAttribute('data-heading-pending');
    section.removeAttribute('inert');
    section.removeAttribute('aria-hidden');
  }
  function reveal(section) {
    revealHeading(section);
    section.classList.add('is-filled');
    const content = section.querySelector('.sw-section-reveal');
    content?.removeAttribute('inert');
    content?.removeAttribute('aria-hidden');
  }
  function revealRow(row) {
    row.classList.add('is-built');
    row.removeAttribute('inert');
    row.removeAttribute('aria-hidden');
  }
  function follow(element) {
    if (!documentView.clientHeight) return;
    // Perspective changes screen rectangles, but scrollTop uses untransformed layout pixels.
    const elementTop = layoutTop(element) - layoutTop(documentView) - documentView.clientTop;
    const visibleTop = elementTop - documentView.scrollTop;
    const clearance = sceneKey === 'program' ? 94 : sceneKey === 'cost' ? 98 : sceneKey === 'procurement' ? 58 : 18;
    if (visibleTop + element.offsetHeight > documentView.clientHeight - 24 || visibleTop < clearance) {
      const top = Math.max(0, Math.min(documentView.scrollHeight - documentView.clientHeight, elementTop - clearance));
      state.autoScrollTarget = top;
      state.autoScrollUntil = win.performance.now() + 900;
      documentView.scrollTop = top;
    }
  }
  function complete() {
    state.done = true;
    state.running = playAll && !motion.matches;
    state.timer = null;
    showPlan();
    sections.forEach(reveal);
    documentView.querySelectorAll('[data-column-heading]').forEach(revealHeading);
    documentView.querySelectorAll('[data-build-row]').forEach(revealRow);
    documentView.querySelectorAll('[data-link-to]').forEach(link => link.classList.add('is-linked'));
    sceneFind('[data-final-reveal]')?.removeAttribute('data-final-pending');
    scene.complete?.();
    prompt.textContent = request;
    find('.sw-caret').hidden = true;
    output(sceneKey).hidden = false;
    highlight(sceneKey);
    documentView.setAttribute('aria-busy', 'false');
    setStage(`${scene.label} · ${sceneKey === 'pmp' ? 'draft complete' : 'complete'}`);
    find('[data-status]').textContent = sceneKey === 'procurement' ? 'Four consultant RFP drafts ready for review. Civil / stormwater engineer RFP open. No requests have been issued.' : `${scene.title} complete. ${sections.length} sections populated${sceneKey === 'program' ? ', with linked activities and milestones' : ', with source evidence'}.`;
    sceneFind('[data-update-pmp]').disabled = false;
    playButton.textContent = state.running ? 'Pause scene' : motion.matches ? 'Show result' : 'Replay scene';
  }
  function buildSteps() {
    const words = request.split(/\s+/), scanStart = words.length * 105 + 2400;
    const scanOrder = [...scene.sources];
    for (let i = scanOrder.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [scanOrder[i], scanOrder[j]] = [scanOrder[j], scanOrder[i]];
    }
    const fillStart = scanStart + scanOrder.length * 550 + 200;
    const actions = [
      ...words.map((_, i) => ({ at: (i + 1) * 105, run: () => { prompt.textContent = words.slice(0, i + 1).join(' '); } })),
      ...scanOrder.map((source, i) => ({ at: scanStart + i * 550, run: () => {
        showPlan(); find('.sw-caret').hidden = true; highlight(source, true);
        setStage(`Reading ${output(source).querySelector('.sw-source').textContent.toLowerCase()}`);
      } })),
      ...sections.filter(section => !section.classList.contains('sw-rfp-section')).map((section, i) => ({ at: scanStart + i * 220, run: () => revealHeading(section) })),
      ...[...documentView.querySelectorAll('[data-column-heading]')].map((heading, i) => ({ at: scanStart + i * 120, run: () => revealHeading(heading) })),
    ];
    let finishedAt;
    if (scene.buildSteps) {
      finishedAt = scene.buildSteps({ at: fillStart, actions, reveal, revealHeading, revealRow, follow, highlight, setStage });
    } else if (sceneKey === 'pmp') {
      actions.push(...sections.map((section, i) => ({ at: fillStart + i * 300, run: () => { reveal(section); setStage('Project plan · populating'); } })));
      finishedAt = fillStart + (sections.length - 1) * 300 + 650;
    } else {
      let at = fillStart;
      for (const section of sections) {
        actions.push({ at, run: () => {
          reveal(section);
          const heading = section.querySelector('.sw-section-title');
          follow(heading || section.querySelector('.sw-stage-heading') || section);
          setStage(`${scene.label} · ${section.dataset.sectionTitle || heading.textContent}`);
        } });
        at += 180;
        for (const row of section.querySelectorAll('[data-build-row]')) {
          actions.push({ at, run: () => { revealRow(row); follow(row); } });
          const links = documentView.querySelectorAll(`[data-link-to="${row.dataset.buildRow}"]`);
          if (links.length) actions.push({ at: at + 550, run: () => links.forEach(link => link.classList.add('is-linked')) });
          at += sceneKey === 'cost' ? 280 : 300;
        }
        at += 700;
      }
      actions.push({ at, run: () => { const result = sceneFind('[data-final-reveal]'); result.removeAttribute('data-final-pending'); follow(result); } });
      finishedAt = at + 800;
    }
    actions.push({ at: finishedAt, run: complete });
    if (playAll) {
      actions.push({ at: finishedAt + 7000, run: () => root.setAttribute('data-scene-exit', '') });
      actions.push({ at: finishedAt + 7450, run: () => selectScene(repeatScene ? sceneKey : order[(order.indexOf(sceneKey) + 1) % order.length], true) });
    }
    return actions.sort((a, b) => a.at - b.at);
  }
  function pause() {
    if (state.running) {
      state.remaining = Math.max(0, state.due - win.performance.now());
      win.clearTimeout(state.timer); state.timer = null;
    }
    state.running = false;
    root.dataset.motionPaused = 'true';
    root.getAnimations?.({ subtree: true }).forEach(animation => { if (animation.id !== 'sw-headline' && !['sw-console-float', 'sw-hero-enter', 'sw-word-arrive', 'sw-firm-drift'].includes(animation.animationName) && animation.playState === 'running') animation.pause(); });
    if (!state.done || playAll) playButton.textContent = state.index ? 'Resume scene' : 'Play scene';
  }
  function schedule(delay) {
    state.due = win.performance.now() + delay;
    state.timer = win.setTimeout(() => {
      const runId = state.runId, step = steps[state.index++];
      step.run();
      if (runId === state.runId && state.running && state.index < steps.length) schedule(steps[state.index].at - step.at);
    }, delay);
  }
  function resume() {
    if (state.running || (state.done && !playAll) || motion.matches) return;
    root.removeAttribute('data-instant');
    state.running = true;
    root.dataset.motionPaused = 'false';
    root.getAnimations?.({ subtree: true }).forEach(animation => { if (animation.id !== 'sw-headline' && !['sw-console-float', 'sw-hero-enter', 'sw-word-arrive', 'sw-firm-drift'].includes(animation.animationName) && animation.playState === 'paused') animation.play(); });
    playButton.textContent = 'Pause scene';
    schedule(state.remaining);
  }
  function reset(action = 'create') {
    pause(); state.runId++;
    request = scene[action]; steps = buildSteps();
    state.index = 0; state.done = false; state.remaining = steps[0].at;
    root.setAttribute('data-instant', ''); root.removeAttribute('data-scene-exit'); root.setAttribute('data-prompt-typing', '');
    scene.content.setAttribute('inert', ''); scene.content.setAttribute('aria-hidden', 'true');
    sceneFind('[data-update-pmp]').disabled = true;
    sections.forEach(section => {
      section.classList.remove('is-filled'); section.setAttribute('data-heading-pending', ''); section.setAttribute('inert', ''); section.setAttribute('aria-hidden', 'true');
      const content = section.querySelector('.sw-section-reveal');
      content?.setAttribute('inert', ''); content?.setAttribute('aria-hidden', 'true');
    });
    documentView.querySelectorAll('[data-column-heading]').forEach(heading => heading.setAttribute('data-heading-pending', ''));
    documentView.querySelectorAll('[data-build-row]').forEach(row => { row.classList.remove('is-built'); row.setAttribute('inert', ''); row.setAttribute('aria-hidden', 'true'); });
    documentView.querySelectorAll('[data-link-to]').forEach(link => link.classList.remove('is-linked'));
    sceneFind('[data-final-reveal]')?.setAttribute('data-final-pending', '');
    state.autoScrollTarget = 0; documentView.scrollTop = 0; documentView.scrollLeft = 0; documentView.setAttribute('aria-busy', 'true');
    prompt.textContent = ''; find('.sw-caret').hidden = false;
    order.forEach(key => { output(key).hidden = order.indexOf(key) >= order.indexOf(sceneKey); });
    find('[data-scene-source="cost"]').hidden = sceneKey === 'pmp';
    find('.sw-source-excerpt').hidden = true; highlight(null);
    root.querySelectorAll('[data-procurement-file]').forEach(row => { row.hidden = true; });
    scene.reset?.();
    setStage(`${scene.label} · preparing`); find('[data-status]').textContent = ''; playButton.textContent = 'Play scene';
    documentView.getBoundingClientRect();
  }
  function selectScene(key, keepSequence = false) {
    if (!scenes[key]) return;
    pause();
    if (!keepSequence) playAll = false;
    updateMode(); sceneKey = key; scene = scenes[key];
    documentView = scene.content.querySelector('[data-document]');
    sections = [...documentView.querySelectorAll('.sw-pmp-section,.sw-control-section')];
    root.dataset.activeScene = key;
    find('[data-send]').setAttribute('aria-label', `Replay ${scene.title.toLowerCase()} prompt`);
    find('.sw-editor').setAttribute('aria-label', `${scene.title} demonstration`);
    for (const [id, entry] of Object.entries(scenes)) entry.content.hidden = id !== key;
    root.querySelectorAll('[data-scene]').forEach(button => {
      if (button.closest('.sw-nav')) {
        if (button.dataset.scene === key) button.setAttribute('aria-current', 'page');
        else button.removeAttribute('aria-current');
      } else button.setAttribute('aria-pressed', String(button.dataset.scene === key));
    });
    reset();
    if (motion.matches) showResult();
    else if (state.visible && !doc.hidden) resume();
    observer?.disconnect(); observer?.observe(documentView);
  }
  function showResult() {
    pause(); playAll = false; updateMode(); root.removeAttribute('data-scene-exit'); root.setAttribute('data-instant', ''); complete();
    state.autoScrollTarget = 0; documentView.scrollTop = 0; documentView.scrollLeft = 0;
  }
  async function onClick(event) {
    const button = event.target.closest('button');
    if (!button || button.disabled || !root.contains(button)) return;
    if (button.dataset.scene) { state.userPaused = false; selectScene(button.dataset.scene); }
    else if (button.hasAttribute('data-play-all')) {
      if (playAll) { pause(); playAll = false; updateMode(); if (state.done) playButton.textContent = 'Replay scene'; }
      else { playAll = true; state.userPaused = false; selectScene('pmp', true); }
    } else if (button === resultButton) showResult();
    else if (button.hasAttribute('data-send') || button.hasAttribute('data-create-pmp') || button.hasAttribute('data-update-pmp') || button === playButton) {
      if (motion.matches) { showResult(); return; }
      if (state.running && button === playButton) { state.userPaused = true; pause(); return; }
      state.userPaused = false;
      if ((state.done && !playAll) || button.hasAttribute('data-send') || button.hasAttribute('data-create-pmp') || button.hasAttribute('data-update-pmp')) reset(button.hasAttribute('data-update-pmp') ? 'update' : 'create');
      resume();
    } else if (button.dataset.openRfp && sceneKey === 'procurement') {
      state.userPaused = true; pause(); root.setAttribute('data-instant', '');
      scene.openRfp(button.dataset.openRfp);
      const article = sceneFind(`[data-rfp="${button.dataset.openRfp}"]`);
      article.querySelectorAll('.sw-rfp-section').forEach(reveal);
      article.querySelectorAll('.sw-rfp-block').forEach(block => block.classList.add('is-built'));
      state.autoScrollTarget = 0;
      sceneFind('[data-back-procurement]').focus({ preventScroll: true });
      highlight(button.dataset.openRfp === 'civil-stormwater' ? 'procurement' : `rfp-${button.dataset.openRfp}`);
    } else if (button.hasAttribute('data-back-procurement')) {
      state.userPaused = true; pause();
      sceneFind('[data-procurement-reader]').hidden = true;
      sceneFind('[data-procurement-register]').hidden = false;
      scene.content.removeAttribute('data-procurement-exit');
      sceneFind(`[data-open-rfp="${scene.content.dataset.openRfp}"]`).focus({ preventScroll: true });
      scene.content.querySelectorAll('.sw-document-actions button').forEach(action => { action.disabled = true; });
      state.autoScrollTarget = 0; documentView.scrollTop = 0;
    } else if (button.hasAttribute('data-rfp-cite')) {
      state.userPaused = true; pause();
      const key = scene.content.dataset.openRfp;
      const references = sceneFind(`[data-rfp="${key}"] [data-section-title="Citation key"]`);
      reveal(references); references.querySelectorAll('.sw-rfp-block').forEach(block => block.classList.add('is-built')); follow(references);
      references.setAttribute('tabindex', '-1'); references.focus({ preventScroll: true });
    } else if (button.hasAttribute('data-download-rfp')) {
      state.userPaused = true; pause();
      const link = doc.createElement('a');
      link.href = new URL(`./${scene.content.dataset.openRfp}-rfp.md`, import.meta.url).href;
      link.download = `Seven-Hills-${scene.content.dataset.openRfp}-RFP-v1.md`;
      link.click();
    } else if (button.hasAttribute('data-copy-rfp')) {
      state.userPaused = true; pause();
      try {
        const response = await win.fetch(new URL(`./${scene.content.dataset.openRfp}-rfp.md`, import.meta.url));
        if (!response.ok) throw new Error('Draft unavailable');
        await win.navigator.clipboard.writeText(await response.text());
        find('[data-status]').textContent = 'RFP copied.'; setStage('RFP copied');
      } catch {
        find('[data-status]').textContent = 'Could not copy the RFP. Use Download to save the draft.'; setStage('Copy unavailable · use Download');
      }
    } else if (button.dataset.mode) {
      root.querySelectorAll('[data-mode]').forEach(mode => mode.setAttribute('aria-pressed', String(mode === button)));
    } else if (button.dataset.scale || button.hasAttribute('data-fit-program')) {
      state.userPaused = true; pause(); setProgrammeScale(scene.content, button.dataset.scale || scene.content.dataset.scale);
      if (button.hasAttribute('data-fit-program')) documentView.scrollLeft = 0;
    } else {
      const source = button.dataset.cite || button.dataset.source || (button.hasAttribute('data-open-generated') ? 'pmp' : null);
      if (!sources[source]) return;
      state.userPaused = true; pause(); highlight(source);
      find('[data-excerpt-title]').textContent = sources[source][0]; find('[data-excerpt]').textContent = sources[source][1]; find('.sw-source-excerpt').hidden = false;
    }
  }
  function syncVisibility() {
    if (!state.visible || doc.hidden) pause();
    else if (!state.userPaused) resume();
  }
  function onMotionChange() { if (motion.matches) showResult(); }
  function onDocumentScroll(event) {
    if (event.target !== documentView) return;
    // Smooth scrolling and section expansion can emit trailing scroll events after reaching the target.
    if (win.performance.now() < state.autoScrollUntil) return;
    if (state.autoScrollTarget !== null) {
      if (Math.abs(documentView.scrollTop - state.autoScrollTarget) < 1) state.autoScrollTarget = null;
      return;
    }
    if (documentView.scrollTop > 0 && state.running) { state.userPaused = true; pause(); }
  }
  function onManualScroll(event) {
    if (!event.target.closest('[data-document]') || event.type === 'keydown' && !['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].includes(event.key)) return;
    state.autoScrollTarget = null; state.autoScrollUntil = 0; state.userPaused = true; pause();
  }
  const observer = win.IntersectionObserver ? new win.IntersectionObserver(([entry]) => { state.visible = Boolean(entry?.isIntersecting); syncVisibility(); }, { threshold: .25 }) : null;
  playButton.hidden = false; resultButton.hidden = false; find('[data-send]').disabled = false;
  updateMode(); root.dataset.activeScene = 'pmp';
  if (motion.matches) showResult(); else reset();
  root.addEventListener('click', onClick); root.addEventListener('scroll', onDocumentScroll, true);
  root.addEventListener('wheel', onManualScroll, { passive: true }); root.addEventListener('touchstart', onManualScroll, { passive: true }); root.addEventListener('keydown', onManualScroll);
  doc.addEventListener('visibilitychange', syncVisibility); motion.addEventListener('change', onMotionChange);
  if (observer) observer.observe(documentView); else { state.visible = true; syncVisibility(); }
  if (initialScene !== 'pmp') selectScene(initialScene, true);
  return () => {
    pause(); observer?.disconnect();
    root.removeEventListener('click', onClick); root.removeEventListener('scroll', onDocumentScroll, true);
    root.removeEventListener('wheel', onManualScroll); root.removeEventListener('touchstart', onManualScroll); root.removeEventListener('keydown', onManualScroll);
    doc.removeEventListener('visibilitychange', syncVisibility); motion.removeEventListener('change', onMotionChange);
  };
}

const root = document.getElementById('sitewise-landing');
if (root) mountLandingDemo(root, { playAll: true, initialScene: 'program', repeatScene: true });
