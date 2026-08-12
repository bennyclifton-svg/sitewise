/* The SiteWise composer, drawn to canvas — the same window as the product's
   chat composer (Composer 2a): depth rail in the open, the mark itself as the
   submit target. Proportioned for film: type is larger relative to the frame
   than in the app, everything else holds its ratios.

   Design units: 1120 x 268. Callers give a width; everything scales from it. */

const SANS = "'Hanken Grotesk', Helvetica, sans-serif";
const W0 = 1120, H0 = 268;
const COL = 160;                 // the mark's column, right-hand side
const PADL = 56;

export const THEMES = {
  // on the product's dark chrome
  dark: {
    bg: 'rgba(11,12,15,0.55)', border: 'rgba(255,255,255,0.11)', top: 'rgba(255,255,255,0.18)',
    ink: '#E8E8E4', dim: '#6F747C', ph: '#5C616A', rail: 'rgba(255,255,255,0.12)',
    activeBg: 'rgba(47,114,196,0.16)', activeLine: '#2F72C4', activeInk: '#E8E8E4',
    caret: '#7FB0E4', hot: 'rgba(47,114,196,0.14)',
    mark: ['#2C3037', '#D6D6D0', '#123564', '#2F72C4'],
    edge: ['rgba(169,198,232,0.32)', 'rgba(140,149,162,0.26)']
  },
  // straight onto the blue glazing: white on transparent
  glass: {
    bg: null, border: 'rgba(255,255,255,0.34)', top: 'rgba(255,255,255,0.52)',
    ink: '#FFFFFF', dim: 'rgba(255,255,255,0.62)', ph: 'rgba(255,255,255,0.52)',
    rail: 'rgba(255,255,255,0.32)',
    activeBg: 'rgba(255,255,255,0.18)', activeLine: '#FFFFFF', activeInk: '#FFFFFF',
    caret: '#FFFFFF', hot: 'rgba(255,255,255,0.14)',
    mark: ['rgba(255,255,255,0.22)', '#FFFFFF', 'rgba(255,255,255,0.34)', 'rgba(255,255,255,0.72)'],
    edge: ['rgba(255,255,255,0.5)', 'rgba(255,255,255,0.3)']
  }
};

const DEPTHS = ['Fast', 'Balanced', 'Complex'];

function poly(x, pts, fill) {
  x.beginPath();
  x.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) x.lineTo(pts[i][0], pts[i][1]);
  x.closePath(); x.fillStyle = fill; x.fill();
}

/* the mark, from the 44-unit artwork, centred on its own middle vertex */
export function drawMark(x, cx, cy, size, th) {
  const s = size / 44;
  const A = [22, 5.5], B = [37, 14.1], C = [22, 22.7], D = [7, 14.1];
  const E = [7, 31.3], F = [22, 39.9], G = [37, 31.3];
  x.save();
  x.translate(cx, cy); x.scale(s, s); x.translate(-22, -22.7);
  poly(x, [A, B, C, D], th.mark[0]);
  poly(x, [C, E, F], th.mark[1]);
  poly(x, [C, B, G], th.mark[2]);
  poly(x, [C, G, F], th.mark[3]);
  x.lineWidth = 1 / s * (size / 44);
  x.strokeStyle = th.edge[0];
  x.beginPath(); x.moveTo(C[0], C[1]); x.lineTo(B[0], B[1]); x.stroke();
  x.strokeStyle = th.edge[1];
  x.beginPath(); x.moveTo(C[0], C[1]); x.lineTo(D[0], D[1]); x.stroke();
  x.restore();
}

/* one, two or three planes — the depth glyphs */
function planes(x, cx, cy, n, on, th) {
  const w = 13, h = 7.4, gap = 9.6;
  const y0 = cy - ((n - 1) * gap) / 2;
  for (let i = 0; i < n; i++) {
    const y = y0 + i * gap;
    x.beginPath();
    x.moveTo(cx, y - h / 2); x.lineTo(cx + w, y); x.lineTo(cx, y + h / 2); x.lineTo(cx - w, y);
    x.closePath();
    x.fillStyle = on ? (i === 0 ? '#7FB0E4' : th.activeLine) : th.dim;
    x.globalAlpha = on ? 1 : 0.9 - i * 0.22;
    x.fill(); x.globalAlpha = 1;
  }
}

function wrapText(x, s, maxw) {
  const lines = []; let cur = '';
  for (const w of s.split(' ')) {
    const test = cur ? cur + ' ' + w : w;
    if (x.measureText(test).width > maxw && cur) { lines.push(cur); cur = w; }
    else cur = test;
  }
  lines.push(cur);
  return lines;
}

/* opts: { x0, y0, w, theme, text, placeholder, caret, depth, hot, alpha } */
export function drawComposer(x, o) {
  const th = typeof o.theme === 'string' ? THEMES[o.theme] : (o.theme || THEMES.dark);
  const s = o.w / W0;
  x.save();
  x.translate(o.x0, o.y0); x.scale(s, s);
  if (o.alpha != null) x.globalAlpha = o.alpha;
  x.textBaseline = 'alphabetic'; x.textAlign = 'left';

  if (th.bg) { x.fillStyle = th.bg; x.fillRect(0, 0, W0, H0); }
  if (o.hot) { x.fillStyle = th.hot; x.fillRect(W0 - COL, 0, COL, H0); }

  // frame, with the top edge broken for the collapse handle
  const gap = 128, gx = W0 / 2 - gap / 2;
  x.lineWidth = 1.6; x.strokeStyle = th.border;
  x.beginPath();
  x.moveTo(0, 0); x.lineTo(0, H0); x.lineTo(W0, H0); x.lineTo(W0, 0);
  x.stroke();
  x.strokeStyle = th.top;
  x.beginPath();
  x.moveTo(0, 0.8); x.lineTo(gx, 0.8);
  x.moveTo(gx + gap, 0.8); x.lineTo(W0, 0.8);
  x.stroke();

  // collapse handle sitting on the edge
  x.strokeStyle = th.border; x.lineWidth = 1.6;
  x.beginPath();
  x.moveTo(gx + 10, 0.8); x.lineTo(gx + 38, 0.8);
  x.moveTo(gx + gap - 38, 0.8); x.lineTo(gx + gap - 10, 0.8);
  x.stroke();
  x.strokeStyle = th.dim; x.lineWidth = 2.4;
  x.beginPath();
  x.moveTo(W0 / 2 - 11, -4); x.lineTo(W0 / 2, 7); x.lineTo(W0 / 2 + 11, -4);
  x.stroke();

  // the field
  const maxw = W0 - COL - PADL - 40;
  const typed = o.text || '';
  let size = 38, lines = [];
  // scroll: hold the type at full size and let earlier lines run up out of the
  // field, rather than shrinking a long instruction past legibility
  if (o.scroll) {
    x.font = `300 ${size}px ${SANS}`;
    lines = typed ? wrapText(x, typed, maxw) : [];
    if (lines.length > 2) lines = lines.slice(-2);
  } else {
    for (const s2 of [38, 32, 27, 23]) {
      size = s2; x.font = `300 ${s2}px ${SANS}`;
      lines = typed ? wrapText(x, typed, maxw) : [];
      if (lines.length <= (s2 <= 27 ? 3 : 2)) break;
    }
  }
  const lh = size * 1.28;
  const y1 = lines.length > 2 ? 74 : lines.length > 1 ? 88 : 104;
  if (!typed && o.placeholder) {
    x.fillStyle = th.ph; x.font = `300 38px ${SANS}`;
    x.fillText(o.placeholder, PADL, 104);
  }
  x.fillStyle = th.ink;
  lines.forEach((ln, i) => x.fillText(ln, PADL, y1 + i * lh));
  if (o.caret) {
    const last = typed ? lines[lines.length - 1] : (o.placeholder || '');
    const cw = x.measureText(last).width;
    x.fillStyle = th.caret;
    x.fillRect(PADL + cw + 5, (typed ? y1 + (lines.length - 1) * lh : 104) - size * 0.84,
      3, size * 1.12);
  }

  // depth rail
  const rY = 164, rH = 66;
  x.font = `400 27px ${SANS}`;
  const segW = DEPTHS.map((d) => x.measureText(d).width + 92);
  const railW = segW.reduce((a, b) => a + b, 0) + 2;
  let cx0 = PADL;
  const active = o.depth == null ? 1 : o.depth;
  DEPTHS.forEach((d, i) => {
    const w = segW[i], on = i === active;
    if (on) { x.fillStyle = th.activeBg; x.fillRect(cx0, rY, w, rH); }
    planes(x, cx0 + 32, rY + rH / 2, i + 1, on, th);
    x.fillStyle = on ? th.activeInk : th.dim;
    x.font = `${on ? 500 : 400} 27px ${SANS}`;
    x.fillText(d, cx0 + 60, rY + rH / 2 + 10);
    if (on) { x.fillStyle = th.activeLine; x.fillRect(cx0, rY + rH - 3, w, 3); }
    if (i < 2) { x.fillStyle = th.rail; x.fillRect(cx0 + w, rY, 1, rH); }
    cx0 += w;
  });
  x.strokeStyle = th.rail; x.lineWidth = 1.4;
  x.strokeRect(PADL, rY, railW - 2, rH);

  // dictate
  const mx = W0 - COL - 62, my = rY + rH / 2;
  x.strokeStyle = o.dictating ? th.caret : th.dim; x.lineWidth = 2.4;
  x.beginPath();
  x.moveTo(mx - 6, my - 14); x.lineTo(mx - 6, my - 3);
  x.arc(mx, my - 3, 6, Math.PI, 0, true);
  x.lineTo(mx + 6, my - 14);
  x.arc(mx, my - 14, 6, 0, Math.PI, true);
  x.stroke();
  x.beginPath();
  x.arc(mx, my - 4, 12, 0.15 * Math.PI, 0.85 * Math.PI);
  x.moveTo(mx, my + 8); x.lineTo(mx, my + 16);
  x.stroke();

  // the mark's column
  x.fillStyle = th.border; x.fillRect(W0 - COL, 0, 1.4, H0);
  drawMark(x, W0 - COL / 2, H0 / 2, 104, th);

  x.restore();
}

export const COMPOSER_ASPECT = H0 / W0;
