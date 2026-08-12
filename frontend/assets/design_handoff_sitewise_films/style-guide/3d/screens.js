/* Two product screens, drawn to canvas so they can live on a face of the cube
   and still be a pure function of time. Deliberately reduced: four columns
   instead of twelve, nine rows instead of forty. On a face seen at an angle the
   gesture has to read, not the data. Colours and type follow the style guide,
   so this is the product in the brand's own voice rather than a screenshot. */
import { THREE } from './cube-geometry.js';
import { drawComposer } from './composer.js?v=5';

const C = {
  bg: '#0B0D10', panel: '#101319', line: '#1E232B', head: '#161A21',
  ink: '#D6D6D0', dim: '#8A8F98', blue: '#2F72C4', sky: '#7FB0E4',
  amber: '#E0A44A', green: '#57A87A'
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
  const words = s.split(' ');
  const lines = []; let cur = '';
  for (const w of words) {
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

/* ---- the chat ---------------------------------------------------------- */
const Q = 'Process this month\u2019s invoices and reconcile against the cost plan.';
const R1 = 'Current month\u2019s invoices have been queued for processing into the ' +
  'invoice register and Cost Plan.';

const SEND = 5.6;

function drawChat(x, t) {
  shell(x, 'SITEWISE \u00b7 ASSISTANT');

  // the composer's dictate glyph, in this canvas's space (composer.js geometry,
  // x0:34 y0:N-258 w:N-68 scaled)
  const MIC_X = 800, MIC_Y = 934;
  const DICT_IN = 0.15, DICT_CLICK = 0.6, DICT_OUT = 3.6;
  const recording = t >= DICT_CLICK && t < DICT_OUT;
  const typed = seg(t, DICT_CLICK + 0.1, DICT_OUT);
  const sent = t >= SEND;

  /* the composer holds the frame alone until the cursor clicks the mark */
  if (!sent) {
    const shown = Math.floor(Q.length * typed);
    drawComposer(x, {
      x0: 34, y0: N - 258, w: N - 68, theme: 'dark',
      text: Q.slice(0, shown),
      placeholder: 'Ask about your project documents',
      caret: !recording && (Math.floor(t * 2.2) % 2 === 0 || typed >= 1),
      depth: 1, hot: seg(t, SEND - 0.5, SEND), dictating: recording
    });

    /* dictation: the cursor clicks the mic, then the bars carry the voice
       while the question fills itself in */
    const toMic = seg(t, DICT_IN, DICT_CLICK - 0.05);
    if (toMic > 0 && t < DICT_CLICK + 0.3) {
      const k = easeInOut(toMic);
      const px = lerp(N - 130, MIC_X, k), py = lerp(N - 56, MIC_Y, k);
      const click = seg(t, DICT_CLICK - 0.1, DICT_CLICK) * (1 - seg(t, DICT_CLICK, DICT_CLICK + 0.3));
      if (click > 0) {
        x.beginPath(); x.arc(px + 2, py + 2, 8 + click * 20, 0, 7);
        x.strokeStyle = 'rgba(127,176,228,' + (0.6 * (1 - click)) + ')';
        x.lineWidth = 3; x.stroke();
      }
      cursor(x, px, py, toMic * (1 - seg(t, DICT_CLICK + 0.05, DICT_CLICK + 0.3)));
    }
    if (recording) {
      x.beginPath(); x.arc(MIC_X, MIC_Y - 5, 22, 0, 7);
      x.strokeStyle = 'rgba(127,176,228,0.4)'; x.lineWidth = 2; x.stroke();
      for (let i = 0; i < 4; i++) {
        const h = 6 + (0.5 + 0.5 * Math.sin(t * 9 + i * 2.1)) * 14;
        x.fillStyle = C.sky;
        x.fillRect(MIC_X + 14 + i * 9, MIC_Y - 5 - h / 2, 5, h);
      }
    }

    const app = seg(t, 4.0, 4.4);
    if (app > 0) {
      const k = easeInOut(seg(t, 4.2, SEND - 0.05));
      const px = lerp(MIC_X, 922, k), py = lerp(MIC_Y, 880, k);
      const ring = seg(t, SEND - 0.2, SEND);
      if (ring > 0) {
        x.beginPath(); x.arc(px + 2, py + 2, 10 + ring * 24, 0, 7);
        x.strokeStyle = 'rgba(127,176,228,' + (0.6 * (1 - ring)) + ')';
        x.lineWidth = 3; x.stroke();
      }
      cursor(x, px, py, app);
    }
    return;
  }

  /* the question rides up as a bubble sized to its own text; everything the
     assistant says sits left of a blue gutter, in one voice */
  const rise = easeOut(seg(t, SEND, SEND + 0.7));
  const qL = wrap(x, Q, 34, 520);
  x.font = `34px ${SANS}`;
  let qw = 0;
  qL.forEach((ln) => { qw = Math.max(qw, x.measureText(ln).width); });
  const bw = Math.min(N - 140, qw + 60), bh = 32 + qL.length * 46;
  const by = 555 + (1 - rise) * 125;
  x.globalAlpha = rise;
  rr(x, N - 34 - bw, by, bw, bh, 12);
  x.fillStyle = 'rgba(47,114,196,0.18)'; x.fill();
  x.strokeStyle = 'rgba(47,114,196,0.55)'; x.lineWidth = 2; x.stroke();
  qL.forEach((ln, i) => text(x, ln, N - 34 - bw + 30, by + 38 + i * 46, 34, C.ink, SANS, 'left'));
  x.globalAlpha = 1;

  const top = by + bh + 50;
  const gut = (h2) => { x.fillStyle = C.blue; x.fillRect(40, top - 16, 3, h2); };

  const think = seg(t, 6.5, 9.6);
  if (think < 1) {
    gut(120);
    text(x, 'Working', 68, top + 16, 27, C.dim, MONO);
    for (let i = 0; i < 3; i++) {
      const p = (Math.sin(t * 5 - i * 0.7) + 1) / 2;
      x.globalAlpha = 0.25 + p * 0.75;
      x.fillStyle = C.sky;
      x.beginPath(); x.arc(218 + i * 26, top + 16, 6, 0, 7); x.fill();
    }
    x.globalAlpha = 1;
    return;
  }

  let y = top;
  const l1 = wrap(x, R1, 34, N - 190);
  x.globalAlpha = seg(t, 9.7, 10.4);
  l1.forEach((ln, i) => text(x, ln, 68, y + 20 + i * 46, 34, C.ink));
  x.globalAlpha = 1;
  y += 20 + l1.length * 46 + 40;

  x.globalAlpha = seg(t, 12.0, 12.6);
  rr(x, 68, y, N - 108, 72, 8);
  x.strokeStyle = C.line; x.lineWidth = 2; x.stroke();
  text(x, 'process invoices completed.', 94, y + 37, 30, C.ink);
  x.globalAlpha = 1;

  gut(y + 72 - (top - 16));
}

/* ---- the application --------------------------------------------------- */
const REPO = [
  ['44 TAX INVOICE VERTEX COST ADVISORY 04.pdf', 'Inbox', 1],
  ['43 TAX INVOICE VERTEX COST ADVISORY 03.pdf', 'Inbox', 1],
  ['1115 CC-01 SETOUT PLAN D.pdf', 'Drawings', 0],
  ['1115 CC-02 BASEMENT 2 F.pdf', 'Drawings', 0],
  ['42 TAX INVOICE FLOWLINE HYDRAULICS.pdf', 'Inbox', 1],
  ['1115 CC-04 GROUND FLOOR J.pdf', 'Drawings', 0],
  ['1115 CC-06 LEVEL 02 F.pdf', 'Drawings', 0],
  ['41 TAX INVOICE CATENARY STRUCTURES.pdf', 'Inbox', 1],
  ['45 TAX INVOICE QUOIN ARCHITECTURE 02.pdf', 'Inbox', 1],
  ['1115 CC-08 LEVEL 05 E.pdf', 'Drawings', 0]
];
const REG = [
  ['04 Aug 26', 'Vertex Cost Advisory', '$14,300', '4.2 \u00b7 Quantity surveyor'],
  ['11 Aug 26', 'Flowline Hydraulics', '$8,125', '9 \u00b7 Hydraulic / wastewater'],
  ['18 Aug 26', 'Catenary Structures', '$10,450', '15 \u00b7 Framing and roof'],
  ['22 Aug 26', 'Quoin Architecture', '$25,920', '1 \u00b7 Architect / PM fee'],
  ['26 Aug 26', 'Vertex Cost Advisory', '$6,400', '4.2 \u00b7 Quantity surveyor']
];
const PLAN = [
  ['1', 'Architect / PM fee', '$96,000', '$41,760', '$54,240', 0],
  ['4.2', 'Quantity surveyor / cost advisory', '$45,000', '$45,000', '$0', 1],
  ['9', 'Hydraulic / wastewater', '$32,500', '$34,125', '\u2212$1,625', 2],
  ['12', 'Preliminaries', '$136,000', '$0', '$136,000', 0],
  ['13', 'Siteworks and demolition', '$47,000', '$0', '$47,000', 0],
  ['15', 'Framing and roof', '$178,000', '$33,440', '$144,560', 1],
  ['16', 'External envelope and lockup', '$323,000', '$0', '$323,000', 0]
];

function tableHead(x, y, cols) {
  x.fillStyle = C.line; x.fillRect(28, y + 54, N - 56, 1.5);
  cols.forEach(([label, cxp, align]) => text(x, label, cxp, y + 27, 21, C.dim, MONO, align));
}
function row(x, y, h) {
  x.fillStyle = C.line; x.fillRect(28, y + h, N - 56, 1);
}

function screenRepo(x, t) {
  text(x, 'DOCUMENT REPOSITORY', 34, 116, 24, C.ink, MONO);
  const done = seg(t, 0.2, 2.0);
  rr(x, 28, 148, N - 56, 46, 6);
  x.strokeStyle = C.line; x.lineWidth = 2; x.stroke();
  x.fillStyle = C.blue; x.fillRect(30, 150, (N - 60) * done, 42);
  text(x, done < 1 ? 'processing files\u2026' : 'Finished ingesting 10 documents.',
    48, 171, 24, done < 1 ? C.ink : C.bg);
  tableHead(x, 214, [['Title', 48], ['Category', N - 60, 'right']]);
  let inv = 0;
  REPO.forEach((r, i) => {
    const y = 270 + i * 64;
    const lit = r[2] && t > 2.5 + (inv++) * 0.75;
    row(x, y, 63, i % 2 === 1);
    if (lit) { x.fillStyle = 'rgba(47,114,196,0.22)'; x.fillRect(28, y, N - 56, 63);
               x.fillStyle = C.amber; x.fillRect(28, y, 4, 63); }
    text(x, r[0], 48, y + 32, 24, lit ? C.ink : C.dim);
    text(x, r[1], N - 60, y + 32, 22, lit ? C.amber : C.dim, MONO, 'right');
  });
}

/* The one that matters: the model maps four of five invoices on its own and
   leaves the fifth amber. Rather than hide that, the film leans on it — the
   user opens the picker, chooses the cost item, and moves on. Human in the
   loop is the feature, so it gets the screen time. */
const MENU = [
  ['g', 'Fees and charges'],
  ['i', '1 \u00b7 Quoin Architecture Pty Ltd architect / PM fee', 1],
  ['i', '2 \u00b7 DA and CC authority fees \u00b7 TBC'],
  ['g', 'Consultants'],
  ['i', '6 \u00b7 Structural engineer \u00b7 TBC'],
  ['i', '9 \u00b7 Hydraulic / wastewater']
];
const ORPHAN = 3;                       // the row the model could not place
const MENU_X = 496, MENU_W = 476;

function cursor(x, px, py, a) {
  x.save(); x.globalAlpha = a; x.translate(px, py);
  x.beginPath(); x.moveTo(0, 0); x.lineTo(0, 30); x.lineTo(8, 23);
  x.lineTo(13, 34); x.lineTo(19, 31); x.lineTo(14, 21); x.lineTo(24, 20);
  x.closePath();
  x.fillStyle = '#F4F6F9'; x.fill();
  x.strokeStyle = '#0B0D10'; x.lineWidth = 2.5; x.stroke();
  x.restore();
}

function screenReg(x, t) {
  text(x, 'INVOICES REGISTER \u00b7 KAVANAGH', 34, 116, 24, C.ink, MONO);
  tableHead(x, 158, [['Date', 48], ['Company', 250], ['Cost item', 560], ['Amount', N - 60, 'right']]);

  const OPEN = 6.5, PICK = 8.9, CLOSE = 9.5, FIXED = 9.7;
  const open = seg(t, OPEN, OPEN + 0.28) * (1 - seg(t, CLOSE, CLOSE + 0.22));
  const travel = easeInOut(seg(t, OPEN + 0.4, PICK));  // single clock drives both the highlight and the cursor
  let orphanPillY = 0;

  REG.forEach((r, i) => {
    const on = seg(t, 0.4 + i * 0.7, 0.9 + i * 0.7);
    if (on <= 0) return;
    const y = 214 + i * 92;
    x.globalAlpha = on;
    row(x, y, 91, i % 2 === 1);
    x.fillStyle = C.blue; x.fillRect(28, y, 4, 91);
    text(x, r[0], 48, y + 46, 24, C.dim, MONO);
    text(x, r[1], 250, y + 46, 26, C.ink);

    const isOrphan = i === ORPHAN;
    const m0 = isOrphan ? FIXED : 1.9 + i * 0.7;
    const mapped = seg(t, m0, m0 + 0.5);
    const glow = mapped * (1 - seg(t, m0 + 0.5, m0 + 1.7));   // the confirming flash

    rr(x, 552, y + 22, 432, 48, 6);
    if (glow > 0) { x.fillStyle = 'rgba(87,168,122,' + (0.30 * glow) + ')'; x.fill(); }
    const armed = isOrphan && t > OPEN - 0.5 && mapped < 1;
    x.strokeStyle = mapped >= 1 ? (glow > 0 ? C.green : C.line)
                  : (armed ? C.sky : C.amber);
    x.lineWidth = armed || glow > 0 ? 3 : 2; x.stroke();
    text(x, mapped < 1 ? 'Choose cost item' : r[3], 572, y + 46, 23,
      mapped < 1 ? C.amber : (glow > 0 ? C.green : C.sky));
    // chevron
    x.strokeStyle = mapped < 1 ? C.amber : C.dim; x.lineWidth = 2.5;
    x.beginPath(); x.moveTo(922, y + 41); x.lineTo(930, y + 50); x.lineTo(938, y + 41); x.stroke();

    text(x, r[2], N - 60, y + 46, 26, C.ink, SANS, 'right');
    x.globalAlpha = 1;
    if (isOrphan) orphanPillY = y + 70;
  });

  /* the picker, drawn over the rows it covers */
  let hy = 0;
  if (open > 0) {
    const h = 44 + MENU.reduce((a, m) => a + (m[0] === 'g' ? 34 : 36), 0);
    x.save();
    x.globalAlpha = open;
    rr(x, MENU_X, orphanPillY + 8, MENU_W, h * open, 8);
    x.fillStyle = '#0E1116'; x.fill();
    x.strokeStyle = C.line; x.lineWidth = 2; x.stroke();
    x.save(); x.clip();
    let my = orphanPillY + 8 + 30;
    text(x, 'Choose cost item', MENU_X + 22, my, 22, C.dim);
    my += 30;
    // the highlight settles on the item the user wants; the cursor below reads
    // its position off this same pass, so the two never drift apart
    let idx = 0, seen = 0;
    const items = MENU.filter((m) => m[0] === 'i');
    const want = items.findIndex((m) => m[2]);
    const cur = Math.round(lerp(items.length - 1, want, travel));
    MENU.forEach((m) => {
      if (m[0] === 'g') { my += 8; text(x, m[1], MENU_X + 22, my + 10, 20, C.dim, SANS); my += 26; return; }
      const isCur = seen === cur;
      if (isCur) { x.fillStyle = 'rgba(214,214,208,0.16)'; x.fillRect(MENU_X + 2, my - 8, MENU_W - 4, 36); }
      const tail = m[1].endsWith('TBC');
      text(x, m[1], MENU_X + 22, my + 10, 21, tail ? C.dim : C.sky);
      if (isCur) hy = my + 10;
      seen++; my += 36;
    });
    x.restore(); x.restore();
    x.globalAlpha = 1;
  }

  /* the hand: to the pill, click, down the list, click */
  const app = seg(t, OPEN - 0.9, OPEN - 0.2);
  const gone = seg(t, CLOSE + 0.3, CLOSE + 0.8);
  if (app > 0 && gone < 1) {
    const px = lerp(760, MENU_X + 150, travel);
    const py = lerp(orphanPillY - 24, hy || orphanPillY + 90, travel);
    const click = Math.max(seg(t, OPEN - 0.12, OPEN) * (1 - seg(t, OPEN, OPEN + 0.25)),
                           seg(t, PICK - 0.12, PICK) * (1 - seg(t, PICK, PICK + 0.25)));
    if (click > 0) {
      x.beginPath(); x.arc(px + 2, py + 2, 10 + click * 22, 0, 7);
      x.strokeStyle = 'rgba(127,176,228,' + (0.55 * (1 - click)) + ')';
      x.lineWidth = 3; x.stroke();
    }
    cursor(x, px, py, app * (1 - gone));
  }
}

function screenPlan(x, t) {
  text(x, 'PROJECT COST PLAN \u00b7 KAVANAGH', 34, 116, 24, C.ink, MONO);
  text(x, 'Selected month \u00b7 Aug-26', N - 34, 116, 22, C.amber, MONO, 'right');
  tableHead(x, 158, [['Cost item', 48], ['Budget', 620, 'right'],
                     ['Claimed', 800, 'right'], ['Remaining', N - 60, 'right']]);
  PLAN.forEach((r, i) => {
    const y = 214 + i * 88;
    row(x, y, 87, i % 2 === 1);
    const upd = r[5] ? seg(t, 1.0 + i * 0.62, 1.8 + i * 0.62) : 0;
    if (upd > 0) {
      x.fillStyle = r[5] === 2 ? 'rgba(224,164,74,0.16)' : 'rgba(87,168,122,0.14)';
      x.fillRect(28, y, N - 56, 87);
      x.fillStyle = r[5] === 2 ? C.amber : C.green; x.fillRect(28, y, 4, 87);
    }
    text(x, r[0], 48, y + 44, 22, C.dim, MONO);
    text(x, r[1], 108, y + 44, 26, C.ink);
    text(x, r[2], 620, y + 44, 25, C.dim, SANS, 'right');
    text(x, r[3], 800, y + 44, 25, upd > 0 ? C.ink : C.dim, SANS, 'right');
    text(x, r[4], N - 60, y + 44, 25,
      upd > 0 ? (r[5] === 2 ? C.amber : C.green) : C.dim, SANS, 'right');
  });
}

/* Three views on one rail: each swipes the next in, so the sequence reads as
   one application doing the work rather than three unrelated pictures. */
const RAIL = [
  { fn: screenRepo, at: 9.9, out: 15.1 },
  { fn: screenReg, at: 15.5, out: 28.9 },
  { fn: screenPlan, at: 29.3, out: 99 }
];
const SW = 0.55;

const TABS = ['Cost Plan', 'Invoices', 'Variations'];
/* The repository is one view, not three tabs — the tab bar arrives with the
   register that it belongs to. */
const REPO_TAB = ['Document Repository'];
function tabRects(x, labels) {
  x.font = `22px ${SANS}`;
  let tx = 34;
  return labels.map((label) => {
    const w = x.measureText(label).width + 54;
    const r = { x: tx, y: 20, w, h: 40, label };
    tx += w + 10;
    return r;
  });
}
function tabBar(x, rects, activeIdx) {
  rects.forEach((r, i) => {
    const isActive = i === activeIdx;
    if (isActive) { x.fillStyle = 'rgba(214,214,208,0.12)'; rr(x, r.x, r.y, r.w, r.h, 6); x.fill(); }
    const ix = r.x + 16, iy = r.y + r.h / 2;
    x.strokeStyle = isActive ? C.ink : C.dim; x.lineWidth = 1.6;
    x.strokeRect(ix, iy - 6, 12, 12);
    x.beginPath(); x.moveTo(ix + 6, iy - 6); x.lineTo(ix + 6, iy + 6);
    x.moveTo(ix, iy); x.lineTo(ix + 12, iy); x.stroke();
    text(x, r.label, r.x + 38, iy + 1, 21, isActive ? C.ink : C.dim, SANS);
  });
}

function iconDownload(x, cx, cy, col) {
  x.strokeStyle = col; x.lineWidth = 1.8;
  x.beginPath(); x.moveTo(cx, cy - 9); x.lineTo(cx, cy + 3); x.stroke();
  x.beginPath(); x.moveTo(cx - 6, cy - 3); x.lineTo(cx, cy + 3); x.lineTo(cx + 6, cy - 3); x.stroke();
  x.beginPath(); x.moveTo(cx - 9, cy + 9); x.lineTo(cx + 9, cy + 9); x.stroke();
}
function iconCopy(x, cx, cy, col) {
  x.strokeStyle = col; x.lineWidth = 1.8;
  x.strokeRect(cx - 8, cy - 8, 13, 15);
  x.fillStyle = C.bg; x.fillRect(cx - 3, cy - 4, 13, 15);
  x.strokeRect(cx - 3, cy - 4, 13, 15);
}
function excelPopup(x, a) {
  if (a <= 0.002) return;
  const bx = N - 214, by = 84, bw = 172, bh = 56;
  x.save(); x.globalAlpha = a;
  rr(x, bx, by, bw, bh, 8);
  x.fillStyle = '#12151A'; x.fill();
  x.strokeStyle = C.line; x.lineWidth = 2; x.stroke();
  rr(x, bx + 15, by + 15, 26, 26, 4);
  x.fillStyle = C.green; x.fill();
  text(x, 'X', bx + 28, by + 29, 15, '#0B0D10', SANS, 'center');
  text(x, 'Excel', bx + 54, by + 29, 23, C.ink, SANS);
  x.restore();
}

function drawApp(x, t) {
  shell(x, '');
  const rects = tabRects(x, TABS);
  const clickAt = RAIL[1].out - 0.15;
  const swap = seg(t, RAIL[1].at - 0.35, RAIL[1].at - 0.05);
  if (swap < 1) {
    x.save(); x.globalAlpha = 1 - swap;
    tabBar(x, tabRects(x, REPO_TAB), 0);
    x.restore();
  }
  if (swap > 0) {
    x.save(); x.globalAlpha = swap;
    tabBar(x, rects, t < clickAt ? 1 : 0);
    x.restore();
  }

  const dlPos = { x: N - 40, y: 37 }, cpPos = { x: N - 88, y: 37 };
  const DL_CLICK = 30.1, EX_CLICK = 30.9;
  const dlLit = seg(t, DL_CLICK - 0.15, DL_CLICK) * (1 - seg(t, EX_CLICK, EX_CLICK + 0.3));
  iconCopy(x, cpPos.x, cpPos.y, C.dim);
  iconDownload(x, dlPos.x, dlPos.y, dlLit > 0 ? C.ink : C.dim);

  const target = rects[0];
  const tpx = target.x + 30, tpy = target.y + 25;
  const appHand = seg(t, clickAt - 0.9, clickAt - 0.2);
  const goneHand = seg(t, clickAt + 0.25, clickAt + 0.65);
  if (appHand > 0 && goneHand < 1) {
    const k = easeInOut(seg(t, clickAt - 0.9, clickAt - 0.25));
    const px = lerp(640, tpx, k), py = lerp(640, tpy, k);
    const click = seg(t, clickAt - 0.12, clickAt) * (1 - seg(t, clickAt, clickAt + 0.3));
    if (click > 0) {
      x.beginPath(); x.arc(px + 2, py + 2, 8 + click * 20, 0, 7);
      x.strokeStyle = 'rgba(127,176,228,' + (0.6 * (1 - click)) + ')';
      x.lineWidth = 3; x.stroke();
    }
    cursor(x, px, py, appHand * (1 - goneHand));
  }

  x.save();
  x.beginPath(); x.rect(4, 78, N - 8, N - 82); x.clip();
  RAIL.forEach((s, i) => {
    const inP = easeInOut(seg(t, s.at - SW, s.at));
    const outP = easeInOut(seg(t, s.out, s.out + SW));
    if (inP <= 0 || outP >= 1) return;
    const dx = (1 - inP) * N + outP * -N;
    x.save(); x.translate(dx, 0);
    x.globalAlpha = 1;
    s.fn(x, t - s.at);
    x.restore();
  });
  x.restore();

  /* the hand: to the download icon, click, the Excel row pops out, click again */
  const exPopup = seg(t, DL_CLICK, DL_CLICK + 0.25) * (1 - seg(t, EX_CLICK + 0.1, EX_CLICK + 0.4));
  excelPopup(x, exPopup);
  const exPos = { x: N - 214 + 28, y: 84 + 28 };
  const dlApp = seg(t, DL_CLICK - 0.7, DL_CLICK - 0.15);
  const dlGone = seg(t, DL_CLICK + 0.15, DL_CLICK + 0.45);
  if (dlApp > 0 && dlGone < 1) {
    const k = easeInOut(seg(t, DL_CLICK - 0.7, DL_CLICK - 0.2));
    const px = lerp(target.x + target.w + 40, dlPos.x, k), py = lerp(tpy + 60, dlPos.y, k);
    const click = seg(t, DL_CLICK - 0.1, DL_CLICK) * (1 - seg(t, DL_CLICK, DL_CLICK + 0.28));
    if (click > 0) {
      x.beginPath(); x.arc(px + 2, py + 2, 8 + click * 18, 0, 7);
      x.strokeStyle = 'rgba(127,176,228,' + (0.6 * (1 - click)) + ')';
      x.lineWidth = 3; x.stroke();
    }
    cursor(x, px, py, dlApp * (1 - dlGone));
  }
  const exApp = seg(t, DL_CLICK + 0.15, EX_CLICK - 0.15);
  const exGone = seg(t, EX_CLICK + 0.1, EX_CLICK + 0.4);
  if (exApp > 0 && exGone < 1) {
    const k = easeInOut(seg(t, DL_CLICK + 0.15, EX_CLICK - 0.2));
    const px = lerp(dlPos.x, exPos.x, k), py = lerp(dlPos.y, exPos.y, k);
    const click = seg(t, EX_CLICK - 0.1, EX_CLICK) * (1 - seg(t, EX_CLICK, EX_CLICK + 0.28));
    if (click > 0) {
      x.beginPath(); x.arc(px + 2, py + 2, 8 + click * 18, 0, 7);
      x.strokeStyle = 'rgba(87,168,122,' + (0.6 * (1 - click)) + ')';
      x.lineWidth = 3; x.stroke();
    }
    cursor(x, px, py, exApp * (1 - exGone));
  }
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
