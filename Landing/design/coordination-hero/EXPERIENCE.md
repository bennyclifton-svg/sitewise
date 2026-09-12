# Integrated landing experience — 9 September 2026

User chose Datum Soft and ink blue, and authorised completion without further
questions. Local entry: `http://localhost:5173/landing.html`.

## Delivered

- Original Soft wordmark replaces the standalone landing's S lockup. Datum Soft
  is applied to the hero and principal headings; existing body/UI typography is
  retained for readability. Font remains an original display study, with the
  earlier comparison available at `/brand-lab.html`.
- 45/55 desktop model/map composition; map-first mobile stack. The headline sits
  over the map, enters by line, and changes emphasis with ordinary page scroll.
  No scroll interception or mouse-wheel camera zoom.
- Real cadastral parcels retain metre-based proportions. Pointer selection and
  arrow-key selection show source polygon area. Enter / Find the project links
  a representative parcel to the illustrative assembly. This is not a claim
  that the model is surveyed onto that real parcel.
- Timed boundary traces, pause/play, keyboard focus and contour toggle. Contours
  are generated from a coherent synthetic height field; no real elevation claim.
  Regenerate with `python Landing/model/coordination/build_contours.py`.
- 24-second illustrative assembly: foundations, structure, envelope, services,
  whole project. Merged discipline geometry limits the staging to system reveals
  and a structural clipping plane, not task-level construction simulation.
- 24-second continuous camera tour, interrupted by manual exploration.
- Save B-roll uses native canvas capture and MediaRecorder to download WebM.
  First actual export: `output/sitewise-brand/sitewise-building-tour.webm`.
  Playback verified: 641 × 900, 23.95 seconds, approximately 9.6 MB. It is a
  portrait camera study, not a finished multi-shot or sound-designed brand film.

## Runtime behaviour

`landing-experience.js` owns the map. `src/landing/scene-motion.ts` owns assembly,
camera playback and recording; `coordination.ts` owns the existing viewer.
Small DOM events connect map focus and system previews. Offscreen/hidden views
pause motion; reduced-motion preference disables map tracing and camera playback
and preserves manual system exploration. Video export is disabled if unsupported.
Map data failure keeps the static map and disables the dependent focus action.

No new runtime dependencies. Regenerate the viewer with `pnpm viewer:build`.
The static page remains independent of the React application.

## Validation

- Viewer build, TypeScript and ESLint pass.
- Existing landing composition/control suite: 17 passing tests.
- New map suite: 3 passing tests for keyboard focus/model linking, reduced motion
  and contour state, and the static fallback after a data error.
- Browser checks: full desktop composition, mobile fit without horizontal
  overflow, live model loading, linked assembly, palette/font rendering and
  playable B-roll export. Cadastral/source and model licence credits retained.

No production deployment was performed.
