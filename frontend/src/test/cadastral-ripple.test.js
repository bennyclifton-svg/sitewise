import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  applyRipple,
  centroid,
  DELAY_PER_CELL,
  DURATION_BASE,
  DURATION_PER_CELL,
  fullViewBox,
  mountCadastralRipple,
  nearestNeighborScale,
  parcelInView,
  rippleTiming,
  ringPath,
} from '../../public/landing-assets/cadastral-ripple.js';

const square = (x, y, size = 10) => [[
  [x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y],
]];

const fixtureData = {
  viewBox: [-20, -20, 140, 140],
  parcels: [
    { id: 'origin', area_m2: 100, rings: square(0, 0) },
    { id: 'near', area_m2: 100, rings: square(20, 0) },
    { id: 'far', area_m2: 100, rings: square(80, 80) },
    { id: 'offscreen', area_m2: 100, rings: square(400, 400) },
  ],
};

afterEach(() => {
  document.body.innerHTML = '';
  vi.unstubAllGlobals();
});

describe('cadastral ripple timing', () => {
  it('uses vertex averages and ignores a closing duplicate', () => {
    expect(centroid(square(0, 0))).toEqual([5, 5]);
  });

  it('keeps Aceternity delay and duration for one cell of distance', () => {
    expect(rippleTiming([0, 0], [0, 0], 20)).toEqual({
      delay: 0,
      duration: DURATION_BASE,
    });
    expect(rippleTiming([0, 0], [20, 0], 20)).toEqual({
      delay: DELAY_PER_CELL,
      duration: DURATION_BASE + DURATION_PER_CELL,
    });
    expect(rippleTiming([0, 0], [40, 0], 20).delay).toBe(DELAY_PER_CELL * 2);
  });

  it('scales map metres so a typical neighbour equals one cell', () => {
    const parcels = fixtureData.parcels.slice(0, 3);
    expect(nearestNeighborScale(parcels.map(parcel => ({
      centroid: centroid(parcel.rings),
    })))).toBeCloseTo(20, 5);
  });

  it('clips lots to the plan viewBox', () => {
    expect(parcelInView(fixtureData.parcels[0], fixtureData.viewBox)).toBe(true);
    expect(parcelInView(fixtureData.parcels[3], fixtureData.viewBox)).toBe(false);
  });

  it('fits every parcel into one north-up frame', () => {
    expect(fullViewBox(fixtureData.parcels, 0)).toEqual([0, 0, 410, 410]);
  });

  it('writes a closed SVG path', () => {
    expect(ringPath(square(0, 0))).toBe('M0,0 L10,0 L10,10 L0,10 L0,0Z');
  });
});

describe('cadastral ripple mount', () => {
  it('draws visible lots and ripples farther lots later', async () => {
    document.body.innerHTML = '<figure data-lot-ripple><p data-ripple-status></p></figure>';
    const host = document.querySelector('[data-lot-ripple]');
    const session = await mountCadastralRipple(host, { data: fixtureData });
    const lots = [...host.querySelectorAll('.sw-lot')];
    expect(lots).toHaveLength(4);
    expect(host.querySelector('[data-lot="offscreen"]')).not.toBeNull();
    expect(host.style.getPropertyValue('--sw-map-ratio')).toBe('458 / 458');

    lots[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
    const origin = host.querySelector('[data-lot="origin"]');
    const near = host.querySelector('[data-lot="near"]');
    const far = host.querySelector('[data-lot="far"]');
    expect(origin.classList.contains('is-origin')).toBe(true);
    expect(origin.classList.contains('is-rippling')).toBe(true);
    expect(origin.style.getPropertyValue('--delay')).toBe('0ms');
    expect(Number.parseFloat(near.style.getPropertyValue('--delay')))
      .toBeLessThan(Number.parseFloat(far.style.getPropertyValue('--delay')));
    session.dispose();
  });

  it('clips the plan into the system chip and covers the silhouette', async () => {
    document.body.innerHTML = '<figure data-lot-ripple data-system-chip></figure>';
    const host = document.querySelector('[data-lot-ripple]');
    const session = await mountCadastralRipple(host, { data: fixtureData });
    const svg = host.querySelector('.sw-lot-ripple-map');
    expect(host.style.clipPath.startsWith('polygon(')).toBe(true);
    expect(host.style.getPropertyValue('--sw-map-ratio')).toBe('');
    expect(svg.getAttribute('preserveAspectRatio')).toBe('xMidYMid slice');
    host.querySelector('[data-lot="origin"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(host.querySelector('.is-rippling')).not.toBeNull();
    session.dispose();
  });

  it('skips the flash when motion is reduced', async () => {
    document.body.innerHTML = '<figure data-lot-ripple></figure>';
    const host = document.querySelector('[data-lot-ripple]');
    const session = await mountCadastralRipple(host, {
      data: fixtureData,
      reducedMotion: true,
    });
    host.querySelector('[data-lot="origin"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(host.querySelector('.is-origin')).not.toBeNull();
    expect(host.querySelector('.is-rippling')).toBeNull();
    session.dispose();
  });

  it('restarts the same-origin wave by clearing and reapplying the class', () => {
    document.body.innerHTML = '<svg></svg>';
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    document.querySelector('svg').append(path);
    const node = { path, centroid: [0, 0] };
    applyRipple([node], node, 20, false);
    expect(path.classList.contains('is-rippling')).toBe(true);
    applyRipple([node], node, 20, false);
    expect(path.classList.contains('is-rippling')).toBe(true);
    expect(path.style.getPropertyValue('--delay')).toBe('0ms');
  });
});
