"""
Extract v e r i s letter crops from the reference PNG (pixel-exact).

Usage:
  python frontend/public/landing-assets/trace_veris.py

Outputs:
  veris-glyphs-raster.json  — base64 PNG clips + advances for VerisDisplay
  veris-traced.svg          — preview composing the five clips
  glyphs/v.png … glyphs/s.png
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

OUT_DIR = Path(__file__).resolve().parent
REFERENCE = OUT_DIR / "veris-reference.png"
GLYPH_DIR = OUT_DIR / "glyphs"
LETTERS = "veris"
GRID_CAP = 1000


def is_red(r: int, g: int, b: int, a: int) -> bool:
    return a > 128 and r > 150 and g < 120 and b < 120 and r > g + 40 and r > b + 40


def red_mask(img: Image.Image) -> list[list[bool]]:
    w, h = img.size
    px = img.load()
    return [[is_red(*px[x, y]) for x in range(w)] for y in range(h)]


def word_bbox(mask: list[list[bool]]) -> tuple[int, int, int, int]:
    h = len(mask)
    w = len(mask[0])
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    return min_x, min_y, max_x, max_y


def x_projection(mask: list[list[bool]]) -> list[int]:
    h = len(mask)
    w = len(mask[0])
    return [sum(mask[y][x] for y in range(h)) for x in range(w)]


def letter_slices(mask: list[list[bool]]) -> list[tuple[str, int, int]]:
    """Split on wide zero columns between ink clusters."""
    w = len(mask[0])
    proj = x_projection(mask)
    runs: list[tuple[int, int]] = []
    start = None
    for x, count in enumerate(proj):
        if count == 0 and start is None:
            start = x
        elif count > 0 and start is not None:
            if x - start >= 8:
                runs.append((start, x - 1))
            start = None
    if start is not None and w - start >= 8:
        runs.append((start, w - 1))

    if len(runs) != len(LETTERS) - 1:
        raise RuntimeError(f"Expected {len(LETTERS) - 1} gutters, found {len(runs)}: {runs}")

    # Ink spans sit between gutters.
    bounds: list[tuple[int, int]] = []
    prev_end = -1
    for gutter_start, gutter_end in runs:
        ink_start = prev_end + 1
        ink_end = gutter_start - 1
        bounds.append((ink_start, ink_end))
        prev_end = gutter_end
    bounds.append((prev_end + 1, w - 1))

    return list(zip(LETTERS, [b[0] for b in bounds], [b[1] for b in bounds], strict=True))


def letter_bbox(mask: list[list[bool]], x0: int, x1: int) -> tuple[int, int, int, int]:
    h = len(mask)
    min_x, min_y, max_x, max_y = x1 + 1, h, -1, -1
    for y in range(h):
        for x in range(x0, x1 + 1):
            if mask[y][x]:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    return min_x, min_y, max_x, max_y


def png_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def main() -> None:
    if not REFERENCE.exists():
        raise SystemExit(f"Missing reference: {REFERENCE}")

    src = Image.open(REFERENCE).convert("RGBA")
    mask = red_mask(src)
    wx0, wy0, wx1, wy1 = word_bbox(mask)
    word_mask = [row[wx0 : wx1 + 1] for row in mask[wy0 : wy1 + 1]]
    word_img = src.crop((wx0, wy0, wx1 + 1, wy1 + 1))

    slices = letter_slices(word_mask)
    word_h = wy1 - wy0 + 1
    scale = GRID_CAP / word_h

    GLYPH_DIR.mkdir(exist_ok=True)
    glyphs: dict[str, dict] = {}
    svg_images: list[str] = []
    x_cursor = 0.0

    for ch, x0, x1 in slices:
        lx0, ly0, lx1, ly1 = letter_bbox(word_mask, x0, x1)
        clip = word_img.crop((lx0, ly0, lx1 + 1, ly1 + 1))
        clip_w, clip_h = clip.size

        # Trim to red pixels only (transparent elsewhere).
        clip_px = clip.load()
        trimmed = Image.new("RGBA", (clip_w, clip_h), (0, 0, 0, 0))
        tpx = trimmed.load()
        for y in range(clip_h):
            for x in range(clip_w):
                r, g, b, a = clip_px[x, y]
                if is_red(r, g, b, a):
                    tpx[x, y] = (r, g, b, a)

        png_path = GLYPH_DIR / f"{ch}.png"
        trimmed.save(png_path)

        # Advance = full slice width in word (preserves inter-letter spacing from reference).
        adv_px = x1 - x0 + 1
        adv = round(adv_px * scale, 2)
        offset_x = round((lx0 - x0) * scale, 2)
        offset_y = round(ly0 * scale, 2)
        draw_w = round(clip_w * scale, 2)
        draw_h = round(clip_h * scale, 2)

        href = png_data_url(trimmed)
        glyphs[ch] = {
            "width": adv,
            "height": draw_h,
            "offsetX": offset_x,
            "offsetY": offset_y,
            "drawWidth": draw_w,
            "drawHeight": draw_h,
            "href": href,
        }

        svg_images.append(
            f'<image x="{x_cursor + offset_x}" y="{offset_y}" '
            f'width="{draw_w}" height="{draw_h}" href="{href}"/>'
        )
        x_cursor += adv

    total_w = round(x_cursor, 2)
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {GRID_CAP}">\n'
        + "\n".join(svg_images)
        + "\n</svg>\n"
    )
    (OUT_DIR / "veris-traced.svg").write_text(svg, encoding="utf-8")

    payload = {
        "meta": {"cap": GRID_CAP, "source": REFERENCE.name, "mode": "raster"},
        "glyphs": {ch: {k: v for k, v in g.items() if k != "href"} for ch, g in glyphs.items()},
    }
    (OUT_DIR / "veris-glyphs.meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Full payload with embedded PNGs for AI export pipelines.
    payload["glyphs"] = glyphs
    (OUT_DIR / "veris-glyphs-raster.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    data_js = (
        "/* Auto-generated by trace_veris.py — do not edit by hand. */\n"
        "(function (root) {\n"
        '  "use strict";\n'
        f"  root.VerisGlyphData = {json.dumps(payload['glyphs'], indent=2)};\n"
        f"  root.VerisGlyphMeta = {json.dumps(payload['meta'], indent=2)};\n"
        "})(typeof window !== 'undefined' ? window : globalThis);\n"
    )
    (OUT_DIR / "veris-glyphs.data.js").write_text(data_js, encoding="utf-8")

    print(f"Extracted {len(glyphs)} raster glyphs -> {GLYPH_DIR}")
    for ch in LETTERS:
        g = glyphs[ch]
        print(f"  {ch}: adv={g['width']} draw={g['drawWidth']}x{g['drawHeight']}")

    # Keep derived glyphs in data.js (a l n o t) when derive script exists.
    derive_script = OUT_DIR / "derive_veris-glyphs.py"
    if derive_script.exists():
        import subprocess
        import sys

        print("Running derive_veris-glyphs.py …")
        subprocess.run([sys.executable, str(derive_script)], check=True)


if __name__ == "__main__":
    main()
