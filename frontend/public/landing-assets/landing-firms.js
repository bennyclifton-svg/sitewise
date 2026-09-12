const strip = document.querySelector('.sw-firm-strip');
if (strip) {
  let visible = false;
  const sync = () => { strip.dataset.paused = String(!visible || document.hidden); };
  const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
  observer.observe(strip);
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('pagehide', () => { observer.disconnect(); document.removeEventListener('visibilitychange', sync); }, { once: true });
  sync();
}
