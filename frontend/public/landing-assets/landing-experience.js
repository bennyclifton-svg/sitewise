import { mountEstate } from './estate-development.js';
import { mountCadastralSea } from './cadastral-sea.js?v=hero-field-11';
/* global document, window, fetch, IntersectionObserver, CustomEvent */
const ns = 'http://www.w3.org/2000/svg';
const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
function element(name, attributes) {
  const node = document.createElementNS(ns, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}
export function ringPath(rings) {
  return rings.map(ring => ring.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ') + 'Z').join(' ');
}
export function inView(parcel) {
  return parcel.rings.some(ring => ring.some(([x,y]) => x >= -330 && x <= 330 && y >= -440 && y <= 440));
}
export async function mountExperience(plan) {
  if (!plan) return;
  const status = plan.querySelector('[data-map-status]') ?? document.createElement('p');
  const pause = plan.querySelector('[data-map-pause]');
  let paused = preference.matches;
  let estate, sea, complete = false;
  let onscreen = true;
  const update = () => {
    plan.classList.toggle('is-paused', paused || !onscreen || document.hidden);
    pause?.setAttribute('aria-pressed', String(paused));
    if (pause) pause.textContent = complete ? 'Replay map' : paused ? 'Play map' : 'Pause map';
    const hold = paused || !onscreen || document.hidden;
    estate?.sync(hold || Boolean(sea), preference.matches || Boolean(sea));
    sea?.sync(hold, preference.matches);
  };
  pause?.addEventListener('click', () => {
    if (complete) { complete = false; paused = false; estate?.replay(); }
    else paused = !paused;
    update();
  });
  preference.addEventListener('change', () => { paused = preference.matches; update(); });
  document.addEventListener('visibilitychange', update);
  window.addEventListener('sitewise:motion-pause', event => { paused = event.detail; update(); });
  const observer = new IntersectionObserver(([entry]) => { onscreen = entry.isIntersecting; update(); });
  observer.observe(plan);
  try {
    const response = await fetch('./landing-assets/coordination/sitewise-cadastral-plan.json');
    if (!response.ok) throw new Error('Map data unavailable');
    const data = await response.json();
    const svg = element('svg', { viewBox: '-280 -360 560 720', preserveAspectRatio: 'xMidYMid slice', class: 'sw-map-vector', tabindex:'0', role:'group', 'aria-label':'Cadastral parcels. Arrow keys select a parcel. Enter explores the illustrative project.' });
    const parcels = data.parcels.filter(inView);
    const nodes = [];
    let selected;
    function choose(node, parcel, linked = false) {
      selected?.classList.remove('is-selected'); selected = node; node.classList.add('is-selected');
      status.textContent = linked ? 'Illustrative project focus · Explore the building' : `${Math.round(parcel.area_m2).toLocaleString()} m² parcel · Select Find the project to explore the model`;
      if (linked) window.dispatchEvent(new CustomEvent('sitewise:project-focus'));
    }
    for (const parcel of parcels) {
      const path = element('path', { d:ringPath(parcel.rings), class:'sw-parcel', 'aria-hidden':'true' });
      path.addEventListener('click', () => choose(path, parcel));
      svg.append(path); nodes.push({parcel, path});
    }
    // A representative focus in the lower map leaves the headline unobstructed.
    const focus = nodes.filter(({parcel}) => parcel.area_m2 > 450 && parcel.area_m2 < 1000).sort((a,b) => {
      const distance = ({parcel}) => Math.hypot(parcel.rings[0][0][0]-80, parcel.rings[0][0][1]-150);
      return distance(a)-distance(b);
    })[0];
    plan.append(svg);
    estate = mountEstate(svg, data.parcels, data.boundaries ?? [], () => {
      complete = true;
      if (pause) pause.textContent = 'Replay map';
    });
    plan.classList.add('has-estate');
    sea = mountCadastralSea(plan.closest('.sw-coordination') ?? plan, data);
    let keyboardIndex=0;
    svg.addEventListener('keydown', event => {
      if (['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'].includes(event.key)) {
        event.preventDefault();
        keyboardIndex=(keyboardIndex+(['ArrowRight','ArrowDown'].includes(event.key)?1:-1)+nodes.length)%nodes.length;
        choose(nodes[keyboardIndex].path,nodes[keyboardIndex].parcel);
      } else if (event.key==='Enter' && focus) { event.preventDefault();choose(focus.path,focus.parcel,true); }
      else if (event.key==='Escape') { selected?.classList.remove('is-selected'); selected=undefined; status.textContent='Explore the parcel boundaries'; }
    });
    plan.querySelector('[data-map-focus]')?.addEventListener('click', () => { if (focus) choose(focus.path,focus.parcel,true); });
  } catch {
    status.textContent='Showing the cadastral plan. Interactive parcels could not load.';
    const focusButton = plan.querySelector('[data-map-focus]');
    if (focusButton) focusButton.disabled=true;
  }
  update();
  window.addEventListener('pagehide', () => { observer.disconnect(); estate?.dispose(); sea?.dispose(); });
  window.addEventListener('pageshow', () => { observer.observe(plan); update(); });
}
const plan = document.querySelector('.sw-coordination-plan');
if (plan) void mountExperience(plan);
