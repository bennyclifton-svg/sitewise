const SQRT3 = Math.sqrt(3);

export const CHIP = {
  side: 78,
  topWidth: 10,
  topLength: 8,
  bottomWidth: 36,
  bottomLength: 11,
  overlap: 0.85,
};

function lineX(from, to, y) {
  const t = (y - from.y) / (to.y - from.y);
  return from.x + (to.x - from.x) * t;
}

function point(x, y) {
  return { x, y };
}

export function chipGeometry({
  side = CHIP.side,
  topWidth = CHIP.topWidth,
  topLength = CHIP.topLength,
  bottomWidth = CHIP.bottomWidth,
  bottomLength = CHIP.bottomLength,
  overlap = CHIP.overlap,
} = {}) {
  const height = side * SQRT3 / 2;
  const cx = 50;
  const topPad = (100 - topLength - height - bottomLength) / 2;
  const apex = point(cx, topPad + topLength);
  const bl = point(cx - side / 2, apex.y + height);
  const br = point(cx + side / 2, apex.y + height);

  const top = {
    x0: cx - topWidth / 2,
    x1: cx + topWidth / 2,
    y0: apex.y - topLength,
    y1: apex.y + overlap,
  };
  const bottom = {
    x0: cx - bottomWidth / 2,
    x1: cx + bottomWidth / 2,
    y0: bl.y,
    y1: bl.y + bottomLength,
  };

  const outline = [
    [top.x0, top.y0],
    [top.x1, top.y0],
    [top.x1, top.y1],
    [lineX(apex, br, top.y1), top.y1],
    [br.x, br.y],
    [bottom.x1, bottom.y0],
    [bottom.x1, bottom.y1],
    [bottom.x0, bottom.y1],
    [bottom.x0, bottom.y0],
    [bl.x, bl.y],
    [lineX(apex, bl, top.y1), top.y1],
    [top.x0, top.y1],
  ];

  return {
    apex, bl, br, top, bottom, outline,
    side, height, topWidth, topLength, bottomWidth, bottomLength, overlap,
  };
}

function fmt(value) {
  return String(Math.round(value * 1000) / 1000);
}

export function chipClipPolygon(options) {
  const { outline } = chipGeometry(options);
  return `polygon(${outline.map(([x, y]) => `${fmt(x)}% ${fmt(y)}%`).join(', ')})`;
}

export function applyChipClip(host, options) {
  if (!host) return '';
  const clip = chipClipPolygon(options);
  host.style.clipPath = clip;
  return clip;
}
