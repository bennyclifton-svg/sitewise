# Perspective hero — static checkpoint v2

The full development now uses a lower perspective view on the established Petrol / Air palette. The matching plan is authored separately from the same `perspective-context.json` coordinates.

## Reproduce

From the repository root in PowerShell:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/coordination/build_perspective_hero.py
python Landing/model/coordination/export_perspective_hero.py
```

Add `-- --draft` to the Blender command and `--draft` to the export command for the 900 × 990 preview. The final is 1200 × 1320, Cycles 32 samples with denoising; export only changes file format, using WebP quality 89.

## Outputs

- `sitewise-perspective-hero-v2.blend`: derived scene; original siting and v1 hero scenes remain intact.
- `22-perspective-hero.png`: full-resolution render.
- `frontend/public/landing-assets/coordination/sitewise-hero-perspective.webp`: delivery image.
- `perspective-hero-manifest.json`: camera, palette, geometry checks, fence provenance and source-object exception list.
- `perspective-hero-export.json`: image dimensions, file size and draft/final status.

## Composition and validation

- Actual perspective projection, 29.68 mm lens, 15.99° elevation. Geometric horizon is 21.5% from image top; atmospheric colour blends the distant ground into Air sky.
- Registered building/parcel bounds occupy approximately 10.75–91.25% of image width and 31.70–74.36% of image height. This allows the specified wide desktop cover crop while retaining the development and selected lot.
- Canonical sRGB Petrol `#12606D`, Air `#93CEDD`, Chalk `#F9F7F3` and Ink `#0F1F22` are explicitly converted to scene-linear colours. Lighting and AgX tone mapping vary their rendered appearance.
- 1,912 original, reprojected cadastral segments come directly from the shared context. Boundaries use thin, constant-emission near-white curves, without invented subdivisions.
- Every source-object transform is checked unchanged. Original architecture, floor plates, roofs and balcony guards remain; no timber overlay is present.
- 1,053 original low external-fence objects are suppressed by source family, original parent group and original height. The 100 remaining objects in those guard families are retained. The manifest lists the suppressed source IDs.
- New open perimeter-fence centrelines lie exactly on the selected lot edges, X ±12 and Y ±22; measured centreline error is zero. Physical post half-thickness extends either side. The opening at Y = −22, X −10.5 to −6.5 is an illustrative access gap.
- Ground remains level at Z = −0.12. The wider context introduces no terrain elevations. Coordinates are imported-model units, not verified metres.

## Scope and source

This is a still composition checkpoint. Camera animation, street utility routes, traffic movement and structural coordination remain separate work. The current structural direction is reinforced-concrete columns and slabs; this hero does not expose or newly model them. Fence design, access dimensions and cadastral reconstruction do not establish survey or compliance outcomes.

The supplied `duplex.glb` metadata credits **MyStudioNZ**, *Duplex houses at 22 ARNWOOD STREET MANUREWA*, with a **CC-BY-4.0** label and [source model link](https://sketchfab.com/3d-models/duplex-houses-at-22-arnwood-street-manurewa-ef88f585f3d045c89c849ddd64495ad5). Metadata is provided provenance, not independent licence verification. SiteWise modifications include material treatment, lighting, camera, illustrative parcel/context placement and the replacement boundary fence. Existing `sitewise-hero-credits.json` retains the source attribution for the landing page.
