import { readFileSync } from 'node:fs';
import { afterEach, expect, it, vi } from 'vitest';
import { mountPromptExplorer, promptMotion, promptWordDelay, splitPromptWords } from '../../public/landing-assets/landing-prompts.js';

afterEach(() => { document.body.innerHTML = ''; vi.unstubAllGlobals(); });

function loadExplorer(matchMedia = () => ({ matches: true })) {
  document.body.innerHTML = readFileSync('public/landing.html', 'utf8');
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
  vi.stubGlobal('matchMedia', matchMedia);
  return document.querySelector('.sw-prompt-explorer');
}

async function flush(times = 40) {
  for (let i = 0; i < times; i += 1) await Promise.resolve();
}

it('switches four categories and their prompt buttons without leftover explorer chrome', () => {
  const root = loadExplorer();
  const cleanup = mountPromptExplorer(root);
  const categories = [...root.querySelectorAll('.sw-prompt-nav [data-sw-category]')];
  expect(categories.map(button => button.textContent)).toEqual(['Plan', 'Appoint', 'Deliver', 'Manage']);
  expect(root.querySelectorAll('.sw-example-field')).toHaveLength(10);
  expect(root.querySelector('.sw-prompt-choice')).toBeNull();
  expect(root.querySelector('h4, h5')).toBeNull();
  expect(root.querySelector('.sw-prompt-records')).toBeNull();
  expect(root.querySelector('.sw-prompt-note')).toBeNull();
  expect(root.textContent).not.toContain('Connected change');
  expect(root.textContent).not.toContain('Connected project records');
  expect(root.textContent).not.toContain('Illustrative. Drafts and open decisions stay visible.');
  expect(categories[0].getAttribute('aria-pressed')).toBe('true');
  const visible = () => root.querySelector('.sw-prompt-panel:not([hidden])');
  expect(visible().dataset.swPanel).toBe('plan-plan');
  expect(visible().textContent).toContain('coordinated project plan');
  root.querySelector('[data-sw-prompt="plan-cost"]').click();
  expect(visible().textContent).toContain('closing any shortfall');
  categories[1].click();
  expect(categories[1].getAttribute('aria-pressed')).toBe('true');
  expect(visible().textContent).toContain('coordinated RFPs');
  root.querySelector('[data-sw-prompt="appoint-appointment"]').click();
  expect(visible().textContent).toContain('signed letter');
  const fast = visible().querySelector('[data-example-mode="fast"]');
  fast.click();
  expect(fast.getAttribute('aria-pressed')).toBe('true');
  expect(visible().querySelector('[data-example-mode="thorough"]').getAttribute('aria-pressed')).toBe('false');
  expect(visible().querySelector('.sw-example-send').disabled).toBe(true);
  categories[2].click();
  expect(visible().textContent).toContain('like-for-like');
  root.querySelector('[data-sw-prompt="deliver-invoices"]').click();
  expect(visible().textContent).toContain('claimed-to-date');
  categories[3].click();
  expect(root.querySelectorAll('.sw-prompt-switch[data-sw-category="manage"] [data-sw-prompt]')).toHaveLength(1);
  expect(visible().textContent).toContain('keep the approved baseline');
  cleanup();
});

it('pauses longer after sentences than commas, with no metronomic default', () => {
  const steady = () => 0.5;
  expect(splitPromptWords('Save the plan. Flag it.')).toEqual(['Save ', 'the ', 'plan. ', 'Flag ', 'it.']);
  expect(promptWordDelay('plan.', { random: steady })).toBe(Math.round(promptMotion.wordMs * promptMotion.sentencePause));
  expect(promptWordDelay('scope,', { random: steady })).toBe(Math.round(promptMotion.wordMs * promptMotion.commaPause));
  expect(promptWordDelay('plan.', { random: steady })).toBeGreaterThan(promptWordDelay('scope,', { random: steady }) * 1.5);
  expect(promptWordDelay('the', { random: () => 1 })).not.toBe(promptWordDelay('the', { random: () => 0 }));
});

it('types the composer word by word and retracts with ease-in on switch', async () => {
  const root = loadExplorer(query => ({ matches: String(query).includes('min-width') }));
  const calls = [];
  const cleanup = mountPromptExplorer(root, {
    reducedMotion: false,
    random: () => 0.5,
    sleep: async () => {},
    animate(element, frames, options) {
      calls.push({ element, frames, options });
      return { finished: Promise.resolve(), cancel() {} };
    },
  });
  await flush(80);
  expect(root.querySelectorAll('.sw-prompt-word').length).toBeGreaterThan(20);
  const entering = calls.filter(call => call.frames[0].opacity === 0);
  expect(entering.length).toBeGreaterThan(10);
  expect(entering[0].options.easing).toBe(promptMotion.appearEase);
  expect(entering[0].frames[0].transform).toMatch(/translateY/);
  expect(entering[0].frames.at(-1).transform).toMatch(/translateY\(0/);

  calls.length = 0;
  root.querySelector('[data-sw-prompt="plan-cost"]').click();
  await flush(120);
  const visible = root.querySelector('.sw-prompt-panel:not([hidden])');
  expect(visible.dataset.swPanel).toBe('plan-cost');
  expect(visible.textContent).toContain('closing any shortfall');
  const leaving = calls.filter(call => call.frames[0].opacity === 1);
  const arriving = calls.filter(call => call.frames[0].opacity === 0);
  expect(leaving.length).toBeGreaterThan(5);
  expect(arriving.length).toBeGreaterThan(5);
  expect(leaving[0].options.easing).toBe(promptMotion.retractEase);
  expect(leaving[0].options.easing).not.toBe(promptMotion.appearEase);
  expect(leaving[0].options.duration).toBe(promptMotion.retractMs);
  cleanup();
});

it('cancels an in-flight prompt instead of stacking timers', async () => {
  const root = loadExplorer(query => ({ matches: String(query).includes('min-width') }));
  let active = 0;
  let peak = 0;
  const cleanup = mountPromptExplorer(root, {
    reducedMotion: false,
    random: () => 0.5,
    sleep: async () => {
      active += 1;
      peak = Math.max(peak, active);
      active -= 1;
    },
    animate() {
      return { finished: Promise.resolve(), cancel() {} };
    },
  });
  root.querySelector('[data-sw-prompt="plan-cost"]').click();
  root.querySelector('[data-sw-prompt="plan-programme"]').click();
  await flush(120);
  expect(root.querySelector('.sw-prompt-panel:not([hidden])').dataset.swPanel).toBe('plan-programme');
  expect(root.querySelector('.sw-prompt-panel:not([hidden])').textContent).toContain('critical path');
  expect(peak).toBeLessThanOrEqual(1);
  cleanup();
});
