# Cadastral landscape source and vector reconstruction

Source: the user-supplied repository file `Landing/cadastral-landscape.png`
(5504 × 3072 pixels).

The raster web assets preserve the complete image and its lot shapes and morphology.
Only proportional resizing and WebP encoding were applied; there is no cropping,
warping, recolouring, or redrawing. Heights are rounded to the nearest pixel.

The main animation renders reconstructed vector boundaries directly as WebGL
geometry, with a consistent screen-space stroke and antialiased edges. It does not
enlarge a rasterized SVG. A slow diagonal height wave raises and lowers shared
corners while the camera advances; each straight boundary remains a straight
segment between its corners. An independent, broad blue-to-teal colour field
sweeps across the landscape instead of highlighting the physical wave crest.
A raised horizon and stronger distance fade dissolve the map behind the hero.
Mirrored repetition extends the finite source;
the repeated landscape is illustrative, not an authoritative cadastral map.

`cadastral-lines.svg` and `cadastral-lines.json` contain 3,341 polylines and 3,940
segments reconstructed from the source. Extraction isolates bright line centres,
thins them with Zhang-Suen skeletonization, and follows the connected paths.
Graph reconstruction then welds glow-generated junction clusters, prunes tiny
spurs, fits straight parcel runs and collapses narrow duplicate glow faces onto
a shared boundary. The source rebuild welds 1,583 nodes, prunes 249 spurs and
collapses 109 false thin faces. Genuine road curves and wider corridors remain.
There are 3,042 straight two-point runs. The reproducible script is
`frontend/scripts/extract-cadastral-vectors.py` (NumPy and Pillow, build-time only).
Visible parcel layout and road corridors remain source-derived. No unseen lots
are invented. The original perspective remains, while small baked-in bends on
otherwise straight parcel edges are regularized. Unresolved details and the
blurred horizon cannot be recovered exactly from this still.
The fly-through uses the source's 42–98% height band so compressed horizon
fragments never repeat into the foreground; the SVG and JSON retain the full trace.

While vectors load, or if loading fails, a raster renderer shows the original
land crop with higher-resolution sampling, mipmaps and optional anisotropic
filtering. None of these presentation operations edits the source file or the
stored WebP derivatives. If WebGL is unavailable, the complete original image
remains as a proportional CSS grayscale/invert backdrop with a soft fade.
Reduced motion renders a still; the visible motion control pauses both the flight
and console drift without resetting their positions.

| Asset | Dimensions | WebP quality |
| --- | --- | --- |
| `cadastral-landscape-high.webp` | 4096 × 2286 | 96 |
| `cadastral-landscape.webp` | 2200 × 1228 | 90 |
| `cadastral-landscape-medium.webp` | 1100 × 614 | 88 |
| `cadastral-landscape-small.webp` | 640 × 357 | 88 |

The image carries no asserted geographic location or project identity. Do not
present it as a named development, customer project, or evidence of product use.
