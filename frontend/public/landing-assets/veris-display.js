/*
 * VERIS DISPLAY — pixel-exact raster glyphs (v e r i s only).
 *
 * Glyphs are PNG clips traced from veris-reference.png.
 * Re-extract after reference changes:
 *   python frontend/public/landing-assets/trace_veris.py
 *
 * Loads metrics from veris-glyphs.data.js (auto-generated).
 */
(function (root) {
  "use strict";

  var CAP = 1000;
  var TRACK = 0;
  var SPACE_ADV = 400;
  var GLYPH_DIR = "./glyphs/";

  function f(n) {
    return String(Math.round(n * 10) / 10);
  }

  function glyphMap() {
    var data = root.VerisGlyphData || {};
    var out = {};
    for (var ch in data) {
      if (!Object.prototype.hasOwnProperty.call(data, ch)) continue;
      var g = data[ch];
      out[ch] = {
        w: g.width,
        offsetX: g.offsetX,
        offsetY: g.offsetY,
        drawW: g.drawWidth,
        drawH: g.drawHeight,
        href: GLYPH_DIR + ch + ".png"
      };
    }
    return out;
  }

  function getGlyphs() {
    return glyphMap();
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  function measureText(text, opts) {
    opts = opts || {};
    var tracking = typeof opts.tracking === "number" ? opts.tracking : TRACK;
    var chars = String(text).split("");
    var x = 0;
    for (var i = 0; i < chars.length; i++) {
      var ch = chars[i];
      if (ch === " ") { x += SPACE_ADV; continue; }
      var glyph = getGlyphs()[ch];
      if (!glyph) { x += SPACE_ADV; continue; }
      x += glyph.w + tracking;
    }
    return Math.max(x - tracking, 1);
  }

  function renderDisplayText(el, text, opts) {
    opts = opts || {};
    var tracking = typeof opts.tracking === "number" ? opts.tracking : TRACK;
    var glyphs = getGlyphs();
    var chars = String(text).split("");
    var x = 0;
    var parts = [];
    for (var i = 0; i < chars.length; i++) {
      var ch = chars[i];
      if (ch === " ") { x += SPACE_ADV; continue; }
      var glyph = glyphs[ch];
      if (!glyph) { x += SPACE_ADV; continue; }
      parts.push(
        '<image x="' + f(x + glyph.offsetX) + '" y="' + f(glyph.offsetY) + '" ' +
        'width="' + f(glyph.drawW) + '" height="' + f(glyph.drawH) + '" ' +
        'href="' + escapeHtml(glyph.href) + '"/>'
      );
      x += glyph.w + tracking;
    }
    var total = Math.max(x - tracking, 1);
    el.innerHTML =
      '<span class="sr-only">' + escapeHtml(text) + "</span>" +
      '<svg viewBox="0 0 ' + f(total) + " " + CAP + '" aria-hidden="true" focusable="false" ' +
      'preserveAspectRatio="xMinYMid meet">' + parts.join("") + "</svg>";
    return el;
  }

  function renderAll(scope) {
    if (typeof document === "undefined") return;
    var nodes = (scope || document).querySelectorAll("[data-veris-text]");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var text = el.getAttribute("data-veris-text") || el.textContent.trim();
      var trackingAttr = el.getAttribute("data-tracking");
      renderDisplayText(el, text, trackingAttr ? { tracking: Number(trackingAttr) } : {});
    }
  }

  function exportJson() {
    return {
      meta: root.VerisGlyphMeta || { cap: CAP, mode: "raster" },
      glyphs: root.VerisGlyphData || {}
    };
  }

  function toSvgString(text, opts) {
    opts = opts || {};
    var tracking = typeof opts.tracking === "number" ? opts.tracking : TRACK;
    var glyphs = getGlyphs();
    var chars = String(text).split("");
    var x = 0;
    var parts = [];
    for (var i = 0; i < chars.length; i++) {
      var ch = chars[i];
      if (ch === " ") { x += SPACE_ADV; continue; }
      var glyph = glyphs[ch];
      if (!glyph) { x += SPACE_ADV; continue; }
      parts.push(
        '<image x="' + f(x + glyph.offsetX) + '" y="' + f(glyph.offsetY) + '" ' +
        'width="' + f(glyph.drawW) + '" height="' + f(glyph.drawH) + '" ' +
        'href="' + glyph.href + '"/>'
      );
      x += glyph.w + tracking;
    }
    var total = Math.max(x - tracking, 1);
    return '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" ' +
      'viewBox="0 0 ' + f(total) + " " + CAP + '">' + parts.join("") + "</svg>";
  }

  root.VerisDisplay = {
    CAP: CAP,
    TRACK: TRACK,
    SPACE_ADV: SPACE_ADV,
    getGlyphs: getGlyphs,
    GLYPHS: getGlyphs(),
    measureText: measureText,
    renderDisplayText: renderDisplayText,
    renderAll: renderAll,
    exportJson: exportJson,
    toSvgString: toSvgString
  };
})(typeof window !== "undefined" ? window : globalThis);
