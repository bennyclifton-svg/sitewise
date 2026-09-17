# Separate chalk-white 3D assets

Nine authored mesh assets based on the approved illustration direction. These are
editable approximations, not recovered geometry from the generated images.

| File stem | Object |
| --- | --- |
| drawings | Plan sheets with an open spiral roll |
| cost-programme | Programme grid, blue activity bars and curled sheet |
| hard-hat | Domed shell, brim, crown ribs and front logo panel |
| contract-coordination | Contract folio with paragraph rules and signatures |
| planning-legislation | Planning legislation reference book |
| ncc-bca | Combined NCC / BCA reference book |
| australian-standards | Australian standards reference book |
| advice | SiteWise advice folio |
| emails | Correspondence stack and folded envelope |

Each asset has an independent `.glb`, `.blend` and transparent `.png` preview.
GLBs and previews live in `frontend/public/landing-assets/system-3d/`; Blender
sources live beside this README. Each GLB embeds its geometry and materials,
including lettering converted to meshes, with no external texture or font files.
GLBs use Y-up; Blender sources use Z-up. Dimensions are illustrative display
units (paper cover 1.4 by 1.9), so scale uniformly to suit the scene.

The Blender source includes its own orthographic preview camera and studio
lights. GLB exports contain only the asset meshes, without camera or lighting.
The landing page still uses the previous static illustrations. The separate
gallery at `/system-assets-3d.html` lets you rotate, zoom and download each model.

Rebuild the meshes and PNGs using Blender 5.1:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python Landing/system-assets/3d/build_assets.py
```

The gallery's Three.js source is `frontend/src/landing/system-assets-preview.ts`.
It uses the repository's existing Three.js dependency; no dependency was added.
`manifest.json` records mesh-object counts, polygon-face counts and file sizes.
