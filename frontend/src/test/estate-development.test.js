import { readFileSync } from 'node:fs';
import { describe, expect, it, vi } from 'vitest';
import { estateStages, lotProgress, closedFrontage, tracePath, mountEstate } from '../../public/landing-assets/estate-development.js';

const data = JSON.parse(readFileSync('public/landing-assets/coordination/sitewise-cadastral-plan.json', 'utf8'));
describe('estate road loops', () => {
  it('uses exactly five complete blocks with road frontage for every released lot', () => {
    const stages = estateStages(data.parcels, data.boundaries);
    expect(stages).toHaveLength(5);
    const ids = stages.flatMap(stage => stage.lots.map(lot => lot.id));
    expect(new Set(ids).size).toBe(ids.length);
    for (const stage of stages) {
      expect(stage.roadPaths).toHaveLength(1);
      expect(stage.roadPaths.every(path => path.endsWith('Z'))).toBe(true);
      const sourcePoints = new Set(data.boundaries.flatMap(edge => edge.points.map(point => point.join(','))));
      expect(stage.ring.every(point => sourcePoints.has(point.join(',')))).toBe(true);
      const members = new Set(stage.lots.map(lot => lot.id));
      for (const lot of stage.lots) {
        expect(data.boundaries.some(b => b.parcels.length === 1 && b.parcels[0] === lot.id)).toBe(true);
      }
      // No shared rear/side boundary can be cut by a stage boundary.
      for (const edge of data.boundaries) if (edge.parcels.some(id => members.has(id))) {
        expect(edge.parcels.every(id => members.has(id))).toBe(true);
      }
    }
  });
  it('completes the outer ring before any internal tracing and finishes before the next stage', () => {
    expect(lotProgress(2, 6.5)).toEqual({ road: .5, interior: 0 });
    expect(lotProgress(2, 7.1)).toEqual({ road: 1, interior: 0 });
    expect(lotProgress(2, 8.8)).toEqual({ road: 1, interior: 1 });
    expect(lotProgress(3, 8.8)).toEqual({ road: 0, interior: 0 });
  });
  it('draws every source boundary exactly once, including the closing perimeter edge', () => {
    for (const stage of estateStages(data.parcels, data.boundaries)) {
      const segments = [...stage.perimeter.segments, ...stage.interior.segments];
      const key = ({ start, end }) => [start.join(','), end.join(',')].sort().join('|');
      expect(new Set(segments.map(key)).size).toBe(segments.length);
      const members = new Set(stage.lots.map(lot => lot.id));
      const expected = data.boundaries.filter(edge => edge.parcels.some(id => members.has(id)));
      expect(segments).toHaveLength(expected.length);
      const last = stage.perimeter.segments.at(-1);
      expect(last.end).toEqual(stage.ring[0]);
      expect(tracePath(stage.perimeter, 1)).toContain(`M${last.start}L${last.end}`);
      expect(tracePath(stage.interior, 0)).toBe('');
    }
  });
  it('rejects an open road perimeter', () => {
    expect(() => closedFrontage([{ points: [[0, 0], [20, 0]] }])).toThrow('closed road loop');
  });
});

it('continues with a perimeter highlight after assembly and cancels on pause', () => {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  let callback;
  const request = vi.spyOn(window, 'requestAnimationFrame').mockImplementation(fn => { callback = fn; return 1; });
  const cancel = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  const finished = vi.fn();
  const animation = mountEstate(svg, data.parcels, data.boundaries, finished);
  animation.sync(false, false);
  for (let time = 0; time <= 17000; time += 100) callback(time);
  expect(finished).toHaveBeenCalledOnce();
  expect(svg.querySelector('.sw-estate-highlight').getAttribute('d')).not.toBe('');
  animation.sync(true, false);
  expect(cancel).toHaveBeenCalled();
  animation.sync(true, true);
  expect(svg.querySelector('.sw-estate-highlight').getAttribute('d')).toBe('');
  animation.dispose(); request.mockRestore(); cancel.mockRestore();
});
