/* Basement transmittal — two product screens drawn to canvas as pure functions
   of time, so a seeked frame is a deterministic frame. Same reduction rule as
   the invoice film: on a face seen at an angle the gesture has to read, not the
   data. Rows and copy follow the real screens. */
import { THREE } from './cube-geometry.js';
import { drawComposer } from './composer.js?v=5';

const C = {
  bg: '#0B0D10', panel: '#101319', line: '#1E232B', head: '#161A21',
  ink: '#D6D6D0', dim: '#8A8F98', blue: '#2F72C4', sky: '#7FB0E4',
  amber: '#E0A44A', green: '#57A87A', violet: '#B49BE0'
};
const SANS = "'Hanken Grotesk', Helvetica, sans-serif";
const MONO = "'IBM Plex Mono', monospace";

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const seg = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
const lerp = (a, b, t) => a + (b - a) * t;
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

const N = 1024;

function rr(x, a, b, w, h, r) {
  x.beginPath();
  x.moveTo(a + r, b); x.arcTo(a + w, b, a + w, b + h, r);
  x.arcTo(a + w, b + h, a, b + h, r); x.arcTo(a, b + h, a, b, r);
  x.arcTo(a, b, a + w, b, r); x.closePath();
}
function text(x, s, px, py, size, col, font, align) {
  x.fillStyle = col; x.font = `${size}px ${font || SANS}`;
  x.textAlign = align || 'left'; x.textBaseline = 'middle';
  x.fillText(s, px, py);
}
function wrap(x, s, size, maxw, font) {
  x.font = `${size}px ${font || SANS}`;
  const lines = []; let cur = '';
  for (const w of s.split(' ')) {
    const test = cur ? cur + ' ' + w : w;
    if (x.measureText(test).width > maxw && cur) { lines.push(cur); cur = w; }
    else cur = test;
  }
  if (cur) lines.push(cur);
  return lines;
}
function shell(x, title) {
  // transparent stage: no panel fill, just the structural line work and text
  x.fillStyle = C.line; x.fillRect(0, 74, N, 1.5);
  text(x, title, 34, 38, 21, C.sky, MONO);
  x.strokeStyle = C.line; x.lineWidth = 3; x.strokeRect(1.5, 1.5, N - 3, N - 3);
}
function cursor(x, px, py, a) {
  x.save(); x.globalAlpha = a; x.translate(px, py);
  x.beginPath(); x.moveTo(0, 0); x.lineTo(0, 30); x.lineTo(8, 23);
  x.lineTo(13, 34); x.lineTo(19, 31); x.lineTo(14, 21); x.lineTo(24, 20);
  x.closePath();
  x.fillStyle = '#F4F6F9'; x.fill();
  x.strokeStyle = '#0B0D10'; x.lineWidth = 2.5; x.stroke();
  x.restore();
}

/* ---- the assistant ------------------------------------------------------ */
const Q = 'select all basement drawings and create a transmittal';
const R1 = 'Selected all 19 basement drawings and queued an unissued transmittal draft.';
const R2 = ['Recipient: TBC', 'Purpose: Basement drawings transmittal'];
const R3 = 'The draft will appear when ready.';
const CHIPS = [['Project context', C.sky], ['1 tool used', C.blue], ['LLM reasoning', C.dim]];

/* The register runs for nineteen seconds, so the answer cannot arrive early —
   the chat holds on working while the front face does the searching. */
const SEND = 5.4, WORK = 6.2, ANS = 15.0, CARD = 16.6;
const OPEN_AT = 19.4;                      // the cursor click that opens the draft

function drawChat(x, t) {
  shell(x, 'SITEWISE \u00b7 ASSISTANT');

  const typed = seg(t, 0.2, 3.6);
  const sent = t >= SEND;
  const qLines = wrap(x, Q, 34, N - 200);

  /* the composer holds the frame alone until the cursor clicks the mark */
  if (!sent) {
    const shown = Math.floor(Q.length * typed);
    drawComposer(x, {
      x0: 34, y0: N - 258, w: N - 68, theme: 'dark',
      text: Q.slice(0, shown),
      placeholder: 'Ask about your project documents',
      caret: Math.floor(t * 2.2) % 2 === 0 || typed >= 1,
      depth: 1, hot: seg(t, SEND - 0.5, SEND)
    });
    const shown2 = seg(t, 3.9, 4.3);
    if (shown2 > 0) {
      const k = easeInOut(seg(t, 4.1, SEND - 0.05));
      const px = lerp(N - 130, 922, k), py = lerp(N - 56, 880, k);
      const ring = seg(t, SEND - 0.2, SEND);
      if (ring > 0) {
        x.beginPath(); x.arc(px + 2, py + 2, 10 + ring * 24, 0, 7);
        x.strokeStyle = 'rgba(127,176,228,' + (0.6 * (1 - ring)) + ')';
        x.lineWidth = 3; x.stroke();
      }
      cursor(x, px, py, shown2);
    }
    return;
  }

  /* The question rides up to mid-page: a bubble on the right, sized to its own
     text. Everything the assistant says sits left, off a blue gutter, so the
     two voices never read as one block. */
  const rise = easeOut(seg(t, SEND, SEND + 0.8));
  const qL = wrap(x, Q, 34, 520);
  x.font = `34px ${SANS}`;
  let qw = 0;
  qL.forEach((ln) => { qw = Math.max(qw, x.measureText(ln).width); });
  const bw = Math.min(N - 140, qw + 60), bh = 32 + qL.length * 46;
  const by = 432 + (1 - rise) * 160;
  x.globalAlpha = rise;
  rr(x, N - 34 - bw, by, bw, bh, 12);
  x.fillStyle = 'rgba(47,114,196,0.18)'; x.fill();
  x.strokeStyle = 'rgba(47,114,196,0.55)'; x.lineWidth = 2; x.stroke();
  qL.forEach((ln, i) => text(x, ln, N - 34 - bw + 30, by + 38 + i * 46, 34, C.ink, SANS, 'left'));
  x.globalAlpha = 1;

  const top = by + bh + 74;

  if (t < ANS) {
    text(x, 'Working', 68, top + 16, 27, C.dim, MONO);
    for (let i = 0; i < 3; i++) {
      const p = (Math.sin(t * 5 - i * 0.7) + 1) / 2;
      x.globalAlpha = 0.25 + p * 0.75;
      x.fillStyle = C.sky;
      x.beginPath(); x.arc(218 + i * 26, top + 16, 6, 0, 7); x.fill();
    }
    x.globalAlpha = 1;
    const scanning = seg(t, WORK + 0.6, WORK + 1.2) * (1 - seg(t, ANS - 0.6, ANS));
    x.globalAlpha = scanning;
    text(x, 'Searching the document register\u2026', 68, top + 78, 26, C.dim);
    x.globalAlpha = 1;
    return;
  }

  // one answer line, then the draft — one voice, held together
  let y = top;
  const a1 = seg(t, ANS, ANS + 0.7);
  const l1 = wrap(x, R1, 34, N - 150);
  const a6 = seg(t, CARD, CARD + 0.6);
  const blockH = 20 + l1.length * 46 + 18 + 108;
  x.globalAlpha = a1;
  x.fillStyle = C.blue; x.fillRect(40, y - 16, 3, blockH * Math.max(a1 * 0.55, a6));
  l1.forEach((ln, i) => text(x, ln, 68, y + 20 + i * 46, 34, C.ink));
  x.globalAlpha = 1;
  y += 20 + l1.length * 46 + 18;

  x.globalAlpha = a6;
  rr(x, 68, y, N - 108, 108, 8);
  x.fillStyle = C.panel; x.fill();
  x.strokeStyle = C.line; x.lineWidth = 2; x.stroke();
  x.strokeStyle = C.dim; x.lineWidth = 2.5;
  x.strokeRect(96, y + 34, 30, 38);
  text(x, 'Transmittal v01', 150, y + 42, 30, C.ink);
  text(x, 'create transmittal', 150, y + 76, 25, C.dim);

  const hot = seg(t, OPEN_AT - 0.12, OPEN_AT) * (1 - seg(t, OPEN_AT, OPEN_AT + 0.3));
  const btnX = N - 220, btnY = y + 28, btnW = 140, btnH = 54;
  rr(x, btnX, btnY, btnW, btnH, 6);
  x.fillStyle = hot > 0.4 ? 'rgba(127,176,228,0.28)' : 'rgba(47,114,196,0.20)'; x.fill();
  x.strokeStyle = hot > 0.4 ? C.sky : C.blue; x.lineWidth = 2; x.stroke();
  text(x, 'Open', btnX + btnW / 2, btnY + btnH / 2 + 1, 28, C.sky, SANS, 'center');
  x.globalAlpha = 1;

  const app = seg(t, OPEN_AT - 1.3, OPEN_AT - 0.5);
  const gone = seg(t, OPEN_AT + 0.5, OPEN_AT + 1.0);
  if (app > 0 && gone < 1) {
    const px = lerp(N - 90, btnX + 78, easeInOut(seg(t, OPEN_AT - 1.3, OPEN_AT - 0.05)));
    const py = lerp(y + 190, btnY + 30, easeInOut(seg(t, OPEN_AT - 1.3, OPEN_AT - 0.05)));
    if (hot > 0) {
      x.beginPath(); x.arc(px + 2, py + 2, 10 + hot * 26, 0, 7);
      x.strokeStyle = 'rgba(127,176,228,' + (0.6 * (1 - hot)) + ')';
      x.lineWidth = 3; x.stroke();
    }
    cursor(x, px, py, app * (1 - gone));
  }
}

/* ---- the document register ----------------------------------------------
   Four screenshots stitched into one continuous list, in the order the app
   sorts them. Nineteen basement drawings across five disciplines; each one
   selects as it passes the read line, so the count builds with the scroll. */
const REG = [
  ['S0403', 'level 1 TReo Plan', '03'], ['S0401', 'level 1 Fmwk Plan', '04'],
  ['S0303', 'ground floor TReo Plan', '03'], ['S0301', 'ground floor Fmwk Plan', '04'],
  ['S0204', 'basement 1 Details Sht 1', '02', 1], ['S0203', 'basement 1 TReo Plan', '03', 1],
  ['S0202', 'basement 1 BReo Plan', '03', 1], ['S0201', 'basement 1 Fmwk Plan', '04', 1],
  ['S0102', 'basement 2 Details Sht 1', '02', 1], ['S0101', 'basement 2 Plan', '04', 1],
  ['S0030', 'Concrete Wall Details Sht 1', '03'],
  ['M-208', 'MECHANICAL SERVICES LEVEL 7', 'B'],
  ['M-202', 'MECHANICAL SERVICES GROUND LEVEL', 'B'],
  ['M-201', 'MECHANICAL SERVICES BASEMENT LEVEL', 'B', 1],
  ['M-200', 'MECHANICAL SERVICES BASEMENT LEVEL', 'B', 1],
  ['M-000', 'MECHANICAL SERVICES COVER SHEET', 'A'],
  ['H-301', 'STORMWATER SCHEMATIC', 'A'], ['H-103', 'GROUND FLOOR HYDRAULIC', 'D'],
  ['H-102', 'BASEMENT 1 HYDRAULIC SERVICES PLAN', 'D', 1],
  ['H-101', 'BASEMENT 2 HYDRAULIC SERVICES PLAN', 'C', 1],
  ['H-100', 'BASEMENT 2 INGROUND HYDRAULIC', 'C', 1],
  ['H-000', 'COVER SHEET, NOTES & LEGEND', 'KERB'],
  ['E090', 'GROUND FLOOR', 'Cur\u2026'],
  ['E080', 'BASEMENT B1', 'Cur\u2026', 1], ['E070', 'BASEMENT B2', 'Cur\u2026', 1],
  ['E001', 'LEGEND AND NOTES', 'Cur\u2026'],
  ['CC-24', 'DETAILS STAIR', 'B'], ['CC-11', 'SECTIONS SHT 1', 'E'],
  ['CC-36', 'ELEC BASEMENT 1', 'B', 1], ['CC-35', 'ELEC BASEMENT 2', 'B', 1],
  ['CC-26', 'RCP BASEMENT 1', 'C', 1], ['CC-25', 'RCP BASEMENT 2', 'C', 1],
  ['CC-03', 'BASEMENT 1', 'F', 1], ['CC-02', 'BASEMENT 2', 'F', 1],
  ['CC-01', 'SETOUT PLAN', 'D']
];

const ROW = 60, TOP = 218, VIEW_T = 196, VIEW_B = N - 26;
const SCROLL0 = 0.8, SCROLL1 = 6.8;               // register scroll window
const READ = VIEW_T + (VIEW_B - VIEW_T) * 0.78;   // rows commit as they cross this

function screenRegister(x, t) {
  const total = REG.length * ROW;
  // far enough that the last two rows in the list still cross the read line
  const span = Math.max(0, TOP + total - VIEW_B + 150);
  const scroll = span * easeInOut(seg(t, SCROLL0, SCROLL1));

  // the pass only begins when the scroll does; before that the register is idle
  const armed = easeInOut(seg(t, SCROLL0 - 0.5, SCROLL0 + 0.5));

  // how many selected rows have crossed the read line
  let count = 0;
  REG.forEach((r, i) => { if (r[3] && TOP + i * ROW - scroll < READ) count++; });
  count = Math.round(count * armed);

  // toolbar
  text(x, 'DOCUMENT REGISTER', 34, 114, 24, C.ink, MONO);
  const started = seg(t, 0.2, 0.6);
  x.globalAlpha = started;
  rr(x, N - 210, 92, 176, 44, 6);
  x.fillStyle = 'rgba(224,164,74,0.10)'; x.fill();
  x.strokeStyle = C.amber; x.lineWidth = 2; x.stroke();
  text(x, count + ' selected', N - 122, 115, 24, C.amber, MONO, 'center');
  x.globalAlpha = 1;

  // column head
  x.fillStyle = C.line; x.fillRect(28, 196, N - 56, 1.5);
  text(x, '#', 48, 173, 20, C.dim, MONO);
  text(x, 'Title', 168, 173, 20, C.dim, MONO);
  text(x, 'Rev', 800, 173, 20, C.dim, MONO);
  text(x, 'Category', 890, 173, 20, C.dim, MONO);

  x.save();
  x.beginPath(); x.rect(28, VIEW_T + 2, N - 56, VIEW_B - VIEW_T); x.clip();
  REG.forEach((r, i) => {
    const y = TOP + i * ROW - scroll;
    if (y > VIEW_B || y + ROW < VIEW_T) return;
    const sel = r[3] && y < READ && armed > 0.02;
    // the moment of commitment: a short flash as the row crosses
    const fresh = sel ? clamp(1 - (READ - y) / 90, 0, 1) : 0;
    x.fillStyle = C.line; x.fillRect(28, y + ROW - 1, N - 56, 1);
    if (sel) {
      x.fillStyle = 'rgba(47,114,196,' + ((0.16 + 0.26 * fresh) * armed) + ')';
      x.fillRect(28, y, N - 56, ROW - 1);
      x.fillStyle = fresh > 0.15 ? C.sky : C.blue;
      x.fillRect(28, y, 4, ROW - 1);
    }
    const c = sel ? C.ink : C.dim;
    text(x, r[0], 48, y + ROW / 2, 22, sel ? C.sky : C.dim, MONO);
    text(x, r[1], 168, y + ROW / 2, 23, c);
    text(x, r[2], 800, y + ROW / 2, 21, sel ? C.ink : C.dim, MONO);
    text(x, 'Inbox', 890, y + ROW / 2, 21, sel ? C.amber : C.dim, MONO);
  });
  x.restore();

  // the read line itself, only while it is doing work
  const live = seg(t, SCROLL0, SCROLL0 + 0.5) * (1 - seg(t, SCROLL1 - 0.4, SCROLL1 + 0.3));
  if (live > 0) {
    x.globalAlpha = live * 0.5;
    x.fillStyle = C.sky; x.fillRect(28, READ, N - 56, 1.5);
    x.globalAlpha = 1;
  }
}

/* ---- the transmittal draft ----------------------------------------------- */
const TX = [
  ['1', 'E070', 'BASEMENT B2', 'Current', 'Project'],
  ['2', 'E080', 'BASEMENT B1', 'Current', 'Project'],
  ['3', 'CC-02', 'BASEMENT 2', 'F', 'Architectural'],
  ['4', 'CC-03', 'BASEMENT 1', 'F', 'Architectural'],
  ['5', 'CC-25', 'RCP BASEMENT 2', 'C', 'Architectural'],
  ['6', 'CC-26', 'RCP BASEMENT 1', 'C', 'Architectural'],
  ['7', 'CC-35', 'ELEC BASEMENT 2', 'B', 'Architectural'],
  ['8', 'CC-36', 'ELEC BASEMENT 1', 'B', 'Architectural'],
  ['9', 'S0101', 'basement 2 Plan', '04', 'Structural'],
  ['10', 'S0102', 'basement 2 Details Sht 1', '02', 'Structural'],
  ['11', 'S0201', 'basement 1 Fmwk Plan', '04', 'Structural'],
  ['12', 'S0202', 'basement 1 BReo Plan', '03', 'Structural'],
  ['13', 'S0203', 'basement 1 TReo Plan', '03', 'Structural'],
  ['14', 'S0204', 'basement 1 Details Sht 1', '02', 'Structural'],
  ['15', 'H-100', 'BASEMENT 2 INGROUND HYDRAULIC', 'C', 'Hydraulic'],
  ['16', 'H-101', 'BASEMENT 2 HYDRAULIC SERVICES PLAN', 'C', 'Hydraulic'],
  ['17', 'H-102', 'BASEMENT 1 HYDRAULIC SERVICES PLAN', 'D', 'Hydraulic'],
  ['18', 'M-200', 'MECHANICAL SERVICES BASEMENT LEVEL', 'B', 'Project'],
  ['19', 'M-201', 'MECHANICAL SERVICES BASEMENT LEVEL', 'B', 'Project']
];
const TROW = 54;

function screenDraft(x, t) {
  const headH = 546;
  const total = headH + TX.length * TROW + 60;
  const span = Math.max(0, total - (N - 100));
  const scroll = span * easeInOut(seg(t, 1.6, 9.5));

  x.save();
  x.beginPath(); x.rect(4, 78, N - 8, N - 82); x.clip();
  x.translate(0, -scroll);

  text(x, 'Transmittal', 40, 138, 52, C.ink);

  x.fillStyle = C.amber; x.fillRect(40, 206, 4, 46);
  text(x, 'Draft only \u2014 not issued or sent.', 62, 220, 26, C.ink);
  text(x, 'Confirm the recipient before distribution.', 62, 248, 25, C.dim);

  const META = [['Project', 'Mosaic Apartments'], ['To', 'TBC \u2014 confirm before issue'],
                ['Purpose', 'Basement drawings transmittal']];
  META.forEach(([k, v], i) => {
    const y = 296 + i * 50;
    if (i === 1) { x.fillStyle = 'rgba(47,114,196,0.10)'; x.fillRect(40, y, N - 80, 47); }
    x.strokeStyle = C.line; x.lineWidth = 1.5; x.strokeRect(40, y, N - 80, 47);
    if (i === 1) { x.fillStyle = C.blue; x.fillRect(40, y, 3, 47); }
    text(x, k, 62, y + 24, 23, C.dim);
    text(x, v, 250, y + 24, 24, C.ink);
  });

  text(x, 'Documents transmitted', 40, 490, 32, C.sky);
  x.fillStyle = C.line; x.fillRect(40, 516, N - 80, 1.5);

  const hy = headH + 24;
  x.fillStyle = C.line; x.fillRect(40, hy + 44, N - 80, 1.5);
  text(x, '#', 62, hy + 22, 20, C.dim, MONO);
  text(x, 'Document no.', 120, hy + 22, 20, C.dim, MONO);
  text(x, 'Title', 280, hy + 22, 20, C.dim, MONO);
  text(x, 'Rev', 760, hy + 22, 20, C.dim, MONO);
  text(x, 'Category', 850, hy + 22, 20, C.dim, MONO);

  TX.forEach((r, i) => {
    const y = hy + 44 + i * TROW;
    const on = seg(t, 0.6 + i * 0.05, 0.9 + i * 0.05);
    x.globalAlpha = on;
    x.fillStyle = C.line; x.fillRect(40, y + TROW - 1, N - 80, 1);
    text(x, r[0], 62, y + TROW / 2, 21, C.dim, MONO);
    text(x, r[1], 120, y + TROW / 2, 22, C.sky, MONO);
    text(x, r[2], 280, y + TROW / 2, 22, C.ink);
    text(x, r[3], 760, y + TROW / 2, 21, C.dim, MONO);
    text(x, r[4], 850, y + TROW / 2, 21, C.dim);
    x.globalAlpha = 1;
  });

  x.restore();
}

/* One rail: the register holds until the draft is opened, then swipes out. */
const RAIL = [
  { fn: screenRegister, at: 6.6, out: OPEN_AT + 0.1 },
  { fn: screenDraft, at: OPEN_AT + 0.5, out: 99 }
];
const SW = 0.5;

function drawApp(x, t) {
  shell(x, 'SITEWISE \u00b7 PROJECT WORKSPACE');
  x.save();
  x.beginPath(); x.rect(4, 78, N - 8, N - 82); x.clip();
  RAIL.forEach((s) => {
    const inP = easeInOut(seg(t, s.at - SW, s.at));
    const outP = easeInOut(seg(t, s.out, s.out + SW));
    if (inP <= 0 || outP >= 1) return;
    x.save();
    x.translate((1 - inP) * N + outP * -N, 0);
    s.fn(x, t - s.at);
    x.restore();
  });
  x.restore();
}

export function makeScreen(kind) {
  const c = document.createElement('canvas');
  c.width = c.height = N;
  const x = c.getContext('2d');
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  let last = -999;
  return {
    tex,
    draw(t) {
      if (Math.abs(t - last) < 0.008) return;
      last = t;
      x.clearRect(0, 0, N, N);
      (kind === 'chat' ? drawChat : drawApp)(x, Math.max(0, t));
      tex.needsUpdate = true;
    }
  };
}
