import { beforeAll, beforeEach, afterAll, describe, expect, it, vi } from 'vitest';

let mountExperience;
const preference = new EventTarget();
preference.matches = false;
const fixture = () => {
  document.body.innerHTML = '<figure class="sw-coordination-plan"><button data-map-focus>Find the project</button><button data-map-pause></button><p data-map-status role="status"></p></figure>';
  return document.querySelector('figure');
};
const parcel = {area_m2:600,rings:[[[60,130],[80,130],[80,160],[60,160],[60,130]]]};

beforeAll(async () => {
  vi.stubGlobal('matchMedia', () => preference);
  vi.stubGlobal('IntersectionObserver', class { observe() {} disconnect() {} });
  ({mountExperience} = await import('../../public/landing-assets/landing-experience.js'));
});
beforeEach(() => {
  preference.matches=false;
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({parcels:[parcel]})}));
});
afterAll(() => {vi.unstubAllGlobals();document.body.innerHTML='';});

describe('interactive landing map', () => {
  it('provides keyboard parcel selection and connects the project action to the model', async () => {
    const plan=fixture();await mountExperience(plan);
    const onFocus=vi.fn();window.addEventListener('sitewise:project-focus',onFocus,{once:true});
    const svg=plan.querySelector('svg');
    svg.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
    expect(plan.querySelector('[data-map-status]').textContent).toContain('600 m²');
    expect(plan.querySelectorAll('.is-selected')).toHaveLength(1);
    plan.querySelector('[data-map-focus]').click();
    expect(onFocus).toHaveBeenCalledOnce();
  });

  it('mounts the map without the removed hero controls', async () => {
    const plan = fixture();
    plan.replaceChildren();
    await mountExperience(plan);
    expect(plan.querySelector('.sw-estate')).not.toBeNull();
  });

  it('starts paused with reduced motion and removes contours', async () => {
    preference.matches=true;
    const plan=fixture();await mountExperience(plan);
    expect(plan.classList.contains('is-paused')).toBe(true);
    expect(plan.querySelector('[data-map-pause]').getAttribute('aria-pressed')).toBe('true');
    expect(plan.querySelector('.sw-contours')).toBeNull();
    expect(plan.querySelector('.sw-pulse')).toBeNull();
    expect(plan.querySelector('.sw-field-particle')).toBeNull();
    expect(plan.querySelector('.sw-estate')).not.toBeNull();
    expect(plan.querySelector('[data-map-pause]').textContent).toBe('Replay map');
  });

  it('does not select a lot on model changes and clears a manual selection with Escape', async () => {
    const plan=fixture();await mountExperience(plan);
    window.dispatchEvent(new CustomEvent('sitewise:system',{detail:{label:'Architecture',color:'#fff'}}));
    expect(plan.querySelector('.is-selected')).toBeNull();
    const svg=plan.querySelector('svg');
    svg.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
    expect(plan.querySelector('.is-selected')).not.toBeNull();
    svg.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    expect(plan.querySelector('.is-selected')).toBeNull();
  });

  it('leaves the static plan available and disables project focus when interactive data fails', async () => {
    fetch.mockResolvedValue({ok:false});
    const plan=fixture();await mountExperience(plan);
    expect(plan.querySelector('[data-map-focus]').disabled).toBe(true);
    expect(plan.querySelector('[data-map-status]').textContent).toContain('Showing the cadastral plan');
    expect(plan.querySelector('svg')).toBeNull();
  });
});
