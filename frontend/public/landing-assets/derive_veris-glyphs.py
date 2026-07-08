"""
Derive a l n o t from traced v e r i s glyph clips.

Run after trace_veris.py (or standalone if traced glyphs exist):
  python frontend/public/landing-assets/derive_veris-glyphs.py

Merges traced + derived glyphs into veris-glyphs.data.js
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent
GLYPH_DIR = OUT_DIR / "glyphs"
GRID_CAP = 1000
WORD_H_PX = 376  # reference word crop height
SCALE = GRID_CAP / WORD_H_PX
DERIVED = "alnot"
RED = (229, 69, 69, 255)


def is_red(r: int, g: int, b: int, a: int) -> bool:
    return a > 128 and r > 150 and g < 120 and b < 120 and r > g + 40 and r > b + 40


def load(ch: str) -> Image.Image:
    return Image.open(GLYPH_DIR / f"{ch}.png").convert("RGBA")


def red_only(img: Image.Image) -> Image.Image:
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    src = img.load()
    dst = out.load()
    for y in range(img.height):
        for x in range(img.width):
            px = src[x, y]
            if is_red(*px):
                dst[x, y] = RED
    return out


def ink_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    px = img.load()
    w, h = img.size
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if is_red(*px[x, y]):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < 0:
        return None
    return min_x, min_y, max_x, max_y


def trim(img: Image.Image) -> Image.Image:
    box = ink_bbox(img)
    if not box:
        return img
    x0, y0, x1, y1 = box
    return img.crop((x0, y0, x1 + 1, y1 + 1))


def paste_red(dst: Image.Image, src: Image.Image, xy: tuple[int, int]) -> None:
    dpx = dst.load()
    spx = src.load()
    ox, oy = xy
    for y in range(src.height):
        for x in range(src.width):
            if is_red(*spx[x, y]):
                dx, dy = ox + x, oy + y
                if 0 <= dx < dst.width and 0 <= dy < dst.height:
                    dpx[dx, dy] = RED


def stem_rows(img: Image.Image) -> tuple[int, int]:
    """Narrow stem rows below the i dot (skips dot and transition bands)."""
    px = img.load()
    w, h = img.size
    gap_end = 0
    seen_ink = False
    in_gap = False
    for y in range(h):
        has_ink = any(is_red(*px[x, y]) for x in range(w))
        if has_ink:
            seen_ink = True
        if seen_ink and not has_ink:
            in_gap = True
        if in_gap and has_ink:
            gap_end = y
            break

    y0 = None
    y1 = gap_end
    for y in range(gap_end, h):
        xs = [x for x in range(w) if is_red(*px[x, y])]
        if not xs:
            continue
        span = xs[-1] - xs[0] + 1
        if 68 <= span <= 78 and xs[0] >= 14:
            if y0 is None:
                y0 = y
            y1 = y
    if y0 is None:
        return gap_end, h
    return y0, y1 + 1


def derive_l(i: Image.Image) -> Image.Image:
    y0, y1 = stem_rows(i)
    return trim(i.crop((0, y0, i.width, y1)))


def derive_o(e: Image.Image) -> Image.Image:
    out = red_only(e)
    px = out.load()
    w, h = out.size
    # Close the e mouth on the lower-right with the same stroke weight as the bowl.
    for y in range(int(h * 0.55), h):
        xs = [x for x in range(w) if is_red(*px[x, y])]
        if not xs:
            continue
        right = max(xs)
        for x in range(right + 1, w):
            px[x, y] = RED
    # Vertical terminal on the right, flat like e reference.
    xs = [x for x in range(w) if is_red(*px[x, h - 1])]
    if xs:
        right = max(xs)
        for y in range(int(h * 0.45), h):
            px[right, y] = RED
    return trim(out)


def derive_t(i: Image.Image, e: Image.Image) -> Image.Image:
    y0, y1 = stem_rows(i)
    stem = trim(i.crop((0, y0, i.width, y1)))
    sw, sh = stem.size

    bar_y0, bar_y1 = 134, 166
    bar = trim(e.crop((0, bar_y0, 96, bar_y1)))
    bar_canvas = Image.new("RGBA", (sw, bar.height), (0, 0, 0, 0))
    paste_red(bar_canvas, bar, (0, 0))

    out = Image.new("RGBA", (sw, bar_canvas.height + sh), (0, 0, 0, 0))
    paste_red(out, bar_canvas, (0, 0))
    paste_red(out, stem, (0, bar_canvas.height))
    return trim(out)


def derive_n(r: Image.Image) -> Image.Image:
    r = red_only(r)
    stem_w = 74
    gap = 34
    w = r.width + gap + stem_w
    h = r.height
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Left stem + shoulder from r.
    paste_red(out, r.crop((0, 0, r.width, h)), (0, 0))

    # Right stem (same width as r stem).
    stem = r.crop((0, int(h * 0.15), stem_w, h))
    paste_red(out, stem, (w - stem_w, 0))

    # Bridge the shoulder across the gap using r's top profile, stretched.
    rpx = r.load()
    opx = out.load()
    for y in range(int(h * 0.22)):
        xs = [x for x in range(r.width) if is_red(*rpx[x, y])]
        if not xs:
            continue
        left, right = min(xs), max(xs)
        span = right - left
        if span < 12:
            continue
        target_right = w - stem_w + 6
        for x in range(left, target_right + 1):
            t = (x - left) / max(target_right - left, 1)
            sx = int(left + t * span)
            if is_red(*rpx[sx, y]):
                opx[x, y] = RED
    return trim(out)


def derive_a(e: Image.Image, r: Image.Image) -> Image.Image:
    e = red_only(e)
    stem_w = 74
    w = e.width + stem_w - 18
    h = e.height
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    paste_red(out, e, (0, 0))

    stem = r.crop((0, 0, stem_w, r.height))
    paste_red(out, stem, (w - stem_w, 0))

    # Open the bowl top-right (a counter) while keeping the e eye.
    opx = out.load()
    cut_x0 = w - stem_w - 8
    for y in range(int(h * 0.08), int(h * 0.42)):
        for x in range(cut_x0, w - stem_w + 4):
            opx[x, y] = (0, 0, 0, 0)
    return trim(out)


def glyph_record(img: Image.Image, adv_px: float | None = None) -> dict[str, float]:
    w, h = img.size
    adv = adv_px if adv_px is not None else w
    box = ink_bbox(img)
    if not box:
        return {
            "width": round(adv * SCALE, 2),
            "height": round(h * SCALE, 2),
            "offsetX": 0.0,
            "offsetY": 0.0,
            "drawWidth": round(w * SCALE, 2),
            "drawHeight": round(h * SCALE, 2),
        }
    _, y0, _, y1 = box
    # Ink bottom sits on baseline (GRID_CAP).
    ink_bottom = (y1 + 1) * SCALE
    offset_y = round(GRID_CAP - ink_bottom, 2)
    return {
        "width": round(adv * SCALE, 2),
        "height": round(h * SCALE, 2),
        "offsetX": 0.0,
        "offsetY": offset_y,
        "drawWidth": round(w * SCALE, 2),
        "drawHeight": round(h * SCALE, 2),
    }


def main() -> None:
    for ch in "veris":
        if not (GLYPH_DIR / f"{ch}.png").exists():
            raise SystemExit("Run trace_veris.py first.")

    v, e, r, i, s = load("v"), load("e"), load("r"), load("i"), load("s")

    derived_imgs = {
        "l": derive_l(i),
        "o": derive_o(e),
        "t": derive_t(i, e),
        "n": derive_n(r),
        "a": derive_a(e, r),
    }

    for ch, img in derived_imgs.items():
        img.save(GLYPH_DIR / f"{ch}.png")

    # Load traced meta for veris letters.
    meta_path = OUT_DIR / "veris-glyphs.meta.json"
    if meta_path.exists():
        traced = json.loads(meta_path.read_text(encoding="utf-8"))
        glyphs = dict(traced["glyphs"])
        meta = traced["meta"]
    else:
        glyphs = {}
        meta = {"cap": GRID_CAP, "source": "veris-reference.png", "mode": "raster"}

    # Advance widths: match sibling reference letters where sensible.
    adv_map = {
        "l": 89 * SCALE * 0.75,
        "o": glyphs.get("e", {}).get("width", 537),
        "t": 89 * SCALE * 0.95,
        "n": glyphs.get("r", {}).get("width", 431) * 1.35,
        "a": glyphs.get("e", {}).get("width", 537) * 1.05,
    }

    for ch, img in derived_imgs.items():
        rec = glyph_record(img, adv_px=adv_map[ch] / SCALE)
        glyphs[ch] = rec

    meta["derived"] = list(DERIVED)
    meta["mode"] = "raster+derived"

    payload = {"meta": meta, "glyphs": glyphs}
    (OUT_DIR / "veris-glyphs.meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    data_js = (
        "/* Auto-generated by trace_veris.py + derive_veris-glyphs.py */\n"
        "(function (root) {\n"
        '  "use strict";\n'
        f"  root.VerisGlyphData = {json.dumps(glyphs, indent=2)};\n"
        f"  root.VerisGlyphMeta = {json.dumps(meta, indent=2)};\n"
        "})(typeof window !== 'undefined' ? window : globalThis);\n"
    )
    (OUT_DIR / "veris-glyphs.data.js").write_text(data_js, encoding="utf-8")

    print(f"Derived {len(derived_imgs)} glyphs: {''.join(DERIVED)}")
    for ch in DERIVED:
        g = glyphs[ch]
        print(f"  {ch}: adv={g['width']} draw={g['drawWidth']}x{g['drawHeight']}")


if __name__ == "__main__":
    main()
