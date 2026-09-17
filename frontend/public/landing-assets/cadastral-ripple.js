import { applyChipClip } from './system-chip.js';

export const DELAY_PER_CELL = 55;
export const DURATION_BASE = 200;
export const DURATION_PER_CELL = 0;
export const DEFAULT_VIEWBOX = [-280, -360, 560, 720];
const NS = 'http://www.w3.org/2000/svg';

function samePoint(a, b) {
  return a[0] === b[0] && a[1] === b[1];
}

export function centroid(rings) {
  let x = 0;
  let y = 0;
  let count = 0;
  for (const ring of rings ?? []) {
    const closed = ring.length > 1 && samePoint(ring[0], ring.at(-1));
    const points = closed ? ring.slice(0, -1) : ring;
    for (const [px, py] of points) {
      x += px;
      y += py;
      count += 1;
    }
  }
  return count ? [x / count, y / count] : [0, 0];
}

export function ringPath(rings) {
  return rings.map(ring => ring.map(([x, y], index) => `${index ? 'L' : 'M'}${x},${y}`).join(' ') + 'Z').join(' ');
}

export function parcelInView(parcel, viewBox = DEFAULT_VIEWBOX) {
  const [minX, minY, width, height] = viewBox;
  const maxX = minX + width;
  const maxY = minY + height;
  return (parcel.rings ?? []).some(ring => ring.some(([x, y]) => x >= minX && x <= maxX && y >= minY && y <= maxY));
}

export function fullViewBox(parcels, pad = 24) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const parcel of parcels ?? []) {
    for (const ring of parcel.rings ?? []) {
      for (const [x, y] of ring) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }
  if (!Number.isFinite(minX)) return DEFAULT_VIEWBOX;
  return [minX - pad, minY - pad, (maxX - minX) + pad * 2, (maxY - minY) + pad * 2];
}

export function rippleTiming(origin, target, scale) {
  const distance = Math.hypot(origin[0] - target[0], origin[1] - target[1]) / Math.max(scale, 1);
  return {
    delay: Math.max(0, distance * DELAY_PER_CELL),
    duration: DURATION_BASE + distance * DURATION_PER_CELL,
  };
}

export function nearestNeighborScale(nodes) {
  const distances = [];
  for (let index = 0; index < nodes.length; index += 1) {
    let nearest = Infinity;
    for (let other = 0; other < nodes.length; other += 1) {
      if (index === other) continue;
      const gap = Math.hypot(
        nodes[index].centroid[0] - nodes[other].centroid[0],
        nodes[index].centroid[1] - nodes[other].centroid[1],
      );
      if (gap < nearest) nearest = gap;
    }
    if (Number.isFinite(nearest)) distances.push(nearest);
  }
  if (!distances.length) return 16;
  distances.sort((left, right) => left - right);
  return distances[Math.floor(distances.length / 2)] || 16;
}

export function applyRipple(nodes, origin, scale, reduced) {
  for (const node of nodes) {
    const timing = rippleTiming(origin.centroid, node.centroid, scale);
    node.path.style.setProperty('--delay', `${timing.delay}ms`);
    node.path.style.setProperty('--duration', `${timing.duration}ms`);
    node.path.classList.toggle('is-origin', node === origin);
    node.path.classList.remove('is-rippling');
  }
  const host = origin.path.closest('[data-lot-ripple]') ?? origin.path.ownerSVGElement;
  if (host) void host.offsetWidth;
  if (reduced) return;
  for (const node of nodes) node.path.classList.add('is-rippling');
}

function element(document, name, attributes) {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

export async function mountCadastralRipple(host, options = {}) {
  if (!host) return { dispose() {} };
  const chip = options.chip ?? host.hasAttribute('data-system-chip');
  if (chip) applyChipClip(host);
  const media = host.ownerDocument.defaultView?.matchMedia;
  const reducedMotion = options.reducedMotion ?? (
    typeof media === 'function' ? media.call(host.ownerDocument.defaultView, '(prefers-reduced-motion: reduce)').matches : false
  );
  const status = host.querySelector('[data-ripple-status]');
  let data = options.data;
  if (!data) {
    try {
      const response = await fetch('./landing-assets/coordination/sitewise-cadastral-plan.json');
      if (!response.ok) throw new Error('Map data unavailable');
      data = await response.json();
    } catch {
      if (status) status.textContent = 'Cadastral lots could not load.';
      return { dispose() {} };
    }
  }
  const parcels = data.parcels ?? [];
  const viewBox = fullViewBox(parcels);
  if (!chip) host.style.setProperty('--sw-map-ratio', `${viewBox[2]} / ${viewBox[3]}`);
  const svg = element(host.ownerDocument, 'svg', {
    viewBox: viewBox.join(' '),
    preserveAspectRatio: chip ? 'xMidYMid slice' : 'xMidYMid meet',
    class: 'sw-lot-ripple-map',
    tabindex: '0',
    role: 'group',
    'aria-label': 'Two-dimensional cadastral lots. Click a lot to ripple through the neighbouring parcels.',
  });
  const nodes = parcels.map(parcel => {
    const path = element(host.ownerDocument, 'path', {
      d: ringPath(parcel.rings),
      class: 'sw-lot',
      'data-lot': parcel.id,
    });
    svg.append(path);
    return { parcel, path, centroid: centroid(parcel.rings) };
  });
  const scale = nearestNeighborScale(nodes);
  let keyboardIndex = 0;
  const activate = node => {
    if (!node) return;
    applyRipple(nodes, node, scale, reducedMotion);
    if (status) {
      const area = Math.round(node.parcel.area_m2 ?? 0).toLocaleString();
      status.textContent = `${area} m² parcel`;
    }
  };
  const onClick = event => {
    const path = event.target.closest('.sw-lot');
    if (!path) return;
    const node = nodes.find(entry => entry.path === path);
    keyboardIndex = Math.max(0, nodes.indexOf(node));
    activate(node);
  };
  const onKey = event => {
    if (['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      const step = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1;
      keyboardIndex = (keyboardIndex + step + nodes.length) % nodes.length;
      activate(nodes[keyboardIndex]);
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      activate(nodes[keyboardIndex]);
    } else if (event.key === 'Escape') {
      for (const node of nodes) {
        node.path.classList.remove('is-origin', 'is-rippling');
      }
      if (status) status.textContent = '';
    }
  };
  svg.addEventListener('click', onClick);
  svg.addEventListener('keydown', onKey);
  host.append(svg);
  if (status) status.textContent = 'Select a lot';
  return {
    dispose() {
      svg.removeEventListener('click', onClick);
      svg.removeEventListener('keydown', onKey);
      svg.remove();
    },
  };
}

for (const host of document.querySelectorAll('[data-lot-ripple]')) {
  void mountCadastralRipple(host);
}
