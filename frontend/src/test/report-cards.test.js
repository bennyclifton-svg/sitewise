import { readFileSync } from 'node:fs';
import { beforeEach, expect, it, vi } from 'vitest';

beforeEach(async () => {
  vi.resetModules();
  document.body.innerHTML = readFileSync('public/report-cards.html', 'utf8');
  await import('../../public/landing-assets/report-cards.js');
});

it('lets a reader pin and release each report using its button', () => {
  const buttons = [...document.querySelectorAll('.report-select')];
  buttons[0].click();
  expect(buttons[0].getAttribute('aria-pressed')).toBe('true');
  buttons[2].click();
  expect(buttons[0].getAttribute('aria-pressed')).toBe('false');
  expect(buttons[2].getAttribute('aria-pressed')).toBe('true');
  buttons[2].click();
  expect(buttons.every(button => button.getAttribute('aria-pressed') === 'false')).toBe(true);
});

it('keeps the displayed total reconciled with the revised forecast', () => {
  document.querySelector('[data-update]').click();
  expect(document.querySelector('[data-cost]').textContent).toBe('886,000');
  expect(document.querySelector('[data-total]').textContent).toBe('2,056,000');
  expect([...document.querySelectorAll('[data-revision]')].map(node => node.textContent)).toEqual(['09', '13', '07', '05']);
  expect(document.querySelector('[data-procurement]').textContent).toBe('Scope review');
  document.querySelector('[data-update]').click();
  expect(document.querySelector('[data-total]').textContent).toBe('2,042,000');
  expect(document.querySelector('[data-revision]').textContent).toBe('10');
});

it('resets spacing and tilt to the open default', () => {
  const slider = document.querySelector('[name="separation"]');
  slider.value = '100';
  slider.dispatchEvent(new Event('input', { bubbles: true }));
  expect(document.querySelector('.report-deck').style.getPropertyValue('--separation')).toBe('100px');
  document.querySelector('[data-reset]').click();
  expect(document.querySelector('.report-deck').style.getPropertyValue('--separation')).toBe('78px');
});

it('slides only the cards in front of the selected report aside', () => {
  const cards = [...document.querySelectorAll('.report-card')];
  cards[1].querySelector('button').click();
  expect(cards.map(card => card.classList.contains('is-after'))).toEqual([false, false, true, true]);
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  expect(cards.some(card => card.classList.contains('is-after'))).toBe(false);
});
