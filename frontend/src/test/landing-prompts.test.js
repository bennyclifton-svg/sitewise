import { readFileSync } from 'node:fs';
import { afterEach, expect, it, vi } from 'vitest';
import { mountPromptExplorer } from '../../public/landing-assets/landing-prompts.js';

afterEach(() => { document.body.innerHTML = ''; vi.unstubAllGlobals(); });

it('offers ten full composer prompts, defaults to change and switches reasoning modes', () => {
  document.body.innerHTML = readFileSync('public/landing.html', 'utf8');
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
  vi.stubGlobal('matchMedia', () => ({ matches: true }));
  const root = document.querySelector('.sw-prompt-explorer');
  const cleanup = mountPromptExplorer(root);
  const choices = [...root.querySelectorAll('.sw-prompt-choice')];
  expect(choices).toHaveLength(10);
  expect(choices.filter(choice => choice.open)).toEqual([choices[9]]);
  expect(root.querySelectorAll('.sw-example-field')).toHaveLength(10);
  expect(root.querySelector('.sw-prompt-full')).toBeNull();
  expect(choices[9].textContent).toContain('preserving the approved baseline');
  choices[4].open = true;
  choices[4].dispatchEvent(new Event('toggle'));
  expect(choices[9].open).toBe(false);
  const fast = choices[4].querySelector('[data-example-mode="fast"]');
  fast.click();
  expect(fast.getAttribute('aria-pressed')).toBe('true');
  expect(choices[4].querySelector('[data-example-mode="thorough"]').getAttribute('aria-pressed')).toBe('false');
  expect(choices[4].open).toBe(true);
  expect(choices[4].querySelector('.sw-example-field').textContent).toContain('signed letter');
  expect(choices[4].querySelector('.sw-example-send').disabled).toBe(true);
  cleanup();
});
