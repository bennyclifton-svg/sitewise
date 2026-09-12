import { readFileSync } from 'node:fs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mountLandingDemo } from '../../public/landing-assets/landing-sequence.js';

const html = readFileSync('public/landing.html', 'utf8');
const civilMarkdown = readFileSync('public/landing-assets/civil-stormwater-rfp.md', 'utf8');
let root, cleanup, visibility, preference;
const get = selector => root.querySelector(selector);
const scene = () => get('[data-scene-content="procurement"]');
const civil = () => get('[data-rfp="civil-stormwater"]');
const select = key => get(`.sw-nav [data-scene="${key}"]`).click();
const ready = () => scene().querySelectorAll('.sw-rfp-open:not([disabled])').length;
function mount(reduced = false) {
  preference.matches = reduced; cleanup = mountLandingDemo(root); visibility([{ isIntersecting: true }]); select('procurement');
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance'] });
  document.body.innerHTML = new DOMParser().parseFromString(html, 'text/html').body.innerHTML;
  root = document.getElementById('sitewise-landing');
  preference = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() };
  vi.stubGlobal('matchMedia', () => preference);
  vi.stubGlobal('IntersectionObserver', class { constructor(fn) { visibility = fn; } observe() {} disconnect() {} });
});
afterEach(() => { cleanup?.(); cleanup = undefined; vi.useRealTimers(); vi.unstubAllGlobals(); document.body.innerHTML = ''; });

describe('consultant procurement animation', () => {
  it('holds a blank scene while typing, accumulates sources, then builds the real register and drafts', () => {
    const nav = get('.sw-nav'), console = get('.sw-console'), repository = get('.sw-repository');
    mount();
    expect(get('.sw-nav')).toBe(nav); expect(get('.sw-console')).toBe(console); expect(get('.sw-repository')).toBe(repository);
    expect(get('[data-prompt-live]').textContent).toBe(''); expect(scene().hasAttribute('inert')).toBe(true);
    vi.advanceTimersByTime(2500);
    expect(get('[data-prompt-live]').textContent).toBe('Draft consultant RFPs from the project plan, with scopes, deliverables and submission requirements.');
    expect(scene().hasAttribute('inert')).toBe(true);
    vi.advanceTimersByTime(4200);
    expect(root.querySelectorAll('.sw-repo-row.is-active').length).toBeGreaterThan(3);
    expect(scene().querySelectorAll('[data-build-row].is-built')).toHaveLength(0);
    expect(ready()).toBe(0);
    vi.advanceTimersByTime(5800);
    expect(scene().querySelectorAll('[data-build-row].is-built')).toHaveLength(6);
    expect(ready()).toBeGreaterThan(0); expect(ready()).toBeLessThan(4);
    expect([...scene().querySelectorAll('thead th')].slice(0, 6).map(cell => cell.textContent)).toEqual(['Discipline', 'Firm 1', 'Firm 2', 'Firm 3', 'Status', '']);
    vi.advanceTimersByTime(5000);
    expect(ready()).toBe(4); expect(scene().querySelector('[data-procurement-reader]').hidden).toBe(false);
    expect(root.querySelectorAll('.sw-repo-row.is-active')).toHaveLength(0);
    expect(civil().querySelectorAll('.sw-rfp-section.is-filled').length).toBeLessThan(8);
    get('[data-play]').click(); const progress = civil().querySelectorAll('.is-built').length;
    vi.advanceTimersByTime(6000); expect(civil().querySelectorAll('.is-built').length).toBe(progress);
    get('[data-play]').click(); vi.advanceTimersByTime(25000);
    expect(civil().querySelectorAll('.sw-rfp-section.is-filled')).toHaveLength(8);
    expect(civil().querySelectorAll('.sw-rfp-block:not(.is-built)')).toHaveLength(0);
    expect(get('[data-file="procurement"]').hidden).toBe(false);
    expect(get('[data-status]').textContent).toContain('No requests have been issued');
    expect(scene().querySelectorAll('.sw-status-segments[aria-label="Not issued"]')).toHaveLength(6);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('preserves the captured civil scope, fee stages, programme snapshot and source key', () => {
    mount(true);
    const normalise = value => value.replace(/\s+/g, ' ').trim();
    const scope = civilMarkdown.split('## Services and deliverables')[1].split('## Programme')[0];
    const clauses = scope.split('\n').filter(line => /^\d+\. /.test(line)).map(line => normalise(line.replace(/^\d+\. /, '')));
    const rendered = [...civil().querySelectorAll('[data-section-title="Services and deliverables"] li')].map(item => normalise(item.textContent));
    expect(rendered).toEqual(clauses);
    expect(rendered[2]).toContain('adopt, revise or supersede the existing below-ground OSD tank');
    expect(rendered[6]).toContain('exclude structural design of the OSD tank');
    expect(civil().textContent).toContain('Current Programme v73 — static snapshot');
    expect(civil().textContent).toContain('30 April 2027');
    expect(civil().querySelector('[data-section-title="Fee response"] tbody').rows).toHaveLength(10);
    expect(civil().querySelector('[data-section-title="Transmittal (3 documents)"] tbody').rows).toHaveLength(3);
    expect(civil().textContent).not.toContain('clerk:block'); expect(civil().textContent).not.toContain('Trace & QA');
    const citations = [...civil().querySelector('[data-section-title="Citation key"]').querySelectorAll('li')].map(item => item.textContent);
    expect(citations).toHaveLength(8);
    for (const citation of civil().querySelectorAll('[data-rfp-cite]')) expect(citations.some(item => item.startsWith(`[${citation.dataset.rfpCite}]`))).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('opens saved drafts and their citation key, returns to the register and resets all output on replay', () => {
    mount(); get('[data-show-result]').click();
    scene().querySelector('[data-back-procurement]').click();
    expect(scene().querySelector('[data-procurement-register]').hidden).toBe(false);
    const architect = scene().querySelector('[data-open-rfp="architect"]'); architect.click();
    expect(get('[data-rfp="architect"]').hidden).toBe(false); expect(civil().hidden).toBe(true);
    get('[data-rfp="architect"] [data-rfp-cite="3"]').click();
    expect(document.activeElement.dataset.sectionTitle).toBe('Citation key');
    get('[data-file="procurement"] button').click(); expect(civil().hidden).toBe(false);
    scene().querySelector('[data-back-procurement]').click();
    expect(document.activeElement.dataset.openRfp).toBe('civil-stormwater');
    get('[data-send]').click();
    expect(ready()).toBe(0); expect(get('[data-file="procurement"]').hidden).toBe(true);
    expect(scene().querySelector('[data-procurement-reader]').hidden).toBe(true);
    vi.advanceTimersByTime(13000); const count = ready(); select('program');
    vi.advanceTimersByTime(25000); expect(ready()).toBe(count);
    expect(root.querySelectorAll('[data-procurement-file]:not([hidden])')).toHaveLength(0);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('pauses offscreen and exposes the full draft without animation for reduced motion', () => {
    mount(); vi.advanceTimersByTime(10000); visibility([{ isIntersecting: false }]);
    const progress = scene().querySelectorAll('.is-built').length;
    vi.advanceTimersByTime(40000); expect(scene().querySelectorAll('.is-built').length).toBe(progress);
    visibility([{ isIntersecting: true }]); vi.advanceTimersByTime(40000); expect(ready()).toBe(4);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('copies and downloads the captured Markdown rather than the animated DOM', async () => {
    mount(true);
    const writeText = vi.fn().mockResolvedValue(undefined);
    const fetch = vi.fn().mockResolvedValue({ ok: true, text: async () => civilMarkdown });
    vi.stubGlobal('fetch', fetch);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    scene().querySelector('[data-copy-rfp]').click();
    await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith(civilMarkdown));
    expect(String(fetch.mock.calls[0][0])).toMatch(/civil-stormwater-rfp\.md$/);
    expect(get('[data-status]').textContent).toBe('RFP copied.');
    let download;
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { download = [this.href, this.download]; });
    scene().querySelector('[data-download-rfp]').click();
    expect(download[0]).toMatch(/civil-stormwater-rfp\.md$/);
    expect(download[1]).toBe('Seven-Hills-civil-stormwater-RFP-v1.md');
    click.mockRestore();
  });
});
