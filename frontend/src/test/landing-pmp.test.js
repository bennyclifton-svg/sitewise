import {readFileSync} from 'node:fs';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {mountLandingDemo} from '../../public/landing-assets/landing-sequence.js';

const html=readFileSync('public/landing.html','utf8');
let root, cleanup, onVisibility, onMotion, preference;
const get=selector=>root.querySelector(selector);
const active=()=>get('.sw-repo-row.is-active')?.dataset.file;
const selected=()=>[...root.querySelectorAll('.sw-repo-row.is-active')].map(row=>row.dataset.file);
const filled=()=>root.querySelectorAll('.sw-pmp-section.is-filled').length;
const visibleHeadings=()=>[...root.querySelectorAll('.sw-pmp-section:not([data-heading-pending]) .sw-section-title')].map(heading=>heading.textContent);

beforeEach(()=>{
  vi.useFakeTimers({toFake:['setTimeout','clearTimeout','performance']});
  document.body.innerHTML=new DOMParser().parseFromString(html,'text/html').body.innerHTML;
  root=document.getElementById('sitewise-landing');
  preference={matches:false,addEventListener:(_,fn)=>{onMotion=fn;},removeEventListener:vi.fn()};
  vi.stubGlobal('matchMedia',()=>preference);
  vi.stubGlobal('IntersectionObserver',class{
    constructor(fn){onVisibility=fn;}
    observe(){}
    disconnect(){}
  });
});
afterEach(()=>{cleanup?.();cleanup=undefined;vi.useRealTimers();vi.unstubAllGlobals();document.body.innerHTML='';});

function mount(visible=true){cleanup=mountLandingDemo(root);onVisibility([{isIntersecting:visible}]);}

describe('landing PMP demonstration',()=>{
  it('leaves a readable completed plan when JavaScript does not run',()=>{
    expect(filled()).toBe(12);
    expect(visibleHeadings()).toHaveLength(12);
    expect(get('[data-output]').hidden).toBe(false);
    expect(get('[data-prompt-live]').textContent).toContain('Draft the project management plan.');
  });

  it('introduces headings in order, preserves progress while paused and reveals all when skipped',()=>{
    mount();
    expect(visibleHeadings()).toEqual([]);
    vi.advanceTimersByTime(3700);
    expect(visibleHeadings()).toEqual(['Project Summary']);
    expect(get('[data-section="brief"]').hasAttribute('inert')).toBe(true);
    vi.advanceTimersByTime(220);
    expect(visibleHeadings()).toEqual(['Project Summary','Brief']);
    expect(filled()).toBe(0);
    get('[data-play]').click();vi.advanceTimersByTime(5000);
    expect(visibleHeadings()).toEqual(['Project Summary','Brief']);
    get('[data-play]').click();vi.advanceTimersByTime(220);
    expect(visibleHeadings()).toEqual(['Project Summary','Brief','Consultants']);
    get('[data-show-result]').click();
    expect(visibleHeadings()).toHaveLength(12);
    expect(root.querySelectorAll('.sw-pmp-section[inert]')).toHaveLength(0);
    get('[data-send]').click();
    expect(visibleHeadings()).toEqual([]);
  });

  it('accumulates each read source through generation, then clears sources and selects the finished plan',()=>{
    mount();
    const first=get('.sw-pmp-section');
    expect(filled()).toBe(0);
    expect(get('[data-plan-content]').getAttribute('aria-hidden')).toBe('true');
    expect(root.hasAttribute('data-prompt-typing')).toBe(true);
    expect(get('[data-output]').hidden).toBe(true);
    vi.advanceTimersByTime(1000);
    expect(get('[data-prompt-live]').textContent.length).toBeGreaterThan(0);
    expect(get('[data-plan-content]').hasAttribute('inert')).toBe(true);
    vi.advanceTimersByTime(1000);
    expect(get('[data-prompt-live]').textContent).toBe('Read the project profile and consultant reports. Draft the project management plan.');
    expect(root.hasAttribute('data-prompt-typing')).toBe(true);
    expect(active()).toBeUndefined();
    vi.advanceTimersByTime(1600);
    expect(get('[data-plan-content]').hasAttribute('inert')).toBe(true);
    vi.advanceTimersByTime(400);
    expect(selected()).toHaveLength(1);
    expect(root.hasAttribute('data-prompt-typing')).toBe(false);
    expect(get('[data-plan-content]').hasAttribute('inert')).toBe(false);
    let previous=selected();
    for(let count=2;count<=8;count++){
      vi.advanceTimersByTime(550);
      expect(selected()).toHaveLength(count);
      expect(selected()).toEqual(expect.arrayContaining(previous));
      previous=selected();
      expect(filled()).toBe(0);
    }
    expect([...selected()].sort()).toEqual(['brief','dp','ground','handover','planning','preda','qs','title']);
    expect(visibleHeadings()).toHaveLength(12);
    expect(root.querySelectorAll('.sw-source[aria-pressed="true"]')).toHaveLength(8);
    vi.advanceTimersByTime(1000);
    expect(filled()).toBeGreaterThan(0);
    expect(filled()).toBeLessThan(12);
    expect(get('.sw-pmp-section')).toBe(first);
    expect(selected()).toHaveLength(8);
    vi.advanceTimersByTime(6000);
    expect(filled()).toBe(12);
    expect(get('[data-output]').hidden).toBe(false);
    expect(get('[data-output]').parentElement).toBe(get('.sw-sources'));
    expect(selected()).toEqual(['pmp']);
    expect(root.querySelectorAll('.sw-source[aria-pressed="true"]')).toHaveLength(1);
    expect(get('[data-document]').getAttribute('aria-busy')).toBe('false');
    expect(vi.getTimerCount()).toBe(0);
  });

  it('pauses and resumes without duplicating the sequence',()=>{
    mount();vi.advanceTimersByTime(4100);
    const firstSelection=selected();
    get('[data-play]').click();
    vi.advanceTimersByTime(10000);
    expect(selected()).toEqual(firstSelection);expect(filled()).toBe(0);
    get('[data-play]').click();vi.advanceTimersByTime(600);
    expect(selected()).toHaveLength(2);expect(selected()).toEqual(expect.arrayContaining(firstSelection));
    vi.advanceTimersByTime(12000);expect(filled()).toBe(12);expect(vi.getTimerCount()).toBe(0);
    get('[data-send]').click();expect(filled()).toBe(0);
    expect(selected()).toEqual([]);
    vi.advanceTimersByTime(13000);expect(filled()).toBe(12);
  });

  it('suspends offscreen and preserves a manually selected source on return',()=>{
    mount();vi.advanceTimersByTime(4000);onVisibility([{isIntersecting:false}]);
    const firstSelection=selected();
    vi.advanceTimersByTime(10000);expect(selected()).toEqual(firstSelection);
    onVisibility([{isIntersecting:true}]);vi.advanceTimersByTime(550);
    expect(selected()).toHaveLength(2);expect(selected()).toEqual(expect.arrayContaining(firstSelection));
    get('[data-show-result]').click();get('[data-cite="ground"]').click();
    expect(active()).toBe('ground');expect(get('[data-excerpt]').textContent).toContain('intrusive investigation');
    onVisibility([{isIntersecting:false}]);onVisibility([{isIntersecting:true}]);
    vi.advanceTimersByTime(10000);expect(active()).toBe('ground');expect(vi.getTimerCount()).toBe(0);
  });

  it('shows the complete result for reduced motion, including preference changes during playback',()=>{
    mount();vi.advanceTimersByTime(2000);
    preference.matches=true;onMotion();
    expect(filled()).toBe(12);expect(vi.getTimerCount()).toBe(0);
    expect(get('[data-plan-content]').hasAttribute('inert')).toBe(false);
    expect(visibleHeadings()).toHaveLength(12);
    get('[data-send]').click();expect(filled()).toBe(12);expect(vi.getTimerCount()).toBe(0);
  });

  it('cancels an old run when showing the result and when unmounted',()=>{
    mount();vi.advanceTimersByTime(1000);get('[data-show-result]').click();
    vi.advanceTimersByTime(12000);expect(active()).toBe('pmp');expect(filled()).toBe(12);
    get('[data-send]').click();expect(vi.getTimerCount()).toBe(1);
    cleanup();cleanup=undefined;vi.advanceTimersByTime(10000);expect(filled()).toBe(0);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('uses the captured FFE and consultant records, with every citation pointing to a listed source',()=>{
    expect(root.querySelectorAll('[data-section="ffe-schedule"] tbody tr')).toHaveLength(8);
    expect(root.querySelectorAll('[data-section="consultants"] tbody tr')).toHaveLength(20);
    expect(get('[data-section="consultants"]').textContent).toContain('Flux Services');
    expect(get('[data-section="consultants"]').textContent).toContain('$158,000 ex GST');
    expect(get('[data-section="risks-and-mitigations"] table')).not.toBeNull();
    for(const cite of root.querySelectorAll('[data-cite]'))expect(get(`[data-file="${cite.dataset.cite}"]`)).not.toBeNull();
    expect(get('[data-cite="qs"]').textContent).toBe('[1]');
    expect(get('[data-cite="brief"]').textContent).toBe('[2]');
    expect(get('.sw-project-head')).toBeNull();
    expect(get('.sw-project-context').textContent).toContain('14–18 Wianamatta Avenue, Seven Hills NSW 2147');
  });

  it('supports Create PMP and Update PMP without changing the underlying project records',()=>{
    mount();get('[data-show-result]').click();
    expect(get('[data-update-pmp]').disabled).toBe(false);
    get('[data-update-pmp]').click();
    expect(filled()).toBe(0);expect(root.hasAttribute('data-prompt-typing')).toBe(true);
    vi.advanceTimersByTime(13000);
    expect(get('[data-prompt-live]').textContent).toBe('Read the latest project documents. Update the project management plan.');
    expect(filled()).toBe(12);
    get('[data-create-pmp]').click();vi.advanceTimersByTime(13000);
    expect(get('[data-prompt-live]').textContent).toContain('Read the project profile');
    expect(filled()).toBe(12);expect(vi.getTimerCount()).toBe(0);
  });
});
