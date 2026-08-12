/* The project profile sheet, drawn on the inside of the glazing face.
   Light sheet over the blue plane rather than the app's dark chrome — the face
   is already blue, so the styling inverts to keep the two readable together.
   One canvas carries the whole act: prompt, auto-populate, summary, then a
   second prompt where the user configures a project from nothing. */

import { drawComposer } from './composer.js?v=5';

const W = 1200, H = 1200;
const PAD = 40, IW = W - PAD * 2;

/* Drawn straight onto the blue glazing — no sheet, no cards. White type,
   white rules, transparent ground, so the face itself is the background. */
const INK = '#FFFFFF', MUTE = 'rgba(255,255,255,0.58)';
const LINE = 'rgba(255,255,255,0.30)', HOT = 'rgba(255,255,255,0.94)';
const F = (s, w) => `${w || 400} ${s}px 'Hanken Grotesk', Helvetica, sans-serif`;
const MONO = (s) => `500 ${s}px 'IBM Plex Mono', monospace`;

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const seg = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

function rr(x, c, y, w, h, r) {
  x.beginPath();
  x.moveTo(c + r, y); x.arcTo(c + w, y, c + w, y + h, r);
  x.arcTo(c + w, y + h, c, y + h, r); x.arcTo(c, y + h, c, y, r);
  x.arcTo(c, y, c + w, y, r); x.closePath();
}

/* ---- the two projects -------------------------------------------------- */
const SCOPE = [
  ['Enabling Works', ['Demolition', 'Site Clearance', 'Decontamination', 'Bulk Earthworks', 'Temporary Works', 'Utility Diversions']],
  ['Civil Works', ['Detailed Earthworks', 'Site Drainage', 'Stormwater Management', 'Internal Roads/Pavements', 'Retaining Walls']],
  ['Structure', ['Substructure/Foundations', 'Superstructure', 'Post-Tensioning', 'Precast Elements', 'Structural Steel Frame', 'Mass Timber Structure']],
  ['Building Envelope', ['Facade System', 'Curtain Wall', 'Roofing System', 'Glazing/Windows', 'Waterproofing']],
  ['Building Services', ['Mechanical/HVAC', 'Electrical/Power', 'Hydraulic/Plumbing', 'Fire Services', 'Vertical Transport', 'BMS/Controls', 'Security Systems', 'ICT/Structured Cabling']],
  ['Internal Fitout', ['Partitions/Internal Walls', 'Ceilings', 'Flooring', 'Joinery/Cabinetry', 'Specialist Fitout (Lab/Kitchen)']],
  ['External Works', ['Landscaping', 'Car Parking', 'Signage/Wayfinding', 'External Lighting', 'Fencing/Gates']]
];
const SUBCLASS = ['House (Class 1a)', 'Apartments (Class 2)', 'Townhouses (Class 1a)', 'BTR (Build-to-Rent)',
  'Student Housing (PBSA)', 'Retirement Living / ILUs', 'Residential Aged Care (Class 9c)', 'Social/Affordable Housing', 'Other'];
const CLASSES = ['Residential', 'Commercial', 'Industrial', 'Institution', 'Mixed use', 'Infrastructure'];
const WORK = ['New build', 'Refurbishment', 'Extension / addition', 'Remediation / rectification', 'Advisory services'];
const CPLX = ['Contamination level', 'Access constraints', 'Operational constraints', 'Procurement route',
  'Stakeholder complexity', 'Environmental sensitivity', 'Bushfire exposure', 'Flood exposure'];

const PROJ = {
  auto: {
    addr: '74-76 Kitchener Parade, Bankstown NSW 2200',
    client: 'FULLERTON PROPERTY Pty Ltd', state: 'NSW',
    cls: 0, work: 0, sub: 1,
    scale: ['8', '5500', '33', '50-150 sqm/unit'],
    cplx: ['Nil/Clean Site', 'Unrestricted Access', 'Vacant/Unoccupied', 'Traditional (Lump Sum)',
      'Single Owner', 'Standard', 'Not Bushfire Prone', 'Not Flood Prone'],
    ticks: [[0, 1, 3, 4, 5], [0, 1, 2, 4], [0, 1, 3], [0, 2, 3, 4], [0, 1, 2, 3, 4, 6], [0, 1, 2, 3], [0, 1, 2, 3, 4]]
  },
  manual: {
    addr: '12 Warrigal Street, Wollongong NSW 2500',
    client: 'M. & S. Petrakis', state: 'NSW',
    cls: 0, work: 0, sub: 0,
    scale: ['2', '300', '1', '300 sqm'],
    cplx: ['Nil/Clean Site', 'Unrestricted Access', 'Vacant/Unoccupied', 'Traditional (Lump Sum)',
      'Single Owner', 'Standard', 'Bushfire Prone — BAL-12.5', 'Not Flood Prone'],
    ticks: [[1], [1, 2], [0, 1], [0, 2, 3, 4], [0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 3, 4]]
  }
};
const nTicks = (p) => p.ticks.reduce((a, g) => a + g.length, 0);

/* ---- content layout: absolute y in a 1120-wide column ------------------- */
const Y = {
  top: 0, row1L: 88, row1B: 112, clsL: 186, cls: 208, workL: 340, work: 362,
  card: 432, cardH: 548, scopeL: 1012, scopeN: 1044, grp: 1076
};
const GRP_H = 262, GRP_GAP = 20;
const grpY = (i) => Y.grp + Math.floor(i / 3) * (GRP_H + GRP_GAP);
const grpX = (i) => (i % 3) * (IW / 3 + 4);
const GRP_W = IW / 3 - 12;
const CONTENT_H = grpY(6) + GRP_H + 40;

export function makeProfileScreen(THREE) {
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const x = c.getContext('2d');
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;

  /* fill order: index → [y, phase-fraction]. Drives both reveal and scroll. */
  const ORDER = [];
  /* Each entry carries the column it sits in and how far the sheet may push in
     while it is the subject: the full-width rows stay near native scale so
     nothing runs off the face; the three-column card can go closer. */
  const CX = [190, 560, 930];
  const FULL = 1.0, CARD = 1.55;
  ORDER.push(['addr', Y.row1B, CX[1], FULL], ['client', Y.row1B, CX[1], FULL],
    ['state', Y.row1B, CX[1], FULL]);
  ORDER.push(['cls', Y.cls, CX[1], FULL], ['work', Y.work, CX[1], FULL],
    ['sub', Y.card + 40, CX[0], CARD]);
  for (let i = 0; i < 4; i++) ORDER.push(['scale' + i, Y.card + 92 + i * 108, CX[1], CARD]);
  for (let i = 0; i < 8; i++) ORDER.push(['cplx' + i, Y.card + 78 + i * 58, CX[2], CARD]);
  for (let i = 0; i < 7; i++) ORDER.push(['grp' + i, grpY(i), CX[1], 1.0]);
  const NF = ORDER.length;

  /* A triangular blur over the fill order, so the push-in and the sideways
     drift move continuously instead of stepping field to field. */
  function trackAt(idxF, field) {
    let sum = 0, wsum = 0;
    const lo = Math.max(0, Math.floor(idxF) - 3), hi = Math.min(NF - 1, Math.ceil(idxF) + 3);
    for (let i = lo; i <= hi; i++) {
      const w = Math.max(0, 1 - Math.abs(i - idxF) / 2.6);
      sum += ORDER[i][field] * w * w; wsum += w * w;
    }
    return wsum ? sum / wsum : ORDER[0][field];
  }

  function fieldP(t, t0, t1, i) {
    const step = (t1 - t0) / NF;
    return seg(t, t0 + i * step, t0 + i * step + step * 1.9);
  }

  /* ---- primitives ------------------------------------------------------ */
  function label(s, px, py) {
    x.fillStyle = MUTE; x.font = F(21, 500); x.textAlign = 'left';
    x.fillText(s, px, py);
  }
  function glow(px, py, w, h, p) {
    if (p <= 0 || p >= 1) return;
    const a = 1 - clamp((p - 0.55) / 0.45, 0, 1);
    x.fillStyle = `rgba(255,255,255,${0.14 * a})`;
    rr(x, px - 6, py - 6, w + 12, h + 12, 6); x.fill();
  }
  function box(px, py, w, h, val, p, active) {
    glow(px, py, w, h, p);
    x.fillStyle = 'rgba(255,255,255,0.06)'; rr(x, px, py, w, h, 4); x.fill();
    x.strokeStyle = active ? HOT : LINE; x.lineWidth = active ? 2 : 1.4;
    rr(x, px, py, w, h, 4); x.stroke();
    if (p > 0 && val) {
      const n = Math.round(val.length * clamp(p * 1.35, 0, 1));
      x.fillStyle = INK; x.font = F(21); x.textAlign = 'left';
      x.fillText(val.slice(0, n), px + 13, py + h / 2 + 8);
      if (p < 0.98 && n < val.length) {
        x.fillStyle = HOT;
        x.fillRect(px + 14 + x.measureText(val.slice(0, n)).width, py + 9, 2, h - 18);
      }
    }
  }
  function tile(px, py, w, h, s, on, p) {
    const a = on ? easeOut(p) : 0;
    if (on) glow(px, py, w, h, p);
    x.fillStyle = `rgba(255,255,255,${0.16 * a})`; rr(x, px, py, w, h, 4); x.fill();
    x.strokeStyle = a > 0.5 ? HOT : LINE; x.lineWidth = a > 0.5 ? 2 : 1.4;
    rr(x, px, py, w, h, 4); x.stroke();
    x.fillStyle = a > 0.5 ? INK : MUTE; x.font = F(23, a > 0.5 ? 500 : 400);
    x.textAlign = 'left'; x.fillText(s, px + 14, py + h / 2 + 8);
  }
  function radio(px, py, s, on, p) {
    const a = on ? easeOut(p) : 0;
    x.beginPath(); x.arc(px + 9, py, 9, 0, 7); x.strokeStyle = a > 0.5 ? HOT : LINE;
    x.lineWidth = 1.8; x.stroke();
    if (a > 0.5) { x.beginPath(); x.arc(px + 9, py, 4.6, 0, 7); x.fillStyle = HOT; x.fill(); }
    x.fillStyle = a > 0.5 ? INK : MUTE; x.font = F(21, a > 0.5 ? 500 : 400);
    x.textAlign = 'left'; x.fillText(s, px + 28, py + 7);
  }
  function check(px, py, s, on, p) {
    const a = on ? easeOut(p) : 0;
    rr(x, px, py - 9, 18, 18, 3);
    x.fillStyle = a > 0.5 ? 'rgba(255,255,255,0.20)' : 'rgba(255,255,255,0.05)'; x.fill();
    x.strokeStyle = a > 0.5 ? HOT : LINE; x.lineWidth = 1.5; x.stroke();
    if (a > 0.5) {
      x.strokeStyle = '#fff'; x.lineWidth = 2.4; x.lineCap = 'round'; x.beginPath();
      x.moveTo(px + 4.5, py); x.lineTo(px + 7.6, py + 4); x.lineTo(px + 13.6, py - 4.6);
      x.stroke(); x.lineCap = 'butt';
    }
    x.fillStyle = a > 0.5 ? INK : MUTE; x.font = F(20);
    x.textAlign = 'left'; x.fillText(s, px + 30, py + 6);
  }
  function select(px, py, w, val, p) {
    box(px, py, w, 40, p > 0 ? val : '', p > 0 ? 1 : 0, false);
    glow(px, py, w, 40, p);
    x.strokeStyle = MUTE; x.lineWidth = 1.6; x.beginPath();
    x.moveTo(px + w - 22, py + 17); x.lineTo(px + w - 16, py + 23); x.lineTo(px + w - 10, py + 17);
    x.stroke();
  }
  function flash(px, py, w, h, a) {
    if (a <= 0.002) return;
    x.fillStyle = `rgba(255,255,255,${0.20 * a})`; rr(x, px, py, w, h, 5); x.fill();
  }

  /* ---- the sheet ------------------------------------------------------- */
  function sheet(p, proj, t0, t1, t, scroll, cursor) {
    x.save();
    x.beginPath(); x.rect(PAD, PAD, IW, H - PAD * 2); x.clip();

    // fixed top bar
    x.fillStyle = INK; x.font = F(30, 400); x.textAlign = 'left';
    x.fillText('Project profile', PAD + 4, PAD + 42);
    x.strokeStyle = HOT; x.lineWidth = 1.6;
    rr(x, PAD + IW - 178, PAD + 12, 174, 40, 4); x.stroke();
    x.fillStyle = INK; x.font = F(21, 500); x.textAlign = 'center';
    x.fillText('Save profile', PAD + IW - 91, PAD + 39);
    x.strokeStyle = LINE; x.lineWidth = 1; x.beginPath();
    x.moveTo(PAD, PAD + 64.5); x.lineTo(PAD + IW, PAD + 64.5); x.stroke();

    x.save();
    x.beginPath(); x.rect(PAD, PAD + 64, IW, H - PAD * 2 - 64); x.clip();
    x.translate(PAD, PAD + 84 - scroll);

    const at = (i) => fieldP(t, t0, t1, i);
    const cw = IW / 3 - 14;

    // row 1
    label('Site address', 0, Y.row1L);
    box(0, Y.row1B, cw + 90, 44, proj.addr, at(0));
    label('Client / owners', cw + 110, Y.row1L);
    box(cw + 110, Y.row1B, cw + 20, 44, proj.client, at(1));
    label('State', cw * 2 + 150, Y.row1L);
    select(cw * 2 + 150, Y.row1B + 2, cw - 70, proj.state, at(2));

    // class tiles
    label('Class', 0, Y.clsL);
    CLASSES.forEach((s, i) => {
      const px = (i % 3) * (IW / 3), py = Y.cls + Math.floor(i / 3) * 58;
      tile(px, py, IW / 3 - 14, 48, s, i === proj.cls, at(3));
    });

    // work type
    label('Work type', 0, Y.workL);
    let wx = 0;
    WORK.forEach((s, i) => {
      x.font = F(23, 500);
      const tw = x.measureText(s).width + 34;
      tile(wx, Y.work, tw, 48, s, i === proj.work, at(4));
      wx += tw + 12;
    });

    // three-column card
    x.strokeStyle = LINE; x.lineWidth = 1;
    for (let i = 0; i < 3; i++) { rr(x, i * (IW / 3 + 4), Y.card, GRP_W + 4, Y.cardH, 5); x.stroke(); }

    label('Subclass', 22, Y.card + 30);
    SUBCLASS.forEach((s, i) => radio(22, Y.card + 66 + i * 34, s, i === proj.sub, at(5)));

    const sx = IW / 3 + 26;
    label('Scale', sx, Y.card + 30);
    ['Storeys', 'GFA sqm', 'Units', 'Average unit size sqm'].forEach((s, i) => {
      label(s, sx, Y.card + 76 + i * 108);
      box(sx, Y.card + 92 + i * 108, GRP_W - 40, 42, proj.scale[i], at(6 + i));
    });

    const px2 = (IW / 3) * 2 + 30;
    label('Complexity', px2, Y.card + 30);
    CPLX.forEach((s, i) => {
      label(s, px2, Y.card + 68 + i * 58);
      select(px2, Y.card + 78 + i * 58, GRP_W - 46, proj.cplx[i], at(10 + i));
    });

    // fallback scope
    const done = ORDER.slice(18).reduce((a, _, i) => a + (at(18 + i) > 0.5 ? proj.ticks[i].length : 0), 0);
    x.fillStyle = INK; x.font = F(23, 500); x.textAlign = 'left';
    x.fillText(`▾ Fallback scope inputs (${done} selected)`, 0, Y.scopeL);
    x.fillStyle = MUTE; x.font = F(19);
    x.fillText('Used only where project documents do not establish the physical scope.', 0, Y.scopeN);

    SCOPE.forEach(([name, items], i) => {
      const gx = grpX(i), gy = grpY(i), p = at(18 + i);
      x.strokeStyle = LINE; x.lineWidth = 1; rr(x, gx, gy, GRP_W, GRP_H, 5); x.stroke();
      x.fillStyle = INK; x.font = F(21, 500); x.fillText(name, gx + 14, gy + 30);
      items.forEach((s, j) => {
        const on = proj.ticks[i].indexOf(j) >= 0;
        const jp = clamp((p - j * 0.055) * 4, 0, 1);
        check(gx + 14, gy + 62 + j * 29, s, on, jp);
      });
    });
    x.restore();
    x.restore();

    if (cursor) drawCursor(cursor);
  }

  function drawCursor(c2) {
    const s = c2.s || 1;
    x.save();
    x.translate(c2.x, c2.y); x.scale(s, s); x.translate(-c2.x, -c2.y);
    if (c2.click > 0) {
      x.strokeStyle = `rgba(255,255,255,${1 - c2.click})`; x.lineWidth = 2.5;
      x.beginPath(); x.arc(c2.x, c2.y, 8 + c2.click * 26, 0, 7); x.stroke();
    }
    x.fillStyle = '#FFFFFF'; x.strokeStyle = 'rgba(10,30,60,0.85)'; x.lineWidth = 1.6;
    x.beginPath(); x.moveTo(c2.x, c2.y); x.lineTo(c2.x, c2.y + 22);
    x.lineTo(c2.x + 5.5, c2.y + 16.5); x.lineTo(c2.x + 13, c2.y + 16);
    x.closePath(); x.fill(); x.stroke();
    x.restore();
  }

  /* ---- send, then the exchange ------------------------------------------
     The instruction is clicked into the agent on the mark, comes back as the
     user's own line, and the assistant says it is working while the profile is
     being built. */
  const CX0 = PAD - 20, CY0 = PAD + 400, CSC = (IW + 40) / 1120;
  const MARK = [CX0 + 1040 * CSC, CY0 + 134 * CSC];

  function bubble(s, a) {
    if (a <= 0.002) return;
    x.save(); x.globalAlpha = a;
    x.font = F(30, 300); x.textAlign = 'left';
    const maxw = IW * 0.72;
    const lines = [];
    let line = '';
    for (const w of s.split(' ')) {
      const test = line ? line + ' ' + w : w;
      if (x.measureText(test).width > maxw && line) { lines.push(line); line = w; }
      else line = test;
    }
    lines.push(line);
    const lh = 42;
    const bw = Math.max.apply(null, lines.map((l) => x.measureText(l).width)) + 56;
    const bh = lines.length * lh + 30;
    const bx = PAD + IW - bw, by = PAD + 110 + (1 - easeOut(a)) * 40;
    rr(x, bx, by, bw, bh, 16);
    x.fillStyle = 'rgba(255,255,255,0.15)'; x.fill();
    x.strokeStyle = LINE; x.lineWidth = 1.5; x.stroke();
    x.fillStyle = INK;
    lines.forEach((l, i) => x.fillText(l, bx + 28, by + 42 + i * lh));
    x.restore();
  }

  function working(a, t) {
    if (a <= 0.002) return;
    x.save();
    const px = PAD + 8, py = PAD + 430;
    x.globalAlpha = a;
    x.fillStyle = MUTE; x.font = F(32, 400); x.textAlign = 'left';
    x.fillText('Working', px, py);
    const w0 = x.measureText('Working').width;
    for (let i = 0; i < 3; i++) {
      const p = 0.5 + 0.5 * Math.sin(t * 4.4 - i * 0.95);
      x.globalAlpha = a * (0.2 + 0.8 * p);
      x.fillStyle = INK;
      x.beginPath(); x.arc(px + w0 + 24 + i * 24, py - 10, 5.5, 0, 7); x.fill();
    }
    x.restore();
  }

  /* ---- the prompt ------------------------------------------------------
     No card and no field furniture: the instruction is typed straight onto
     the glazing, holds while the caret blinks, then swipes up and off. */
  function prompt(text, p, typed, blink, out, t) {
    const rise = easeInOut(out);
    const n = Math.round(text.length * typed);
    const on = typed < 1 ? true : (blink > 0 && Math.sin(t * 6.6) > -0.15);
    drawComposer(x, {
      x0: PAD - 20, y0: PAD + 400 + (1 - easeOut(p)) * 80 - rise * 360,
      w: IW + 40, theme: 'glass',
      text: text.slice(0, n),
      placeholder: 'Ask about your project documents',
      caret: on, depth: 1, hot: typed >= 1 ? 1 : 0, scroll: true,
      alpha: p * (1 - rise)
    });
  }

  function wrap(text, px, py, maxw, lh, maxLines) {
    const words = text.split(' ');
    let line = '', n = 0;
    for (const w of words) {
      const test = line ? line + ' ' + w : w;
      if (x.measureText(test).width > maxw && line) {
        x.fillText(line, px, py + n * lh); line = w; n++;
        if (maxLines && n >= maxLines) break;
      } else line = test;
    }
    if (!maxLines || n < maxLines) x.fillText(line, px, py + n * lh);
    return { line, n };
  }

  /* ---- the summary card ------------------------------------------------ */
  function summary(p, t) {
    const w = IW - 40, ph = 400;
    const py = PAD + 400 + (1 - easeOut(p)) * 60;
    x.save(); x.globalAlpha = p;
    x.strokeStyle = LINE; x.lineWidth = 1.4; rr(x, PAD + 20, py, w, ph, 6); x.stroke();
    x.fillStyle = HOT; x.fillRect(PAD + 20, py, 4, ph);

    let yy = py + 60;
    x.fillStyle = INK; x.font = F(32, 400); x.textAlign = 'left';
    x.fillText('Project Profile updated', PAD + 56, yy); yy += 50;
    x.fillStyle = MUTE; x.font = F(21);
    x.fillText('Evidence-backed fields written from the project documents:', PAD + 56, yy); yy += 50;

    const rows = [
      ['Site address', '74-76 Kitchener Parade, Bankstown NSW 2200'],
      ['Client', 'FULLERTON PROPERTY Pty Ltd'],
      ['Scale', '8 storeys and 33 units']
    ];
    rows.forEach((r, i) => {
      const a = seg(t, 0.4 + i * 0.35, 1.1 + i * 0.35);
      x.globalAlpha = p * a;
      x.fillStyle = MUTE; x.font = F(21);
      x.fillText(r[0] + ':', PAD + 56, yy);
      x.fillStyle = INK; x.font = F(21, 500);
      x.fillText(r[1], PAD + 56 + 152, yy);
      yy += 42;
    });
    x.globalAlpha = p * seg(t, 1.9, 2.6);
    yy += 24;
    x.strokeStyle = LINE; x.beginPath();
    x.moveTo(PAD + 56, yy - 18); x.lineTo(PAD + w - 4, yy - 18); x.stroke();
    x.fillStyle = MUTE; x.font = MONO(17);
    x.fillText('SOURCES', PAD + 56, yy + 18);
    x.font = F(19);
    x.fillText('Bankstown PPR October 2015 · BCA Assessment Report R0 ·', PAD + 56, yy + 52);
    x.fillText('hydraulic drawing title blocks', PAD + 56, yy + 78);
    x.restore();
  }

  /* ---- the act --------------------------------------------------------- */
  const Q1 = 'update the profile';
  const Q2 = 'create a new project, address 12 Warrigal Street, Wollongong, New South Wales, , 4 bed, 2 car, 300 sqm GFA, 2 stories, Bal 12.5.  Knockdown, rebuild. CDC, Lump sum.';

  // manual run: the cursor visits four controls, the rest fill behind it
  const CLICKS = [
    [0.10, 0.30, 'Residential'], [0.30, 0.46, 'New build'],
    [0.46, 0.62, 'House (Class 1a)'], [0.62, 0.78, 'Storeys']
  ];

  function draw(t) {
    x.clearRect(0, 0, W, H);

    /* prompt 1 → auto fill → summary → clear */
    /* instruction typed → caret blinks → swipes up → the sheet swipes in */
    const q1In = seg(t, 0.4, 1.3), q1Out = seg(t, 5.2, 6.1);
    const q2In = seg(t, 26.8, 27.6), q2Out = seg(t, 32.0, 32.9);

    const sheetIn = seg(t, 6.1, 7.1);
    const sheetOut = seg(t, 25.6, 26.4);
    const sheet2In = seg(t, 35.6, 36.6);
    const sp = seg(t, 22.8, 23.6) * (1 - seg(t, 25.4, 26.0));
    const sheetA = clamp(sheetIn - sheetOut + sheet2In, 0, 1) * (1 - 0.88 * sp);

    if (sheetA > 0.002) {
      const manual = t >= 32.0;
      const proj = manual ? PROJ.manual : PROJ.auto;
      const t0 = manual ? 38.0 : 7.4, t1 = manual ? 50.0 : 22.4;
      const slideY = manual
        ? (1 - easeOut(sheet2In)) * 300
        : (1 - easeOut(sheetIn)) * 300 - easeInOut(sheetOut) * 320;

      /* The camera never moves in this act: the sheet holds still and scrolls
         itself once the fields below the fold are the ones being filled. */

      /* No push-in at all: the sheet is held whole while the fields populate,
         then scrolls once — as the complexity column nears full — so the second
         half comes into view while the last selections are still landing. */
      const fp = clamp((t - t0) / (t1 - t0), 0, 1);
      const viewH = H - PAD * 2 - 84;
      const maxS = Math.max(0, CONTENT_H - viewH);
      const Z = 1;
      const scroll = maxS * easeInOut(seg(fp, 0.66, 0.94));
      const cxc = PAD + IW / 2;

      let cursor = null;
      if (manual) {
        const cp = clamp((t - t0) / (t1 - t0), 0, 1);
        for (const [a, b, name] of CLICKS) {
          if (cp >= a - 0.06 && cp <= b) {
            const k = seg(cp, a - 0.06, a + 0.02);
            const targets = {
              'Residential': [PAD + 120, PAD + 84 + Y.cls + 24 - scroll],
              'New build': [PAD + 80, PAD + 84 + Y.work + 24 - scroll],
              'House (Class 1a)': [PAD + 120, PAD + 84 + Y.card + 66 - scroll],
              'Storeys': [PAD + IW / 3 + 120, PAD + 84 + Y.card + 110 - scroll]
            };
            const [tx, ty] = targets[name];
            cursor = { x: lerp(tx - 180, tx, easeInOut(k)), y: lerp(ty + 120, ty, easeInOut(k)),
              click: clamp((cp - a) * 14, 0, 1) < 1 ? clamp((cp - a) * 14, 0, 1) : 0 };
          }
        }
      }

      x.save();
      x.globalAlpha = sheetA;
      x.translate(0, slideY);
      x.translate(W / 2, H / 2); x.scale(Z, Z); x.translate(-cxc, -H / 2);
      sheet(1, proj, t0, t1, t, scroll, cursor);
      x.restore();
    }

    if (t < 6.2) prompt(Q1, q1In, seg(t, 1.5, 3.4), seg(t, 3.4, 3.5), q1Out, t);
    if (t >= 26.6 && t < 33.0) prompt(Q2, q2In, seg(t, 27.6, 30.6), seg(t, 30.6, 30.7), q2Out, t);

    /* the send, then the exchange */
    const SEND = 31.9;
    const sIn = seg(t, 30.8, SEND), sOut = seg(t, SEND + 0.5, SEND + 0.9);
    if (sIn > 0 && sOut < 1) {
      const k = easeInOut(sIn);
      const ring = clamp((t - SEND) * 2.0, 0, 1);
      drawCursor({
        x: lerp(MARK[0] - 230, MARK[0], k),
        y: lerp(MARK[1] + 200, MARK[1], k),
        s: 2.8,
        click: ring < 1 ? ring : 0
      });
    }
    bubble(Q2, seg(t, 32.6, 33.4) * (1 - seg(t, 35.8, 36.6)));
    working(seg(t, 33.6, 34.2) * (1 - seg(t, 35.4, 36.0)), t);

    if (sp > 0.002) summary(sp, t - 22.8);

    tex.needsUpdate = true;
  }

  return { tex, draw, canvas: c };
}
