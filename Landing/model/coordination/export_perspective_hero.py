"""Convert the inspected Blender perspective render to the landing WebP asset."""
import json
import sys
from pathlib import Path

from PIL import Image


output = Path(__file__).resolve().parent
web = output.parents[2] / "frontend/public/landing-assets/coordination"
draft = "--draft" in sys.argv
source = output / ("21-perspective-hero-draft.png" if draft else "22-perspective-hero.png")
target = web / "sitewise-hero-perspective.webp"
web.mkdir(parents=True, exist_ok=True)
with Image.open(source) as render:
    render.convert("RGB").save(target, "WEBP", quality=89, method=6)
with Image.open(target) as exported:
    exported.load()
    assert exported.size == ((900, 990) if draft else (1200, 1320))
    result = {"source": str(source), "asset": str(target), "size": list(exported.size),
              "bytes": target.stat().st_size, "draft": draft}
(output / "perspective-hero-export.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result))
