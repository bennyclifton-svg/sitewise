# SiteWise type studies — 09 September 2026

Review at `/brand-lab.html`. This isolated prototype does not replace the live
landing page or adopt a final brand direction.

## Original typeface studies

`python Landing/design/datum/build_fonts.py` generates three real TrueType fonts
under `frontend/public/landing-assets/datum/` using FontTools as a build tool.
No font outlines are copied or derived from third-party fonts.

- Datum: extended proportions, medium roundness, light architectural strokes.
- Span: fuller curves, lighter strokes, alternate a and W constructions.
- Section: compact proportions, squared curves, angular S/s.

Each contains 67 original characters: Latin uppercase and lowercase, numerals,
period, comma, colon, hyphen and slash, plus a space glyph. These are prototype
outlines, not release-ready fonts. Unsupported characters use browser fallback.
UI explanatory copy uses the system sans while the bespoke display cuts are
evaluated; it is not the proposed final text face.

Still required after direction selection: optical corrections, overlap removal,
kerning, accent and symbol coverage, production webfont packaging and a tuned
body-text cut. No claim of a completed proprietary font family yet.

## Interaction scope

Font and palette switches update the wordmark, headline and type specimen.
Replay reveals headline lines through masks. Scroll changes the middle line's
colour; reduced motion disables the entrance. All switches are native buttons
with pressed states, keyboard access and visible focus. Editable specimen text
stays in the page; no analytics, persistence or network submission.

The real cadastral map is reused unchanged with on-page attribution. The
existing building poster receives a CSS hue shift for colour exploration only.
There is no claim that the building occupies a lot in this cadastral extract.

Construction sequencing, B-roll, contours and linked parcel/building behaviour
remain subsequent steps. This prototype is the first decision checkpoint for
the user's request to move quickly and see alternative type directions.

## Round 2

User chose Datum and ink blue, requesting less elongation and a more finished feel.
The lab now compares Original, Refined (default) and Soft. Refined reduces the
construction width from 1.16 to 1.02, increases strokes from 62 to 72 units,
redraws e/r/W, uses outline-based sidebearings and adds 11 kerning pairs.
Soft uses the same revised spacing and width, with rounder bowls and 66-unit
strokes. Both remain display prototypes. Earlier cuts remain archived.

## Selected direction

User selected C / Soft (DatumSoft), retaining ink blue. This is now the lab
default and the direction for subsequent landing-page work.
