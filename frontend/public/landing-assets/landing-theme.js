const darkLockup = new URL('../brand/sitewise-lockup-dark.png', import.meta.url).href;
const lightLockup = new URL('../brand/sitewise-lockup-light.png', import.meta.url).href;

export function mountTabletTheme(surround) {
  const toggle = surround.querySelector('[data-theme-toggle]');
  if (!toggle) return () => {};
  const previousTheme = surround.getAttribute('data-theme');
  const attributes = ['aria-label', 'aria-pressed', 'title', 'type'];
  const previousAttributes = attributes.map(name => [name, toggle.getAttribute(name)]);
  const brands = [...surround.querySelectorAll('[data-nav-brand]')].map(image => [image, image.getAttribute('src')]);

  function apply(dark) {
    surround.dataset.theme = dark ? 'dark' : 'light';
    const label = `Switch tablet to ${dark ? 'light' : 'dark'} mode`;
    toggle.setAttribute('aria-label', label);
    toggle.setAttribute('title', label);
    toggle.setAttribute('aria-pressed', String(dark));
    for (const [image] of brands) image.setAttribute('src', dark ? darkLockup : lightLockup);
  }

  const onToggle = () => apply(surround.dataset.theme !== 'dark');
  toggle.setAttribute('type', 'button');
  toggle.addEventListener('click', onToggle);
  apply(true);

  return () => {
    toggle.removeEventListener('click', onToggle);
    if (previousTheme === null) surround.removeAttribute('data-theme');
    else surround.setAttribute('data-theme', previousTheme);
    for (const [name, value] of previousAttributes) {
      if (value === null) toggle.removeAttribute(name);
      else toggle.setAttribute(name, value);
    }
    for (const [image, source] of brands) {
      if (source === null) image.removeAttribute('src');
      else image.setAttribute('src', source);
    }
  };
}

for (const surround of document.querySelectorAll('.sw-surround')) mountTabletTheme(surround);
