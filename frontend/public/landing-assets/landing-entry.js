// A refresh starts at the hero; explicit links to lower sections still work on navigation.
history.scrollRestoration = 'manual';
const refreshed = performance.getEntriesByType('navigation')[0]?.type === 'reload';
if (refreshed && location.hash) history.replaceState(history.state, '', location.pathname + location.search);
window.addEventListener('pageshow', () => {
  if (refreshed || !location.hash) window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
});
