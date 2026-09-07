import { readFileSync } from 'node:fs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mountLandingDemo } from '../../public/landing-assets/landing-sequence.js';
import { costGroups, costRollup, costTotals, projectCostTotals, programmeGroups, programmeDependencies, duration, finish, dayNumber } from '../../public/landing-assets/landing-control-data.js';

const html = readFileSync('public/landing.html', 'utf8');
let root, cleanup, visibility, motionChange, preference;
const get = selector => root.querySelector(selector);
const content = key => get(`[data-scene-content="${key}"]`);
const built = key => content(key).querySelectorAll('[data-build-row].is-built').length;
const choose = key => get(`.sw-nav [data-scene="${key}"]`).click();
const promptText = () => get('[data-prompt-live]').textContent;
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance'] });
  document.body.innerHTML = new DOMParser().parseFromString(html, 'text/html').body.innerHTML;
  root = document.getElementById('sitewise-landing');
  preference = { matches: false, addEventListener: (_, fn) => { motionChange = fn; }, removeEventListener: vi.fn() };
  vi.stubGlobal('matchMedia', () => preference);
  vi.stubGlobal('IntersectionObserver', class {
    constructor(fn) { visibility = fn; }
    observe() {}
    disconnect() {}
  });
});
afterEach(() => { cleanup?.(); cleanup = undefined; vi.useRealTimers(); vi.unstubAllGlobals(); document.body.innerHTML = ''; });
function mount(options) { cleanup = mountLandingDemo(root, options); visibility([{ isIntersecting: true }]); }

describe('landing cost plan and program', () => {
  it('keeps the shells, starts blank and builds the cost groups before rows', () => {
    mount();
    const nav = get('.sw-nav'), repository = get('.sw-repository'), console = get('.sw-console');
    choose('cost');
    expect(get('.sw-nav')).toBe(nav); expect(get('.sw-repository')).toBe(repository); expect(get('.sw-console')).toBe(console);
    expect(content('pmp').hidden).toBe(true); expect(promptText()).toBe('');
    expect(content('cost').hasAttribute('inert')).toBe(true); expect(built('cost')).toBe(0);
    vi.advanceTimersByTime(2000);
    expect(promptText()).toBe('Build the cost plan from the project plan and received proposals.');
    expect(content('cost').hasAttribute('inert')).toBe(true);
    vi.advanceTimersByTime(3100);
    expect(content('cost').querySelectorAll('[data-heading-pending]')).toHaveLength(0);
    expect(built('cost')).toBe(0);
    vi.advanceTimersByTime(1800);
    expect(built('cost')).toBeGreaterThan(0); expect(built('cost')).toBeLessThan(26);
    get('[data-play]').click(); const progress = built('cost'); vi.advanceTimersByTime(5000); expect(built('cost')).toBe(progress);
    get('[data-play]').click(); vi.advanceTimersByTime(18000);
    expect(built('cost')).toBe(26); expect(get('[data-file="cost"]').hidden).toBe(false);
    expect(get('.sw-repo-row.is-active').dataset.file).toBe('cost');
    expect(content('cost').querySelector('tfoot [data-label="Forecast Final Cost"]').textContent).toBe('158,000.00'); expect(vi.getTimerCount()).toBe(0);
  });

  it('matches the captured register columns, codes, rows and two-decimal formatting', () => {
    mount(); choose('cost'); get('[data-show-result]').click();
    const table = content('cost').querySelector('.sw-cost-grid');
    expect(content('cost').querySelectorAll('table')).toHaveLength(1);
    expect([...table.querySelectorAll('thead th')].map(cell => cell.textContent)).toEqual([
      'Code', 'Category', 'Item', 'Budget', 'Approved Contract', 'Forecast Variations',
      'Approved Variations', 'Forecast Final Cost', 'Budget Variance', 'Claimed to Date', 'This Month', 'Remaining', '',
    ]);
    expect([...table.querySelectorAll('tr[data-build-row]')].filter(row => row.dataset.buildRow).map(row => row.dataset.buildRow)).toEqual([
      '1', '2', '3', '4', '5', '8', '9', '10', '11', '12', '13', '28', '14', '15', '16', '17', '18', '19', '20', '21', '22', '27',
    ]);
    const fees = table.querySelector('[data-build-row="1"]');
    expect([...fees.cells].slice(0, 9).map(cell => cell.textContent)).toEqual([
      '1', 'Fees and charges', 'Architect-PM architect / PM fee', '60,000.00', '0.00', '0.00', '0.00', '0.00', '60,000.00',
    ]);
    expect(table.querySelector('[data-build-row="14"] [data-label="Budget"]').textContent).toBe('970,500.00');
    expect(content('cost').querySelector('.sw-cost-month').textContent).toBe('August 2026');
    expect(content('cost').querySelector('.sw-cost-tab-list [aria-current]').textContent).toBe('Cost Plan v9');
    expect(table.querySelector('.sw-cost-subtotal').cells[1].colSpan).toBe(2);
    expect(table.querySelector('[data-build-row="21"] [data-label="Budget"]').textContent).toBe('—');
  });

  it('uses the app rollups and preserves unknown budgets without inventing totals', () => {
    const totals = costGroups.map(costTotals);
    expect(totals[0].budget).toBe(96500);
    expect(totals[1]).toEqual({ budget: 225500, approved: 158000, forecastVariations: 0, approvedVariations: 0, forecast: 158000, variance: 67500, claimed: 0, thisMonth: 0, remaining: 225500 });
    expect(projectCostTotals.forecast).toBe(158000);
    expect(projectCostTotals.budget).toBeNull();
    expect(projectCostTotals.variance).toBeNull();
    expect(projectCostTotals.remaining).toBeNull();
    expect(costRollup([1, 'Example', 100000, 60000, 5000, 2000, 10000, 3000])).toEqual({
      budget: 100000, approved: 60000, forecastVariations: 5000, approvedVariations: 2000,
      forecast: 67000, variance: 33000, claimed: 10000, thisMonth: 3000, remaining: 90000,
    });
  });

  it('builds dated activities and links across Planning, Procurement and Delivery', () => {
    mount(); choose('program');
    expect(promptText()).toBe(''); expect(built('program')).toBe(0);
    vi.advanceTimersByTime(5400);
    expect(content('program').querySelectorAll('[data-heading-pending]')).toHaveLength(0);
    expect(built('program')).toBe(0);
    vi.advanceTimersByTime(3000);
    expect(built('program')).toBeGreaterThan(0); expect(built('program')).toBeLessThan(29);
    expect(content('program').querySelectorAll('.is-linked').length).toBeGreaterThan(0);
    vi.advanceTimersByTime(17000);
    expect(built('program')).toBe(29); expect(content('program').querySelectorAll('[data-link-to]:not(.is-linked)')).toHaveLength(0);
    expect(get('[data-build-row="da-approval"]').dataset.start).toBe('2025-09-17');
    expect(get('[data-build-row="start"]').dataset.start).toBe('2026-04-13');
    expect(get('[data-build-row="pc"]').dataset.finish).toBe('2026-10-04');
    expect(get('[data-build-row="fire-authority"]').dataset.duration).toBe('55');
    expect(get('[data-link-from="da-approval"][data-link-to="earthworks"]')).not.toBeNull();
    expect(get('[data-link-from="mobilise"][data-link-to="site"]')).not.toBeNull();
    expect(vi.getTimerCount()).toBe(0);
    const rows = programmeGroups.flatMap(group => group.rows);
    for (const row of rows) {
      expect(duration(row)).toBeGreaterThanOrEqual(0);
    }
    for (const [from, to, lag = 0] of programmeDependencies) {
      const predecessor = rows.find(candidate => candidate[0] === from);
      const successor = rows.find(candidate => candidate[0] === to);
      expect(dayNumber(successor[2])).toBeGreaterThanOrEqual(dayNumber(finish(predecessor)) + lag);
    }
  });

  it('reproduces the attached programme fields, saved dates, durations and row order', () => {
    mount(); choose('program'); get('[data-show-result]').click();
    expect([...content('program').querySelectorAll('.sw-gantt-axis [role="columnheader"]')].map(cell => cell.getAttribute('aria-label') || cell.textContent)).toEqual(['Activity', 'Start', 'Days', 'Add activity', 'Timeline']);
    const rows = [...content('program').querySelectorAll('[data-build-row]')];
    expect(rows.map(row => [row.dataset.start, Number(row.dataset.duration)])).toEqual([
      ['2025-02-10', 47], ['2025-03-29', 52], ['2025-05-25', 30], ['2025-06-24', 85],
      ['2025-03-29', 0], ['2025-04-09', 0], ['2025-09-17', 0], ['2025-02-10', 46],
      ['2025-02-10', 109], ['2025-05-30', 41], ['2025-07-10', 55], ['2025-02-10', 0],
      ['2025-02-01', 56], ['2025-03-29', 29], ['2025-04-27', 28], ['2025-05-25', 24],
      ['2025-04-24', 0], ['2025-06-19', 0], ['2025-06-18', 14], ['2025-09-17', 35],
      ['2025-10-22', 42], ['2025-12-03', 105], ['2026-03-18', 56], ['2026-05-13', 42],
      ['2026-06-24', 105], ['2026-06-24', 95], ['2026-10-07', 25], ['2026-04-13', 0], ['2026-10-04', 0],
    ]);
    expect([...content('program').querySelectorAll('.sw-stage-heading .sw-programme-days')].map(cell => cell.textContent)).toEqual(['219', '138', '501']);
    expect(rows.every(row => row.querySelectorAll('[role="cell"]').length === 5)).toBe(true);
    expect(content('program').querySelectorAll('.sw-gantt-milestone')).toHaveLength(8);
    expect(content('program').querySelector('.sw-gantt-links').getAttribute('viewBox')).toBe('0 0 1000 768');
    expect(content('program').querySelector('.sw-gantt-lag[data-link-from="concept"]').textContent).toBe('+5d');
  });

  it('cancels earlier work when switching or replaying a scene', () => {
    mount(); choose('cost'); vi.advanceTimersByTime(7000); const costRows = built('cost');
    choose('program'); expect(promptText()).toBe('');
    vi.advanceTimersByTime(5000); expect(built('cost')).toBe(costRows);
    expect(get('[data-file="program"]').hidden).toBe(true); expect(vi.getTimerCount()).toBe(1);
    get('[data-show-result]').click(); expect(built('program')).toBe(29); expect(vi.getTimerCount()).toBe(0);
    get('[data-send]').click(); expect(built('program')).toBe(0); expect(promptText()).toBe('');
    cleanup(); cleanup = undefined; vi.advanceTimersByTime(40000); expect(built('program')).toBe(0); expect(vi.getTimerCount()).toBe(0);
  });

  it('loops all three scenes with a readable hold, and lets manual selection stop the cycle', () => {
    mount({ playAll: true }); vi.advanceTimersByTime(13000);
    expect(root.dataset.activeScene).toBe('pmp'); expect(get('[data-document]').getAttribute('aria-busy')).toBe('false');
    vi.advanceTimersByTime(6000); expect(root.dataset.activeScene).toBe('pmp');
    vi.advanceTimersByTime(1000); expect(root.dataset.activeScene).toBe('cost');
    vi.advanceTimersByTime(25000); expect(root.dataset.activeScene).toBe('program');
    vi.advanceTimersByTime(26000); expect(root.dataset.activeScene).toBe('pmp'); expect(vi.getTimerCount()).toBe(1);
    choose('cost'); expect(get('[data-play-all]').getAttribute('aria-pressed')).toBe('false');
    vi.advanceTimersByTime(50000); expect(root.dataset.activeScene).toBe('cost'); expect(vi.getTimerCount()).toBe(0);
  });

  it('pauses when offscreen or manually inspected and offers reduced-motion results for every scene', () => {
    mount(); choose('program'); vi.advanceTimersByTime(7300); visibility([{ isIntersecting: false }]);
    const progress = built('program'); vi.advanceTimersByTime(10000); expect(built('program')).toBe(progress);
    visibility([{ isIntersecting: true }]); vi.advanceTimersByTime(1000); expect(built('program')).toBeGreaterThan(progress);
    content('program').querySelector('[data-document]').dispatchEvent(new Event('wheel', { bubbles: true }));
    const stopped = built('program'); vi.advanceTimersByTime(6000); expect(built('program')).toBe(stopped);
    preference.matches = true; motionChange(); expect(built('program')).toBe(29); expect(vi.getTimerCount()).toBe(0);
    choose('cost'); expect(built('cost')).toBe(26); expect(content('cost').hasAttribute('inert')).toBe(false); expect(vi.getTimerCount()).toBe(0);
  });

  it('switches the program timescale and fits it without editing the project dates', () => {
    mount(); choose('program'); get('[data-show-result]').click();
    const dates = [...content('program').querySelectorAll('[data-start]')].map(row => row.dataset.start);
    expect(content('program').dataset.scale).toBe('month');
    expect(get('.sw-gantt-ticks').textContent).toContain('Feb');
    get('[data-scale="quarter"]').click(); expect(content('program').dataset.scale).toBe('quarter'); expect(get('.sw-gantt-ticks').textContent).toContain('Q1');
    expect(get('.sw-gantt-ticks .sw-axis-short').textContent).toBe('Q1');
    get('[data-fit-program]').click(); expect(content('program').dataset.scale).toBe('quarter');
    get('[data-scale="week"]').click(); expect(content('program').dataset.scale).toBe('week'); expect(get('.sw-gantt-ticks').textContent).toContain('1 Feb');
    get('[data-scale="month"]').click(); expect(content('program').dataset.scale).toBe('month');
    expect([...content('program').querySelectorAll('[data-start]')].map(row => row.dataset.start)).toEqual(dates);
  });
});
