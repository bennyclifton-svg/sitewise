import { afterEach, describe, expect, it, vi } from 'vitest';
import { createHeadlineHand, finishHeadlineHand, headlineHand, playHeadlineHand } from '../../public/landing-assets/landing-headline-hand.js';

afterEach(() => {
  document.body.innerHTML = '';
});

describe('headline handwritten closer', () => {
  it('writes a blue Allison comma and then in detail.', () => {
    expect(headlineHand.font).toBe('Allison');
    expect(headlineHand.color).toBe('#087ac9');
    expect(headlineHand.comma).toBe(',');
    expect(headlineHand.text).toBe('in detail.');
    expect(headlineHand.rotate).toBeLessThan(0);
    expect(headlineHand.commaMs).toBeGreaterThanOrEqual(120);
    expect(headlineHand.commaMs).toBeLessThanOrEqual(160);
    expect(headlineHand.writeMs).toBeGreaterThanOrEqual(280);
    expect(headlineHand.writeMs).toBeLessThanOrEqual(450);

    const hand = createHeadlineHand({ drawn: true });
    expect(hand.className).toBe('sw-headline-hand');
    expect(hand.querySelector('[data-hand=comma]').textContent).toBe(',');
    expect(hand.querySelector('[data-hand=words]').textContent).toBe(' in detail.');
  });

  it('reveals the comma first, then the words, with a writing clip', async () => {
    const slot = document.createElement('span');
    const calls = [];
    await playHeadlineHand(slot, {
      sleep: async () => {},
      animate(element, frames, options) {
        calls.push({ element, frames, options });
        return { finished: Promise.resolve(), cancel() {} };
      },
    });

    expect(slot.hidden).toBe(false);
    expect(calls).toHaveLength(2);
    expect(calls[0].element.getAttribute('data-hand')).toBe('comma');
    expect(calls[1].element.getAttribute('data-hand')).toBe('words');
    expect(calls.every(call => call.options.id === 'sw-headline')).toBe(true);
    expect(calls[0].options.duration).toBe(headlineHand.commaMs);
    expect(calls[1].options.duration).toBe(headlineHand.writeMs);
    expect(calls[0].frames[0].clipPath).toBe(headlineHand.hiddenClip);
    expect(calls[0].frames.at(-1).clipPath).toBe(headlineHand.openClip);
  });

  it('shows the finished ink when motion is reduced', async () => {
    const slot = document.createElement('span');
    const animate = vi.fn();
    await playHeadlineHand(slot, { reducedMotion: true, animate });
    expect(animate).not.toHaveBeenCalled();
    expect(slot.querySelector('[data-hand=comma]').textContent).toBe(',');
    expect(slot.querySelector('[data-hand=words]').textContent).toBe(' in detail.');
    expect(slot.querySelector('[data-hand=words]').style.clipPath).toBe('');
  });

  it('replaces a slot with finished ink', () => {
    const slot = document.createElement('span');
    slot.hidden = true;
    finishHeadlineHand(slot);
    expect(slot.hidden).toBe(false);
    expect(slot.querySelector('.sw-headline-hand')).not.toBeNull();
  });
});
