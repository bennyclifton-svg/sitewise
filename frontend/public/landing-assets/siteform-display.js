/*
 * SITEFORM DISPLAY — custom display face, build path A (SVG glyph library).
 * From docs/plans/landing/landingprg.md, Prompt 1.5.
 *
 * GLYPH DNA
 *   - 1000-unit grid, cap height 1000, no descenders.
 *   - Monolinear stroke ~210 units; ultra-wide (advance ~1.1-1.3x cap).
 *   - Outer corners near-square with slight rounding (~50 units).
 *   - Counters are deep rounded slots (radius ~92-250 units).
 *   - Stencil/LED breaks (~80 unit gaps) at select junctions:
 *     B reads almost as "З" (left side open), A almost as "Λ" (low hairline
 *     crossbar, gapped), M/W centre vertices stop well short of base/cap.
 *
 * Geometry is composed from filled primitives on a single <path> per glyph:
 * positive shapes wind clockwise, counters wind counter-clockwise (nonzero
 * fill rule punches the holes). Counters that "open" an edge are drawn flush
 * to that edge — a counter must never extend past positive coverage, or the
 * nonzero rule would fill it.
 *
 * Build path B (FontForge -> SiteformDisplay.woff2) is a deferred upgrade;
 * these same paths are the source geometry for it.
 */
(function (root) {
  "use strict";

  var CAP = 1000;      // cap height / design grid
  var STROKE = 210;    // monolinear stroke weight
  var TRACK = 70;      // default inter-glyph tracking (design units)
  var SPACE_ADV = 480; // word-space advance

  function f(n) {
    return String(Math.round(n * 10) / 10);
  }

  /* Rounded rectangle. r: number or [tl, tr, br, bl]. hole=true reverses
   * winding so it subtracts from positives underneath it. */
  function rr(x, y, w, h, r, hole) {
    var radii = Array.isArray(r) ? r.slice() : [r, r, r, r];
    for (var i = 0; i < 4; i++) {
      radii[i] = Math.max(0, Math.min(radii[i], w / 2, h / 2));
    }
    var tl = radii[0], tr = radii[1], br = radii[2], bl = radii[3];
    if (!hole) {
      return "M" + f(x + tl) + " " + f(y) +
        "H" + f(x + w - tr) +
        (tr ? "A" + f(tr) + " " + f(tr) + " 0 0 1 " + f(x + w) + " " + f(y + tr) : "") +
        "V" + f(y + h - br) +
        (br ? "A" + f(br) + " " + f(br) + " 0 0 1 " + f(x + w - br) + " " + f(y + h) : "") +
        "H" + f(x + bl) +
        (bl ? "A" + f(bl) + " " + f(bl) + " 0 0 1 " + f(x) + " " + f(y + h - bl) : "") +
        "V" + f(y + tl) +
        (tl ? "A" + f(tl) + " " + f(tl) + " 0 0 1 " + f(x + tl) + " " + f(y) : "") +
        "Z";
    }
    return "M" + f(x + tl) + " " + f(y) +
      (tl ? "A" + f(tl) + " " + f(tl) + " 0 0 0 " + f(x) + " " + f(y + tl) : "") +
      "V" + f(y + h - bl) +
      (bl ? "A" + f(bl) + " " + f(bl) + " 0 0 0 " + f(x + bl) + " " + f(y + h) : "") +
      "H" + f(x + w - br) +
      (br ? "A" + f(br) + " " + f(br) + " 0 0 0 " + f(x + w) + " " + f(y + h - br) : "") +
      "V" + f(y + tr) +
      (tr ? "A" + f(tr) + " " + f(tr) + " 0 0 0 " + f(x + w - tr) + " " + f(y) : "") +
      "Z";
  }

  /* Signed area via shoelace; > 0 means clockwise on screen (y grows down). */
  function signedArea(p) {
    var a = 0;
    for (var i = 0; i < p.length; i++) {
      var j = (i + 1) % p.length;
      a += p[i][0] * p[j][1] - p[j][0] * p[i][1];
    }
    return a;
  }

  /* Polygon with per-vertex corner rounding (quadratic corner cuts).
   * Winding is normalised: positives clockwise, holes counter-clockwise,
   * whatever order the points arrive in — otherwise a stray CCW positive
   * would punch holes out of anything it overlaps (nonzero fill rule). */
  function poly(pts, r, hole) {
    var p = pts.slice(), radii = Array.isArray(r) ? r.slice() : pts.map(function () { return r; });
    var clockwise = signedArea(p) > 0;
    if (clockwise === !!hole) {
      p.reverse();
      radii.reverse();
    }
    var n = p.length, d = "";
    for (var i = 0; i < n; i++) {
      var prev = p[(i + n - 1) % n], cur = p[i], nxt = p[(i + 1) % n];
      var v1x = cur[0] - prev[0], v1y = cur[1] - prev[1];
      var v2x = nxt[0] - cur[0], v2y = nxt[1] - cur[1];
      var l1 = Math.hypot(v1x, v1y), l2 = Math.hypot(v2x, v2y);
      var ri = Math.min(radii[i], l1 / 2, l2 / 2);
      var ax = cur[0] - (v1x / l1) * ri, ay = cur[1] - (v1y / l1) * ri;
      var bx = cur[0] + (v2x / l2) * ri, by = cur[1] + (v2y / l2) * ri;
      d += (i === 0 ? "M" : "L") + f(ax) + " " + f(ay);
      d += "Q" + f(cur[0]) + " " + f(cur[1]) + " " + f(bx) + " " + f(by);
    }
    return d + "Z";
  }

  /* Slanted monolinear bar from (x1,y1) to (x2,y2), thickness t, cap radius r. */
  function beam(x1, y1, x2, y2, t, r) {
    var dx = x2 - x1, dy = y2 - y1, l = Math.hypot(dx, dy);
    var nx = (-dy / l) * (t / 2), ny = (dx / l) * (t / 2);
    return poly([
      [x1 + nx, y1 + ny],
      [x2 + nx, y2 + ny],
      [x2 - nx, y2 - ny],
      [x1 - nx, y1 - ny]
    ], r, false);
  }

  var GLYPHS = (function () {
    var R = 50;   // outer corner rounding — softened machine block
    var NR = 92;  // slot counter end radius (bar-gap slots are 185 tall)
    var CR = 250; // deep counter radius (O/U/D bowls)
    var box = function (x, y, w, h, r) { return rr(x, y, w, h, r, false); };
    var cut = function (x, y, w, h, r) { return rr(x, y, w, h, r, true); };
    var P = function (w) {
      return { w: w, d: Array.prototype.slice.call(arguments, 1).join("") };
    };
    var g = {};

    /* Bar grid shared by most glyphs: top bar y 0-210, middle bar y 395-605,
     * bottom bar y 790-1000; inter-bar slots are 185 units tall. */

    // Λ silhouette; low hairline crossbar floats with stencil gaps.
    g.A = P(1100,
      poly([[390, 0], [710, 0], [1100, 1000], [860, 1000], [550, 205], [240, 1000], [0, 1000]],
        [R, R, R, R, 120, R, R], false),
      box(410, 760, 280, 70, 35));

    // Left side open — reads almost as "З": bars carried by the right stem
    // only, with a stencil slit in the stem at the waist.
    g.B = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(0, 210, 890, 185, [0, NR, NR, 0]),
      cut(0, 605, 890, 185, [0, NR, NR, 0]),
      cut(890, 460, 210, 80, [35, 0, 0, 35]));

    g.C = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 210, 890, 580, [CR, 0, 0, CR]));

    // Left stem + bowl, machine-cut apart at the bar junctions.
    g.D = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 210, 680, 580, [90, CR, CR, 90]),
      cut(300, 0, 80, 210, 0),
      cut(300, 790, 80, 210, 0));

    g.E = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 210, 890, 185, [NR, 0, 0, NR]),
      cut(210, 605, 890, 185, [NR, 0, 0, NR]),
      cut(210, 395, 80, 210, 0));

    g.F = P(1100,
      box(0, 0, 210, 1000, R),
      box(0, 0, 1100, 210, R),
      box(290, 395, 660, 210, 105));

    g.G = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 210, 680, 580, 230),
      cut(890, 210, 210, 220, 0),
      box(550, 395, 550, 210, [105, 0, 0, 105]));

    // Floating LED-style crossbar.
    g.H = P(1100,
      box(0, 0, 210, 1000, R),
      box(890, 0, 210, 1000, R),
      box(290, 395, 520, 210, 105));

    g.I = P(320, box(55, 0, 210, 1000, R));

    g.J = P(1100,
      box(890, 0, 210, 1000, R),
      box(0, 790, 1100, 210, [105, 0, 0, 105]));

    g.K = P(1100,
      box(0, 0, 210, 1000, R),
      beam(290, 520, 1030, 110, 240, 60),
      beam(290, 480, 1030, 890, 240, 60));

    g.L = P(1100,
      box(0, 0, 210, 1000, R),
      box(0, 790, 1050, 210, [0, 105, 105, 0]));

    // Centre vertex stops well short of the baseline.
    g.M = P(1300,
      box(0, 0, 210, 1000, R),
      box(1090, 0, 210, 1000, R),
      beam(270, 70, 650, 560, 230, 60),
      beam(1030, 70, 650, 560, 230, 60));

    g.N = P(1100,
      box(0, 0, 210, 1000, R),
      box(890, 0, 210, 1000, R),
      beam(105, 150, 995, 850, 240, 60));

    g.O = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 210, 680, 580, CR));

    g.P = P(1100,
      box(0, 0, 210, 1000, R),
      box(0, 0, 1100, 605, R),
      cut(210, 210, 680, 185, NR),
      cut(300, 395, 80, 210, 0));

    g.Q = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 210, 680, 580, CR),
      beam(720, 680, 990, 915, 220, 50));

    g.R = P(1100,
      box(0, 0, 210, 1000, R),
      box(0, 0, 1100, 605, R),
      cut(210, 210, 680, 185, NR),
      beam(480, 605, 980, 895, 240, 55));

    // Block with two opposing deep slots.
    g.S = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 210, 890, 185, [NR, 0, 0, NR]),
      cut(0, 605, 890, 185, [0, NR, NR, 0]));

    // Stem floats free of the top bar (stencil gap).
    g.T = P(1100,
      box(0, 0, 1100, 210, R),
      box(445, 290, 210, 710, R));

    g.U = P(1100,
      box(0, 0, 1100, 1000, R),
      cut(210, 0, 680, 790, [0, 0, CR, CR]));

    g.V = P(1100,
      poly([[0, 0], [240, 0], [550, 738], [860, 0], [1100, 0], [680, 1000], [420, 1000]],
        [R, R, 120, R, R, 60, 60], false));

    // Centre vertex stops well short of the cap line.
    g.W = P(1300,
      box(0, 0, 210, 1000, R),
      box(1090, 0, 210, 1000, R),
      beam(270, 930, 650, 440, 230, 60),
      beam(1030, 930, 650, 440, 230, 60));

    g.X = P(1100,
      beam(90, 105, 1010, 895, 240, 60),
      beam(1010, 105, 90, 895, 240, 60));

    // Tail gapped from the fork junction.
    g.Y = P(1100,
      beam(60, 95, 550, 470, 230, 60),
      beam(1040, 95, 550, 470, 230, 60),
      box(445, 640, 210, 360, R));

    g.Z = P(1100,
      box(0, 0, 1100, 210, R),
      box(0, 790, 1100, 210, R),
      beam(900, 300, 200, 700, 250, 60));

    g["0"] = P(1000,
      box(0, 0, 1000, 1000, R),
      cut(210, 210, 580, 580, CR));

    g["1"] = P(460,
      box(250, 0, 210, 1000, R),
      beam(60, 230, 255, 75, 170, 40));

    g["2"] = P(1000,
      box(0, 0, 1000, 1000, R),
      cut(0, 210, 790, 185, [0, NR, NR, 0]),
      cut(210, 605, 790, 185, [NR, 0, 0, NR]));

    // B-form with the middle bar trimmed back from the left edge.
    g["3"] = P(1000,
      box(0, 0, 1000, 1000, R),
      cut(0, 210, 790, 185, [0, NR, NR, 0]),
      cut(0, 605, 790, 185, [0, NR, NR, 0]),
      cut(0, 395, 260, 210, [0, 105, 105, 0]));

    g["4"] = P(1000,
      box(0, 0, 210, 605, R),
      box(0, 395, 1000, 210, [50, 0, 0, 50]),
      box(790, 0, 210, 1000, R));

    // Same topology as S; sharper slot ends + digit width tell them apart.
    g["5"] = P(1000,
      box(0, 0, 1000, 1000, R),
      cut(210, 210, 790, 185, [60, 0, 0, 60]),
      cut(0, 605, 790, 185, [0, 60, 60, 0]));

    g["6"] = P(1000,
      box(0, 0, 1000, 1000, R),
      cut(210, 210, 790, 185, [NR, 0, 0, NR]),
      cut(210, 605, 580, 185, NR));

    g["7"] = P(1000,
      box(0, 0, 1000, 210, R),
      beam(840, 280, 420, 920, 250, 60));

    g["8"] = P(1000,
      box(0, 0, 1000, 1000, R),
      cut(210, 210, 580, 185, NR),
      cut(210, 605, 580, 185, NR));

    g["9"] = P(1000,
      box(0, 0, 1000, 1000, R),
      cut(210, 210, 580, 185, NR),
      cut(0, 605, 790, 185, [0, NR, NR, 0]));

    g["-"] = P(640, box(30, 395, 580, 210, 105));

    // Stylised stencil ampersand: open top-right, two counters, diagonal leg.
    g["&"] = P(1150,
      box(0, 0, 1150, 1000, R),
      cut(720, 0, 430, 395, [0, 0, 0, 120]),
      cut(210, 210, 510, 185, NR),
      cut(210, 605, 730, 185, NR),
      beam(700, 500, 1060, 910, 230, 60));

    return g;
  })();

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Renders text as one inline SVG of SITEFORM DISPLAY glyph runs.
   * The real text is mirrored in a visually-hidden element for a11y/SEO.
   * Size via CSS: the emitted svg is height:1em-friendly (see page CSS). */
  function renderDisplayText(el, text, opts) {
    opts = opts || {};
    var tracking = typeof opts.tracking === "number" ? opts.tracking : TRACK;
    var chars = String(text).toUpperCase().split("");
    var x = 0;
    var parts = [];
    for (var i = 0; i < chars.length; i++) {
      var ch = chars[i];
      if (ch === " ") { x += SPACE_ADV; continue; }
      var glyph = GLYPHS[ch];
      if (!glyph) { x += SPACE_ADV; continue; } // unsupported char -> gap
      parts.push('<path transform="translate(' + f(x) + ' 0)" d="' + glyph.d + '"/>');
      x += glyph.w + tracking;
    }
    var total = Math.max(x - tracking, 1);
    el.innerHTML =
      '<span class="sr-only">' + escapeHtml(text) + "</span>" +
      '<svg viewBox="0 0 ' + f(total) + " " + CAP + '" aria-hidden="true" focusable="false" ' +
      'preserveAspectRatio="xMinYMid meet"><g fill="currentColor">' + parts.join("") + "</g></svg>";
    return el;
  }

  /* Renders every [data-display-text] element under root (default: document).
   * Text comes from the attribute value, falling back to textContent. */
  function renderAll(scope) {
    if (typeof document === "undefined") return;
    var nodes = (scope || document).querySelectorAll("[data-display-text]");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var text = el.getAttribute("data-display-text") || el.textContent.trim();
      var trackingAttr = el.getAttribute("data-tracking");
      renderDisplayText(el, text, trackingAttr ? { tracking: Number(trackingAttr) } : {});
    }
  }

  function prefersReducedMotion() {
    return typeof matchMedia !== "undefined" &&
      matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  root.SiteformDisplay = {
    CAP: CAP,
    STROKE: STROKE,
    TRACK: TRACK,
    SPACE_ADV: SPACE_ADV,
    GLYPHS: GLYPHS,
    renderDisplayText: renderDisplayText,
    renderAll: renderAll,
    prefersReducedMotion: prefersReducedMotion
  };
})(typeof window !== "undefined" ? window : globalThis);
