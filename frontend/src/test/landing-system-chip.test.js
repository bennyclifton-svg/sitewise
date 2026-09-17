import { afterEach, describe, expect, it } from 'vitest';
import {
  applyChipClip,
  CHIP,
  chipClipPolygon,
  chipGeometry,
} from '../../public/landing-assets/system-chip.js';

const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

afterEach(() => {
  document.body.innerHTML = '';
});

describe('system chip geometry', () => {
  it('builds a large equilateral triangle centred on the plan', () => {
    const chip = chipGeometry();
    expect(chip.apex.x).toBeCloseTo(50);
    expect(chip.side).toBeGreaterThan(74);
    expect(distance(chip.apex, chip.bl)).toBeCloseTo(CHIP.side);
    expect(distance(chip.apex, chip.br)).toBeCloseTo(CHIP.side);
    expect(distance(chip.bl, chip.br)).toBeCloseTo(CHIP.side);
  });

  it('pops a small top tab and a centred base tab, not mid-side boxes', () => {
    const chip = chipGeometry();
    expect(chip.top.x0 + chip.top.x1).toBeCloseTo(100);
    expect(chip.apex.y - chip.top.y0).toBeCloseTo(CHIP.topLength);
    expect(chip.top.x1 - chip.top.x0).toBeCloseTo(CHIP.topWidth);
    expect(chip.bottom.x0 + chip.bottom.x1).toBeCloseTo(100);
    expect((chip.bottom.x0 + chip.bottom.x1) / 2).toBeCloseTo(50);
    expect(chip.bottom.x1 - chip.bottom.x0).toBeCloseTo(CHIP.bottomWidth);
    expect(chip.bottom.x1 - chip.bottom.x0).toBeLessThan(chip.side);
    expect(chip.bottom.y1 - chip.bl.y).toBeCloseTo(CHIP.bottomLength);
    expect(chip.left).toBeUndefined();
    expect(chip.right).toBeUndefined();

    const midY = (chip.apex.y + chip.bl.y) / 2;
    const midSpan = chip.side * ((midY - chip.apex.y) / chip.height);
    const outside = chip.outline.filter(([x, y]) => (
      Math.abs(y - midY) < 6 && (x < 50 - midSpan / 2 - 1 || x > 50 + midSpan / 2 + 1)
    ));
    expect(outside).toEqual([]);
  });

  it('keeps left-right mirror symmetry', () => {
    const chip = chipGeometry();
    expect(chip.bl.x + chip.br.x).toBeCloseTo(100);
    for (const [x, y] of chip.outline) {
      const mirrored = chip.outline.some(([mx, my]) => (
        Math.abs(mx - (100 - x)) < 0.05 && Math.abs(my - y) < 0.05
      ));
      expect(mirrored, `${x},${y}`).toBe(true);
    }
  });

  it('writes a closed CSS clip polygon in plan percentages', () => {
    const clip = chipClipPolygon();
    expect(clip.startsWith('polygon(')).toBe(true);
    expect(clip).toContain('%');
    expect(clip).toBe(applyChipClip(document.createElement('div')));
  });
});
