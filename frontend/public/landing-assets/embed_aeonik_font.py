"""One-off: embed Aeonik-Bold.otf as data URI in aeonik-font.css."""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent
font_path = ROOT / "fonts" / "Aeonik-Bold.otf"
out_path = ROOT / "aeonik-font.css"

b64 = base64.b64encode(font_path.read_bytes()).decode()
css = (
    "/* Aeonik Bold — embedded for reliable hero marquee loading */\n"
    "@font-face {\n"
    '  font-family: "Aeonik";\n'
    f'  src: url("data:font/otf;base64,{b64}") format("opentype");\n'
    "  font-weight: 400 800;\n"
    "  font-style: normal;\n"
    "  font-display: swap;\n"
    "}\n"
)
out_path.write_text(css, encoding="utf-8")
print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
