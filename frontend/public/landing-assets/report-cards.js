const deck = document.querySelector('.report-deck');
const cards = [...document.querySelectorAll('.report-card')];
const controls = document.querySelector('.study-controls');

let pinned = null;
function showCard(selected) {
  const selectedIndex = cards.indexOf(selected);
  cards.forEach((card, index) => {
    const active = card === selected;
    card.classList.toggle('is-active', active);
    card.classList.toggle('is-after', selectedIndex !== -1 && index > selectedIndex);
    card.querySelector('.report-select').setAttribute('aria-pressed', String(card === pinned));
  });
}
function selectCard(selected) {
  pinned = selected;
  showCard(selected);
}

cards.forEach(card => {
  card.querySelector('.report-select').addEventListener('click', () => {
    selectCard(pinned === card ? null : card);
  });
  card.addEventListener('pointerenter', event => {
    if (event.pointerType === 'mouse') showCard(card);
  });
  card.addEventListener('pointerleave', () => showCard(pinned));
  card.addEventListener('focusin', () => showCard(card));
  card.addEventListener('focusout', () => showCard(pinned));
});

document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    selectCard(null);
    if (deck.contains(document.activeElement)) document.activeElement.blur();
  }
});

function setComposition() {
  const separation = controls.elements.namedItem('separation').value;
  const angle = controls.elements.namedItem('angle').value;
  deck.style.setProperty('--separation', `${separation}px`);
  deck.style.setProperty('--angle', `${angle}deg`);
  document.querySelector('[data-separation-value]').textContent = `${separation} px`;
  document.querySelector('[data-angle-value]').textContent = `${angle}°`;
}
controls.addEventListener('input', setComposition);
controls.addEventListener('submit', event => event.preventDefault());
document.querySelector('[data-reset]').addEventListener('click', () => {
  controls.reset();
  setComposition();
  selectCard(null);
});

let revision = 0;
const startingRevisions = cards.map(card => Number(card.querySelector('[data-revision]').textContent));
const bars = [...document.querySelectorAll('[data-bar]')];
const starts = bars.map(bar => Number(bar.style.getPropertyValue('--start')));
document.querySelector('[data-update]').addEventListener('click', () => {
  revision += 1;
  const revised = revision % 2 === 1;
  document.querySelector('.report-demo').classList.toggle('is-revised', revised);
  cards.forEach((card, index) => {
    card.querySelector('[data-revision]').textContent = String(startingRevisions[index] + revision).padStart(2, '0');
  });
  const structuralForecast = revised ? 886000 : 872000;
  document.querySelector('[data-cost]').textContent = structuralForecast.toLocaleString('en-AU');
  document.querySelector('[data-total]').textContent = (245000 + structuralForecast + 415000 + 325000 + 185000).toLocaleString('en-AU');
  bars.forEach((bar, index) => bar.style.setProperty('--start', starts[index] + (revised ? .5 : 0)));
  document.querySelector('[data-plan-text]').textContent = revised
    ? 'Revised structural drawings received. Reconcile the package scope, forecast and procurement dates.'
    : 'Complete consultant coordination before releasing the structural package.';
  document.querySelector('[data-program-text]').textContent = revised ? 'Structural package · forecast shifted by half a week' : 'Linked activities · current forecast';
  document.querySelector('[data-procurement]').textContent = revised ? 'Scope review' : 'Preparing';
  document.querySelector('[data-procurement-note]').textContent = revised
    ? 'Review revised structural scope and dates before issuing the package.'
    : 'Confirm the structural scope before issuing the package.';
  document.querySelector('[data-status]').textContent = `Illustrative update ${revision}: ${revised ? 'revised structural scope' : 'original scope restored'}. All four records revised; forecast total ${((245000 + structuralForecast + 415000 + 325000 + 185000)).toLocaleString('en-AU')} dollars.`;
});
