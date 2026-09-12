import { mountLandingDemo } from './landing-sequence.js';
const opening = document.querySelector('#project-workspace');
const demo = opening?.querySelector('.sw-demo');
const source = demo?.querySelector('.sw-surround');
if (opening && demo && source) {
  const gallery = document.createElement('div');
  gallery.className = 'sw-tablet-gallery';
  const full = document.createElement('div');
  full.className = 'sw-tablet-panel sw-tablet-panel--full';
  const crop = document.createElement('div');
  crop.className = 'sw-tablet-panel sw-tablet-panel--crop';
  crop.setAttribute('role', 'img');
  crop.setAttribute('aria-label', 'Animated cost plan shown on a cropped tablet');
  demo.before(gallery);
  full.append(demo);
  const left = document.createElement('section');
  const right = document.createElement('section');
  left.className = right.className = 'sw-tablet-feature';
  left.append(full);
  right.append(crop);
  gallery.append(left, right);
  const mirror = document.createElement('div');
  mirror.className = 'sw-tablet-mirror';
  crop.append(mirror);
  // Isolate the decorative copy from the live demo's selectors and event handlers.
  const shadow = mirror.attachShadow({ mode: 'open' });
  for (const sheet of document.querySelectorAll('link[rel="stylesheet"]')) shadow.append(sheet.cloneNode());
  const style = document.createElement('style');
  style.textContent = '#sitewise-landing{background:transparent!important;max-width:none!important}#sitewise-landing .sw-opening{padding:0!important}#sitewise-landing .sw-demo{margin:0!important}#sitewise-landing .sw-device-scale{width:1280px!important;zoom:1!important;container-type:inline-size}#sitewise-landing .sw-surround{transform:none!important;animation:none!important}#sitewise-landing .sw-document{height:560px}';
  shadow.append(style);
  const shell = document.createElement('div');
  shell.id = 'sitewise-landing';
  shadow.append(shell);
  let disposed = false;
  let cleanupDemo = () => {};
  // Load a pristine template: each tablet owns its own timing and scene state.
  fetch(new URL('../landing.html', import.meta.url)).then(response => {
    if (!response.ok) throw new Error('Tablet template unavailable');
    return response.text();
  }).then(html => {
    if (disposed) return;
    const template = new DOMParser().parseFromString(html, 'text/html').querySelector('.sw-demo');
    const wrapper = document.createElement('div');
    wrapper.className = 'sw-opening';
    wrapper.append(template);
    shell.append(wrapper);
    cleanupDemo = mountLandingDemo(shell, { playAll: true, initialScene: 'cost', repeatScene: true });
  }).catch(error => {
    console.error('Cost tablet failed to load', error);
    shell.append(source.cloneNode(true));
  });
  // The existing composition observer scales the live device to this panel.
  const resize = new ResizeObserver(() => {
    const zoom = demo.clientWidth / 1280;
    mirror.style.transform = `scale(${zoom * 1.55})`;
  });
  resize.observe(demo);
  window.addEventListener('pagehide', () => {
    disposed = true; cleanupDemo(); resize.disconnect();
  }, { once: true });
}

const platform = document.querySelector('#project-platform');
function showPlatformHeading() {
  if (!platform) return;
  const top = window.scrollY + platform.getBoundingClientRect().top - 72;
  window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
}
for (const link of document.querySelectorAll('a[href="#project-platform"]')) {
  link.addEventListener('click', event => {
    event.preventDefault();
    history.pushState(null, '', '#project-platform');
    showPlatformHeading();
  });
}
if (window.location.hash === '#project-platform') showPlatformHeading();
