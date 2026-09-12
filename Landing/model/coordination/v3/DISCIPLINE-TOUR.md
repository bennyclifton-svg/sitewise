# Manual discipline exploration

Automatic discipline cycling is disabled. The viewer starts with the whole white model.

Seven outlined, transparent buttons (S E M H C L I) preview a discipline on hover or keyboard focus. Clicking locks the discipline; clicking the selected button again or pressing Escape restores the whole model. Leaving an unselected preview restores the current locked selection, or the whole model if none is locked. Full accessible labels and tooltips retain the discipline names.

Four matching camera controls (T F S R) select top, front, side and rear. Clicking the active camera button again restores the base perspective. The All, Architecture and Perspective buttons are removed.

Landscaping, fences, driveways and pavement stay visible in white. Selected services use crisp blue with faint building outlines, without fades or bloom. Secondary vehicle/rotor updates pause while inspecting a discipline. Existing pause and reduced-motion support remains in the shared scene motion controller.

The previous sequence module is not connected to the viewer. `dwelling-reveal.ts` still controls material visibility and matching shadows; `export_outlines.py` supplies simplified building outlines.

Wheel zoom is enabled only when a ray from the pointer intersects visible model geometry, including the site. Outside that geometry, OrbitControls leaves the wheel event untouched so the browser scrolls normally. The check is recalculated for every wheel event and respects the current camera and discipline visibility.
