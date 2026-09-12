const clamp = value => Math.max(0, Math.min(1, value));
const pathFor = rings => rings.map(ring => ring.map((p, i) => `${i ? 'L' : 'M'}${p}`).join('') + 'Z').join('');
const pointKey = point => point.join(',');
// Stable source parcel IDs select five whole street blocks, in development order.
const stageSeeds = ['1843778', '64008', '64011', '1862283', '1863995'];

export function closedFrontage(boundaries) {
  const neighbours = new Map();
  for (const { points: [a, b] } of boundaries) {
    for (const [from, to] of [[a, b], [b, a]]) {
      const key = pointKey(from);
      if (!neighbours.has(key)) neighbours.set(key, []);
      neighbours.get(key).push(to);
    }
  }
  if (!neighbours.size || [...neighbours.values()].some(points => points.length !== 2)) throw new Error('Stage frontage must form a closed road loop');
  const start = boundaries[0].points[0], ring = [start];
  let previous = null, current = start;
  while (ring.length <= neighbours.size) {
    const next = neighbours.get(pointKey(current)).find(point => pointKey(point) !== previous);
    if (pointKey(next) === pointKey(start)) break;
    previous = pointKey(current); current = next; ring.push(current);
  }
  if (ring.length !== neighbours.size) throw new Error('Stage has disconnected frontage loops');
  return ring;
}

export function estateStages(parcels, boundaries, seeds = stageSeeds) {
  const byId = new Map(parcels.map(parcel => [parcel.id, parcel]));
  const adjacency = new Map(parcels.map(parcel => [parcel.id, new Set()]));
  for (const boundary of boundaries) for (const a of boundary.parcels) for (const b of boundary.parcels) {
    if (a !== b && byId.has(b)) adjacency.get(a)?.add(b);
  }
  const assigned = new Set();
  return seeds.filter(seed => byId.has(seed)).map(seed => {
    const ids = new Set([seed]), queue = [seed];
    for (let i = 0; i < queue.length; i++) for (const next of adjacency.get(queue[i])) {
      if (!ids.has(next)) { ids.add(next); queue.push(next); }
    }
    if (queue.some(id => assigned.has(id))) throw new Error('A road block cannot belong to two stages');
    queue.forEach(id => assigned.add(id));
    const frontages = boundaries.filter(boundary => boundary.parcels.length === 1 && ids.has(boundary.parcels[0]));
    const ring = closedFrontage(frontages);
    // Every released lot must have frontage on the enclosing road.
    const serviced = new Set(frontages.map(boundary => boundary.parcels[0]));
    if (queue.some(id => !serviced.has(id))) throw new Error('A stage contains an unserviced lot');
    return {
      ring, roadPaths: [pathFor([ring])],
      perimeter: prepareTrace([ring.concat([ring[0]])]),
      interior: prepareTrace(boundaries.filter(edge => edge.parcels.length > 1 && edge.parcels.every(id => ids.has(id))).map(edge => edge.points)),
      lots: queue.map((id, i) => ({ id, path: pathFor(byId.get(id).rings), order: i / queue.length })),
    };
  });
}

export function prepareTrace(lines) {
  const segments = lines.flatMap(line => line.slice(1).map((end, i) => ({ start: line[i], end, length: Math.hypot(end[0] - line[i][0], end[1] - line[i][1]) })));
  return { segments, length: segments.reduce((sum, segment) => sum + segment.length, 0) };
}

export function tracePath(trace, progress) {
  if (progress >= 1) return trace.segments.map(({ start, end }) => `M${start}L${end}`).join('');
  let remaining = trace.length * clamp(progress), path = '';
  for (const { start, end, length } of trace.segments) {
    if (remaining <= 0) break;
    const ratio = Math.min(1, remaining / length);
    const point = ratio === 1 ? end : [start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio];
    path += `M${start}L${point}`;
    remaining -= length;
  }
  return path;
}

function traceHighlight(trace, start, end) {
  let offset = 0, path = '';
  for (const segment of trace.segments) {
    const from = Math.max(0, start * trace.length - offset);
    const to = Math.min(segment.length, end * trace.length - offset);
    if (to > from) {
      const point = distance => segment.start.map((value, i) => value + (segment.end[i] - value) * distance / segment.length);
      path += `M${point(from)}L${point(to)}`;
    }
    offset += segment.length;
  }
  return path;
}

export function lotProgress(stage, time) {
  const age = time - stage * 3;
  return { road: clamp(age / 1), interior: clamp((age - 1.2) / 1.5) };
}

export function mountEstate(svg, parcels, boundaries, onComplete) {
  const win = svg.ownerDocument.defaultView;
  const stages = estateStages(parcels, boundaries);
  const duration = stages.length * 3;
  function element(name, attributes) {
    const node = svg.ownerDocument.createElementNS(svg.namespaceURI, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }
  const layer = element('g', { class: 'sw-estate', 'aria-hidden': 'true' });
  const selected = new Set(stages.flatMap(stage => stage.lots.map(lot => lot.id)));
  const context = boundaries.filter(edge => !edge.parcels.some(id => selected.has(id)));
  layer.append(element('path', { d: tracePath(prepareTrace(context.map(edge => edge.points)), 1), class: 'sw-estate-context' }));
  const groups = stages.map(stage => {
    const road = element('path', { class: 'sw-estate-road' });
    const interior = element('path', { class: 'sw-estate-lot' });
    layer.append(road, interior);
    return { road, interior, perimeterTrace: stage.perimeter, interiorTrace: stage.interior };
  });
  const highlight = element('path', { class: 'sw-estate-highlight' });
  layer.append(highlight);
  svg.prepend(layer);
  let time = 0, last = null, frame = 0, complete = false;
  function draw() {
    if (complete && stages.length) {
      const cycle = (time - duration) / 6;
      const phase = cycle % 1;
      highlight.setAttribute('d', traceHighlight(stages[Math.floor(cycle) % stages.length].perimeter, Math.max(0, phase - .09), phase));
      highlight.style.opacity = String(Math.sin(phase * Math.PI) * .5);
      return;
    }
    groups.forEach((group, stage) => {
      const progress = lotProgress(stage, time);
      group.road.setAttribute('d', tracePath(group.perimeterTrace, progress.road));
      group.interior.setAttribute('d', tracePath(group.interiorTrace, progress.interior));
    });
    if (time >= duration && !complete) { complete = true; onComplete(); }
  }
  function tick(now) {
    time += last === null ? 0 : Math.min((now - last) / 1000, .1); last = now;
    draw();
    frame = win.requestAnimationFrame(tick);
  }
  draw();
  return {
    sync(paused, reduced) {
      win.cancelAnimationFrame(frame); last = null;
      if (reduced) { time = duration; draw(); highlight.setAttribute('d', ''); }
      if (!paused && !reduced) frame = win.requestAnimationFrame(tick);
    },
    replay() { time = 0; complete = false; highlight.setAttribute('d', ''); draw(); },
    dispose() { win.cancelAnimationFrame(frame); },
  };
}
