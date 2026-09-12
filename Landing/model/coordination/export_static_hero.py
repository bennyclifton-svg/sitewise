"""Convert the unchanged Blender still to the web delivery format."""
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parent
destination=root.parents[2]/'frontend/public/landing-assets/coordination/sitewise-hero-isometric.webp'
with Image.open(root/'19-static-hero-isometric.png') as source:
    source.convert('RGB').save(destination,'WEBP',quality=89,method=6)
print(destination, destination.stat().st_size)
