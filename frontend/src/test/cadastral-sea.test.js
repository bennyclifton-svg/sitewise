import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  extractSegments,
  fitGroundFrame,
  GROUND_TILT,
  GROUND_ZOOM,
  LINE_ALPHA,
  FIELD_SHIFT_X,
  FIELD_SHIFT_Y,
  FIELD_YAW,
  HORIZON_CLIP,
  turnFittedPoint,
  WAVE_FREQ,
  EDGE_BAND,
  BLUR_SPREAD,
  BLUR_MIX,
  VIEW_BOUNDS,
  crestWeight,
  mountCadastralSea,
  projectIsometric,
  rotateGround,
  subdivideSegment,
  waveHeight,
} from '../../public/landing-assets/cadastral-sea.js';

const COS30 = Math.sqrt(3) / 2;

describe('cadastral sea geometry', () => {
  it('keeps in-view boundaries and splits long edges so waves can bend them', () => {
    const segments = extractSegments({
      boundaries: [
        { points: [[0, 0], [24, 0]] },
        { points: [[800, 800], [820, 800]] },
      ],
    }, VIEW_BOUNDS, 8, 0);
    expect(segments).toHaveLength(3);
    expect(segments[0]).toEqual([0, 0, 8, 0]);
    expect(segments[1]).toEqual([8, 0, 16, 0]);
    expect(segments[2]).toEqual([16, 0, 24, 0]);
    expect(segments.every(([, , x2, y2]) => x2 <= 330 && y2 <= 440)).toBe(true);
  });

  it('subdivides a diagonal without dropping the original endpoints', () => {
    expect(subdivideSegment([0, 0], [0, 20], 8)).toEqual([
      [0, 0],
      [0, 8],
      [0, 16],
      [0, 20],
    ]);
  });

  it('tightens travelling waves to half their previous ground length', () => {
    expect(WAVE_FREQ).toBe(2);
    expect(waveHeight(12, -8, 0.4, 2)).not.toBeCloseTo(waveHeight(12, -8, 0.4, 1), 5);
  });

  it('softens only the outer few percent of the frame so the middle stays sharp', () => {
    expect(EDGE_BAND).toBeCloseTo(0.025);
  });

  it('stacks several travelling waves so a still field is choppy, not a single swell', () => {
    const here = waveHeight(12, -8, 0.4);
    const there = waveHeight(40, 18, 0.4);
    const later = waveHeight(12, -8, 1.1);
    expect(here).not.toBeCloseTo(there, 5);
    expect(here).not.toBeCloseTo(later, 5);
    expect(Math.abs(here)).toBeGreaterThan(0);
  });

  it('projects from a lower camera and lifts points by wave height', () => {
    const near = projectIsometric(10, VIEW_BOUNDS.maxY, 0);
    const far = projectIsometric(10, VIEW_BOUNDS.minY, 0);
    expect(near.y).toBeCloseTo((10 + VIEW_BOUNDS.maxY) * GROUND_TILT);
    expect(Math.abs(far.x)).toBeLessThan(Math.abs((10 - VIEW_BOUNDS.minY) * COS30));
    expect(projectIsometric(10, VIEW_BOUNDS.maxY, 6).y).toBeCloseTo(near.y - 6);
  });

  it('fits the field into the lower two thirds so the top third stays sky', () => {
    const fit = fitGroundFrame({ minX: -30, maxX: 30, minY: -4, maxY: 4 }, 1);
    const clipY = isoY => isoY * fit[1] + fit[3];
    expect(clipY(4)).toBeCloseTo(-1, 5);
    expect(clipY(-4)).toBeCloseTo(HORIZON_CLIP, 5);
  });

  it('keeps that horizon when the field is wide enough to overflow the sides', () => {
    const fit = fitGroundFrame({ minX: -80, maxX: 80, minY: -4, maxY: 4 }, 1.8);
    expect(4 * fit[1] + fit[3]).toBeCloseTo(-1, 5);
    expect(-4 * fit[1] + fit[3]).toBeCloseTo(HORIZON_CLIP, 5);
  });

  it('zooms the live field a little further and parks the horizon two thirds up the page', () => {
    expect(GROUND_ZOOM).toBeCloseTo(1.7);
    expect(LINE_ALPHA).toBeCloseTo(0.7);
    expect(FIELD_SHIFT_X).toBeCloseTo(0);
    const base = fitGroundFrame({ minX: -30, maxX: 30, minY: -4, maxY: 4 }, 1);
    const live = fitGroundFrame({ minX: -30, maxX: 30, minY: -4, maxY: 4 }, 1, GROUND_ZOOM, FIELD_SHIFT_X, FIELD_SHIFT_Y);
    expect(live[0]).toBeCloseTo(base[0] * 1.7);
    expect(4 * live[1] + live[3]).toBeLessThan(-1);
    expect(-4 * live[1] + live[3]).toBeCloseTo(HORIZON_CLIP, 5);
  });

  it('turns the ground map a quarter turn so finer lots run across the window', () => {
    expect(FIELD_YAW).toBeCloseTo(Math.PI / 2);
    const [x, y] = rotateGround(24, 0);
    expect(x).toBeCloseTo(0);
    expect(y).toBeCloseTo(24);
    const turned = extractSegments({
      boundaries: [{ points: [[0, 0], [24, 0]] }],
    });
    expect(turned[0][0]).toBeCloseTo(0);
    expect(turned[0][1]).toBeCloseTo(0);
    expect(turned[0][2]).toBeCloseTo(0);
    expect(turned[0][3]).toBeCloseTo(8);
  });

  it('keeps only the upper part of a wave as a sharp crest', () => {
    expect(crestWeight(-8)).toBe(0);
    expect(crestWeight(12)).toBe(1);
    expect(crestWeight(0)).toBeGreaterThan(0);
    expect(crestWeight(0)).toBeLessThan(1);
  });

  it('keeps trough lines mostly in focus so the blur stays a light veil', () => {
    expect(BLUR_SPREAD).toBeCloseTo(1.25);
    expect(BLUR_MIX).toBeCloseTo(0.3);
  });

  it('turns a fitted point around the bottom so the near-left corner drops into the frame', () => {
    const turned = turnFittedPoint(-0.6, -0.3);
    expect(turned.x).toBeLessThan(-0.6);
    expect(turned.y).toBeLessThan(-0.3);
  });

  it('lets a passing wave move the projected cadastral point without changing its ground coordinates', () => {
    const rest = projectIsometric(20, 12, waveHeight(20, 12, 0));
    const swell = projectIsometric(20, 12, waveHeight(20, 12, 0.9));
    expect(rest.x).toBeCloseTo(swell.x);
    expect(rest.y).not.toBeCloseTo(swell.y);
  });
});

describe('cadastral sea mount', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('draws into a canvas over the plan and pauses the renderer when asked', () => {
    const plan = document.createElement('figure');
    plan.className = 'sw-coordination-plan';
    document.body.append(plan);
    const renderer = { resize: vi.fn(), render: vi.fn(), dispose: vi.fn() };
    const sea = mountCadastralSea(plan, { boundaries: [{ points: [[0, 0], [8, 0]] }] }, () => renderer);
    expect(plan.querySelector('canvas.sw-cadastral-sea')).not.toBeNull();
    expect(plan.classList.contains('has-sea')).toBe(true);
    expect(renderer.resize).toHaveBeenCalledOnce();
    expect(renderer.render).toHaveBeenCalledWith(0);
    sea.sync(true, false);
    expect(renderer.render).toHaveBeenCalledTimes(1);
    sea.dispose();
    expect(renderer.dispose).toHaveBeenCalledOnce();
    expect(plan.querySelector('canvas')).toBeNull();
  });

  it('leaves the flat plan in place when the sea renderer cannot start', () => {
    const plan = document.createElement('figure');
    document.body.append(plan);
    const sea = mountCadastralSea(plan, { boundaries: [] }, () => {
      throw new Error('WebGL is unavailable.');
    });
    expect(sea).toBeNull();
    expect(plan.querySelector('canvas')).toBeNull();
    expect(plan.classList.contains('has-sea')).toBe(false);
  });
});
