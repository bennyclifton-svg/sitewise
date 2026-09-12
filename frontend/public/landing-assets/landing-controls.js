import { costGroups, costRollup, costTotals, projectCostTotals, programmeGroups, programmeDependencies, programmeStart, programmeEnd, addDays, duration, finish, position } from './landing-control-data.js';
import { createProcurementScene } from './landing-procurement.js';

const escape = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const money = value => value == null ? '—' : value.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const date = value => new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short', year: '2-digit', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`));
const cell = (value, label, className = '') => `<td class="${className}" data-label="${label}"><div class="sw-cell-reveal"><div><span data-label="${label}">${value}</span></div></div></td>`;

const costColumns = [
  ['budget', 'Budget'], ['approved', 'Approved Contract'],
  ['forecastVariations', 'Forecast Variations'], ['approvedVariations', 'Approved Variations'],
  ['forecast', 'Forecast Final Cost'], ['variance', 'Budget Variance'],
  ['claimed', 'Claimed to Date'], ['thisMonth', 'This Month'], ['remaining', 'Remaining'],
];
const sortIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 8 4-4 4 4M7 4v16m6-4 4 4 4-4M17 20V4"/></svg>';
const calendarIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M8 15h.01M12 15h.01M16 15h.01M8 18h.01M12 18h.01"/></svg>';

function costMoneyCells(totals, summary = false) {
  return costColumns.map(([key, label], index) => cell(money(totals[key]), label,
    `sw-money${!summary && index < 4 ? ' sw-cost-editable' : ''}`)).join('');
}
function costSummary(label, totals, final = false) {
  return `<tr class="sw-cost-subtotal is-built" ${final ? 'data-final-reveal=""' : 'data-build-row=""'}>
    ${cell('', 'Code', 'sw-cost-code-cell')}<td colspan="2"><div class="sw-cell-reveal"><div><span>${label}</span></div></div></td>
    ${costMoneyCells(totals, true)}${cell('', 'Actions')}</tr>`;
}
function costMarkup() {
  return `<div class="sw-cost-tabs"><div class="sw-cost-tab-list"><span aria-current="page">Cost Plan v9</span><span>Invoices</span><span>Variations</span></div><span class="sw-cost-month"><time datetime="2026-08">August 2026</time>${calendarIcon}</span></div>
    <table class="sw-cost-grid" aria-label="Cost Plan v9 · AUD excluding GST">
      <colgroup><col class="sw-cost-code"><col class="sw-cost-category"><col class="sw-cost-description">${costColumns.map(() => '<col class="sw-cost-money">').join('')}<col class="sw-cost-actions"></colgroup>
      <thead><tr>${['Code', 'Category', 'Item'].map(label => `<th scope="col"><span data-column-heading="">${label}${sortIcon}</span></th>`).join('')}${costColumns.map(([, label]) => `<th scope="col"><span data-column-heading="">${label}</span></th>`).join('')}<th scope="col" aria-label="Actions"></th></tr></thead>
      ${costGroups.map(group => `<tbody class="sw-control-section is-filled" data-section="${group.id}" data-section-title="${group.title}">
        <tr class="sw-cost-placeholder" aria-hidden="true">${cell('', 'Code')}<td><div class="sw-cell-reveal"><div><span>${group.title}</span></div></div></td><td colspan="11"><div class="sw-cell-reveal"><div><span><i class="sw-thinking"></i></span></div></div></td></tr>
        ${group.rows.map(row => `<tr data-build-row="${row[0]}" class="is-built">${cell(row[0], 'Code', 'sw-cost-code-cell')}${cell(escape(group.title), 'Category', 'sw-cost-editable')}${cell(escape(row[1]), 'Item', 'sw-cost-editable')}${costMoneyCells(costRollup(row))}${cell('', 'Actions')}</tr>`).join('')}
        ${costSummary(`${group.title} subtotal`, costTotals(group))}
      </tbody>`).join('')}
      <tfoot>${costSummary('Grand total', projectCostTotals, true)}</tfoot>
    </table>`;
}

const chevronIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
const plusIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>';
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function axisBands(scale) {
  const bands = [];
  for (let cursor = programmeStart; cursor < programmeEnd;) {
    const date = new Date(`${cursor}T00:00:00Z`), year = date.getUTCFullYear(), month = date.getUTCMonth();
    const next = scale === 'week' ? addDays(cursor, 7) : new Date(Date.UTC(
      scale === 'year' ? year + 1 : year,
      scale === 'year' ? 0 : scale === 'quarter' ? Math.floor(month / 3) * 3 + 3 : month + 1, 1,
    )).toISOString().slice(0, 10);
    const end = next < programmeEnd ? next : programmeEnd;
    const label = scale === 'year' ? year : scale === 'quarter' ? `Q${Math.floor(month / 3) + 1}` : scale === 'week' ? `${date.getUTCDate()} ${months[month]}` : months[month];
    bands.push({ start: cursor, end, label });
    cursor = end;
  }
  return bands;
}
function axis(scale) {
  return axisBands(scale).map(band => {
    const short = scale === 'quarter' ? band.label : scale === 'week' ? Number(band.start.slice(8)) : String(band.label).slice(0, 1);
    return `<span title="${band.label}" style="left:${position(band.start)}%;width:${position(band.end) - position(band.start)}%"><span class="sw-axis-full">${band.label}</span><span class="sw-axis-short" aria-hidden="true">${short}</span></span>`;
  }).join('');
}
function gridLines(scale) {
  return axisBands(scale).map(band => `<i style="left:${position(band.start)}%"></i>`).join('');
}
function programmeFields(name, start, days, stage = false) {
  return `<div class="sw-programme-name" role="cell" title="${escape(name)}">${stage ? chevronIcon : ''}<span>${escape(name)}</span></div>
    <div class="sw-programme-date" role="cell">${calendarIcon}<time datetime="${start}">${date(start)}</time></div>
    <div class="sw-programme-days" role="cell">${days}</div>
    <div class="sw-programme-add" role="cell"><button type="button" disabled aria-label="Add activity after ${escape(name)} (preview)" title="Add activity (preview)">${plusIcon}</button></div>`;
}

function programmeLinks(labels = false) {
  const rows = programmeGroups.flatMap(group => [[group.id], ...group.rows]);
  return programmeDependencies.map(([from, to, lag = 0]) => {
    const source = rows.findIndex(row => row[0] === from), target = rows.findIndex(row => row[0] === to);
    const x1 = position(finish(rows[source])) * 10, x2 = position(rows[target][2]) * 10;
    const y1 = source * 24 + 12, y2 = target * 24 + 12;
    // Same finish-to-start elbow routing as programme.ts:ganttLinkPath.
    const sourceStub = x1 + 12, targetStub = x2 - 12;
    const trunk = sourceStub <= targetStub ? (sourceStub + targetStub) / 2 : Math.max(sourceStub, targetStub) + 12;
    if (labels) return lag ? `<span class="sw-gantt-lag is-linked" data-link-from="${from}" data-link-to="${to}" style="left:calc(var(--sw-schedule-width) + (100% - var(--sw-schedule-width)) * ${trunk / 1000});top:${(y1 + y2) / 2 - 8}px">+${lag}d</span>` : '';
    return `<g data-link-from="${from}" data-link-to="${to}" class="is-linked"><path pathLength="1" d="M${x1} ${y1} H${sourceStub} H${trunk} V${y2} H${targetStub} H${x2}"/></g>`;
  }).join('');
}
function programmeMarkup() {
  const rowCount = programmeGroups.reduce((count, group) => count + group.rows.length + 1, 0);
  return `<div class="sw-programme-chart" role="table" aria-label="Seven Hills Townhouse programme" aria-colcount="5" aria-rowcount="${rowCount + 1}">
    <div class="sw-gantt-axis" role="row"><div class="sw-programme-name" role="columnheader">${chevronIcon}<span data-column-heading="">Activity</span></div><div role="columnheader"><span data-column-heading="">Start</span></div><div class="sw-programme-days" role="columnheader"><span data-column-heading="">Days</span></div><div role="columnheader" aria-label="Add activity"></div><div class="sw-gantt-time-axis" role="columnheader" aria-label="Timeline"><div class="sw-gantt-years">${axis('year')}</div><div class="sw-gantt-ticks">${axis('month')}</div></div></div>
    <div class="sw-programme-body"><div class="sw-programme-gridlines" aria-hidden="true">${gridLines('month')}</div>
    ${programmeGroups.map(group => `<section class="sw-control-section sw-programme-stage is-filled" role="rowgroup" data-section="${group.id}" data-section-title="${group.title}">
      <div class="sw-stage-heading sw-gantt-row" role="row">${programmeFields(group.title, group.start, group.days, true)}<div class="sw-activity-track" role="cell"><span class="sw-stage-range" style="left:${position(group.start)}%;width:${position(addDays(group.start, group.days)) - position(group.start)}%"></span><i class="sw-thinking" aria-hidden="true"></i></div></div>
      <div class="sw-section-reveal"><div>${group.rows.map(row => `<div class="sw-gantt-row is-built" role="row" data-build-row="${row[0]}" data-start="${row[2]}" data-finish="${finish(row)}" data-duration="${duration(row)}"${row[0] === 'pc' ? ' data-final-reveal=""' : ''}>
        ${programmeFields(row[1], row[2], duration(row))}
        <div class="sw-activity-track" role="cell" aria-label="${escape(row[1])}: ${date(row[2])}${duration(row) ? ` to ${date(finish(row))}, ${duration(row)} days` : ', milestone'}"><span class="${duration(row) ? 'sw-gantt-bar' : 'sw-gantt-milestone'}" style="left:${position(row[2])}%;${duration(row) ? `width:${position(finish(row)) - position(row[2])}%` : ''}" title="${date(row[2])} – ${date(finish(row))}"></span></div>
      </div>`).join('')}</div></div>
    </section>`).join('')}
    <svg class="sw-gantt-links" viewBox="0 0 1000 ${rowCount * 24}" preserveAspectRatio="none" aria-hidden="true">${programmeLinks()}</svg>${programmeLinks(true)}
    </div></div>`;
}

export function installControlScenes(root) {
  const doc = root.ownerDocument;
  const original = root.querySelector('[data-plan-content]');
  original.dataset.sceneContent = 'pmp';
  const proposal = root.querySelector('[data-file="qs"]').cloneNode(true);
  proposal.dataset.file = 'services';
  proposal.dataset.sceneSource = 'cost';
  proposal.dataset.sourceTitle = 'Flux Services · Fee proposal FS-26028';
  proposal.dataset.sourceExcerpt = 'The 26 June 2025 proposal offers integrated hydraulic, electrical and mechanical design for $158,000 excluding GST. A proposal is subject to a written agreement; the appointment shown in the cost plan is separately recorded in the captured PMP.';
  proposal.querySelector('.sw-source').dataset.source = 'services';
  proposal.querySelector('.sw-source').textContent = 'Services fee';
  proposal.querySelector('.sw-repo-rev').textContent = '—';
  proposal.querySelector('.sw-repo-category').textContent = 'Electrical';
  proposal.querySelector('.sw-bin').setAttribute('aria-label', 'Remove services fee proposal (preview)');
  proposal.hidden = true;
  root.querySelector('[data-output]').before(proposal);
  const definitions = {
    cost: { label: 'Cost Plan', title: 'Cost plan', create: 'Build the cost plan from the project plan and received proposals.', update: 'Read the latest proposals and cost advice. Refresh the cost plan.', sources: ['pmp', 'brief', 'qs', 'services'], markup: costMarkup() },
    program: { label: 'Program', title: 'Program', create: 'Build the program from the project plan, linking design, approvals, procurement and construction.', update: 'Review the project plan and latest advice. Update the linked program.', sources: ['pmp', 'qs', 'planning', 'preda'], markup: programmeMarkup() },
    procurement: createProcurementScene(root),
  };
  for (const [key, definition] of Object.entries(definitions)) {
    const content = doc.createElement('div');
    content.dataset.planContent = '';
    content.dataset.sceneContent = key;
    if (key === 'program') content.dataset.scale = 'month';
    content.hidden = true;
    const actions = original.querySelector('.sw-pmp-actions').cloneNode(true);
    const create = actions.querySelector('[data-create-pmp]');
    const update = actions.querySelector('[data-update-pmp]');
    create.lastChild.textContent = definition.createLabel || (key === 'cost' ? 'Create cost plan' : 'Create program');
    update.lastChild.textContent = definition.updateLabel || (key === 'cost' ? 'Refresh cost plan' : 'Update program');
    const exports = original.querySelector('.sw-document-actions').cloneNode(true);
    exports.setAttribute('aria-label', `${definition.title} export preview`);
    for (const button of exports.querySelectorAll('button')) button.setAttribute('aria-label', button.getAttribute('aria-label').replace('project management plan', definition.title.toLowerCase()));
    content.innerHTML = original.querySelector('.sw-project-context').outerHTML + actions.outerHTML +
      `<div class="sw-document-head"><h2>${definition.title}</h2>${exports.outerHTML}</div>
      <div class="sw-document sw-control-document sw-${key}-document" data-document="" role="region" tabindex="0" aria-label="${definition.title}">
      ${key !== 'program' ? '' : '<div class="sw-programme-tools"><div role="group" aria-label="Program timescale"><button type="button" data-scale="week" aria-pressed="false">Week</button><button type="button" data-scale="month" aria-pressed="true">Month</button><button type="button" data-scale="quarter" aria-pressed="false">Quarter</button></div><button type="button" data-fit-program="">Fit to screen</button></div>'}
      ${definition.markup}</div>`;
    root.querySelector('.sw-console').before(content);
    definition.content = content;
    if (definition.output === false) continue;
    const output = root.querySelector('[data-output]').cloneNode(true);
    output.removeAttribute('data-output');
    output.dataset.sceneOutput = key;
    output.dataset.file = key;
    output.dataset.sourceTitle = `${definition.title} · v${key === 'cost' ? 9 : 1}`;
    output.dataset.sourceExcerpt = key === 'cost' ? 'Captured Cost Plan v9, August 2026. Fees and charges budget $96,500; consultants budget $225,500, including the recorded $158,000 Electrical contract. Budgets beyond the supplied capture are shown as a dash. Forecast final cost follows approved contracts and variations.' : 'Saved Seven Hills Townhouse programme from the supplied screenshot: 29 activities and milestones across Planning, Procurement and Delivery, including fire engineering. Dates and durations reproduce that saved state, including practical completion on 4 October 2026.';
    output.querySelector('.sw-repo-rev').textContent = key === 'cost' ? '9' : '1';
    const source = output.querySelector('.sw-source');
    source.removeAttribute('data-open-generated');
    source.dataset.source = key;
    source.textContent = definition.label;
    output.querySelector('.sw-repo-category').textContent = key === 'cost' ? 'Cost' : 'Program';
    output.querySelector('.sw-bin').setAttribute('aria-label', `Remove ${definition.title.toLowerCase()} (preview)`);
    output.hidden = true;
    root.querySelector('.sw-sources').append(output);
  }
  const navItems = [...root.querySelectorAll('.sw-nav-links .sw-nav-item')];
  for (const [index, key] of [[1, 'pmp'], [2, 'cost'], [3, 'program'], [4, 'procurement']]) {
    const button = doc.createElement('button');
    button.type = 'button';
    button.className = 'sw-nav-item sw-nav-scene';
    button.dataset.scene = key;
    button.innerHTML = navItems[index].innerHTML;
    if (key === 'pmp') button.setAttribute('aria-current', 'page');
    navItems[index].replaceWith(button);
  }
  const picker = doc.createElement('nav');
  picker.className = 'sw-scene-picker';
  picker.setAttribute('aria-label', 'Choose an animation');
  picker.innerHTML = '<button type="button" data-scene="pmp" aria-pressed="true">Project Plan</button><button type="button" data-scene="cost" aria-pressed="false">Cost Plan</button><button type="button" data-scene="program" aria-pressed="false">Program</button><button type="button" data-scene="procurement" aria-pressed="false">Procurement</button><button type="button" data-play-all="" aria-pressed="false">Play all</button>';
  root.querySelector('.sw-review-controls').prepend(picker);
  return definitions;
}

export function setProgrammeScale(content, scale) {
  content.dataset.scale = scale;
  content.querySelector('.sw-gantt-ticks').innerHTML = axis(scale);
  content.querySelector('.sw-gantt-years').innerHTML = axis(scale === 'week' ? 'month' : 'year');
  content.querySelector('.sw-programme-gridlines').innerHTML = gridLines(scale);
  content.querySelectorAll('[data-scale]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.scale === scale)));
}
