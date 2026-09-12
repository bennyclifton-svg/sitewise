export function mountComposition(opening) {
  const demo = opening.querySelector('.sw-demo');
  const device = demo?.querySelector('.sw-device-scale');
  if (!demo || !device) return () => {};
  const win = opening.ownerDocument.defaultView;
  const desktop = win.matchMedia('(min-width: 900px)');
  const previousZoom = opening.style.getPropertyValue('--sw-device-zoom');
  const previousMode = opening.dataset.composition;

  function update() {
    const width = demo.clientWidth;
    if (!desktop.matches || width <= 0) {
      opening.style.removeProperty('--sw-device-zoom');
      delete opening.dataset.composition;
      return;
    }
    const zoom = String(width / 1280);
    if (opening.style.getPropertyValue('--sw-device-zoom') !== zoom) {
      opening.style.setProperty('--sw-device-zoom', zoom);
    }
    opening.dataset.composition = 'scaled';
  }

  const observer = new win.ResizeObserver(update);
  observer.observe(demo);
  desktop.addEventListener('change', update);
  update();

  return () => {
    observer.disconnect();
    desktop.removeEventListener('change', update);
    if (previousZoom) opening.style.setProperty('--sw-device-zoom', previousZoom);
    else opening.style.removeProperty('--sw-device-zoom');
    if (previousMode === undefined) delete opening.dataset.composition;
    else opening.dataset.composition = previousMode;
  };
}

for (const opening of document.querySelectorAll('.sw-opening')) mountComposition(opening);
