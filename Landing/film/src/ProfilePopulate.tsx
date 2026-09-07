import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  Easing,
  Img,
  interpolate,
  random,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

/**
 * Profile page being filled in by the agent.
 *
 * Source is public/profile-full.png — "1.1 Profile A" and "B" aligned at
 * dx=7, dy=406. All coordinates are in that screenshot's 1311x1106 space.
 *
 * The identity fields (name, address, client, state, budget, scale) are simply
 * present. Only the decisions animate, because the point of the shot is that
 * the agent is choosing, not typing:
 *
 *  1. CLASS, WORK TYPE, SUBCLASS — the highlight races through every option
 *     twice before settling, so the viewer sees the size of the choice. Each
 *     then lifts off big, hovers, and scatters off in its own direction.
 *  2. COMPLEXITY — each dropdown riffles through real alternatives and lands.
 *     No lift-off; ten fields flying at once was the clutter.
 *  3. SCOPE — 39 ticks fly in and land in their boxes.
 *
 * Option lists are the real ones from data/taxonomy/complexity-dimensions.json,
 * not invented.
 */

const PAGE_W = 1311;
const PAGE_H = 1106;

const INPUT_FILL = '#FEFCF5';
const CHIP_FILL = '#F8F5ED';
const CHIP_BORDER = '#E8E6E3';
const INK = '#2C2A2A';
const BLUE = '#4184F2';
const BLUE_TINT = 'rgba(65,132,242,0.13)';
const CHECK_BLUE = '#0075FC';
const BOX_BORDER = '#828383';
const BOX_FILL = '#FBFBFB';

type Rect = {x: number; y: number; w: number; h: number};

// ---- the three decision groups -------------------------------------------

const CLASS_CHIPS: {label: string; r: Rect}[] = [
  {label: 'Residential', r: {x: 29, y: 240, w: 412, h: 33}},
  {label: 'Commercial', r: {x: 450, y: 240, w: 412, h: 33}},
  {label: 'Industrial', r: {x: 869, y: 240, w: 412, h: 33}},
  {label: 'Institution', r: {x: 29, y: 278, w: 412, h: 33}},
  {label: 'Mixed use', r: {x: 450, y: 278, w: 412, h: 33}},
  {label: 'Infrastructure', r: {x: 869, y: 278, w: 412, h: 33}},
];

const WORK_CHIPS: {label: string; r: Rect}[] = [
  {label: 'New build', r: {x: 29, y: 344, w: 88, h: 31}},
  {label: 'Refurbishment', r: {x: 125, y: 344, w: 96, h: 31}},
  {label: 'Extension / addition', r: {x: 229, y: 344, w: 136, h: 31}},
  {label: 'Remediation / rectification', r: {x: 373, y: 344, w: 170, h: 31}},
  {label: 'Advisory services', r: {x: 551, y: 344, w: 122, h: 31}},
];

/** Radio centres detected at x=45; box sits 6px above each. */
const SUBCLASS_Y = [442, 466, 489, 512, 536, 559, 582, 606, 629];
const SUBCLASS_PICK = 2; // Townhouses (Class 1a)

// ---- complexity, from data/taxonomy/complexity-dimensions.json ------------

type Dim = {x: number; y: number; options: string[]; pick: number};

const COMPLEXITY: Dim[] = [
  {x: 680, y: 452, pick: 2, options: ['Exempt', 'CDC', 'DA', 'State Significant Development (SSD)']},
  {x: 984, y: 452, pick: 1, options: ['Traditional (Lump Sum)', 'Design & Construct', 'Early Contractor Involvement', 'Managing Contractor', 'Alliance (+5-10%)', 'PPP']},
  {x: 680, y: 503, pick: 0, options: ['Nil/Clean Site', 'Minor (Spot Treatment)', 'Significant (+10-20%)', 'Heavily Contaminated (+30-50%)']},
  {x: 984, y: 503, pick: 1, options: ['Unrestricted Access', 'Urban/Constrained', 'Restricted Hours', 'Remote Site (+15-30%)']},
  {x: 680, y: 553, pick: 0, options: ['Vacant/Unoccupied', 'Partial Occupation', 'Live Environment (+10-20%)', '24/7 Occupied (+20-30%)']},
  {x: 984, y: 553, pick: 0, options: ['Single Owner', 'Strata Ownership', 'Government Client', 'Multiple Agencies (+10-20%)']},
  {x: 680, y: 603, pick: 1, options: ['Standard', 'Environmentally Sensitive', 'Protected Habitat (+20%)', 'Aboriginal Heritage (+15%)']},
  {x: 984, y: 603, pick: 0, options: ['Not Bushfire Prone', 'Bushfire Prone - BAL-LOW', 'BAL-12.5 (+2-4%)', 'BAL-19 (+4-7%)', 'BAL-29 (+7-12%)']},
  {x: 680, y: 654, pick: 1, options: ['Not Flood Prone', 'Above Flood Planning Level', 'Within Flood Planning Area (+5-10%)', 'Below 1% AEP Flood Level (+10-20%)']},
  {x: 984, y: 654, pick: 1, options: ['None', 'Heritage conservation area', 'Local heritage item', 'State Heritage Register']},
];

const CHECKBOXES: [number, number][] = [
  [50, 744], [50, 773], [50, 794], [50, 836], [50, 878],
  [227, 744], [227, 773], [227, 794], [227, 815], [227, 853], [227, 892],
  [404, 744], [404, 773], [404, 794],
  [581, 744], [581, 773], [581, 815], [581, 836], [581, 857],
  [758, 745], [758, 774], [758, 795], [758, 816], [758, 837], [758, 858], [758, 879], [758, 921],
  [935, 745], [935, 774], [935, 812], [935, 833], [935, 854], [935, 875],
  [1111, 744], [1111, 773], [1111, 794], [1111, 815], [1111, 836], [1111, 857],
];

// ---- timing ---------------------------------------------------------------

const CLASS_AT = 16;
const CLASS_STEP = 2.5;
const WORK_AT = 40;
const WORK_STEP = 2.5;
const SUB_AT = 62;
const SUB_STEP = 2;

const classSettle = CLASS_AT + CLASS_CHIPS.length * 2 * CLASS_STEP;
const workSettle = WORK_AT + WORK_CHIPS.length * 2 * WORK_STEP;
const subSettle = SUB_AT + (SUBCLASS_Y.length * 2 - 2) * SUB_STEP;

export type ProfilePopulateProps = {
  transparent: boolean;
  /** Size a settled decision grows to while it hovers. */
  heroHoverScale: number;
  /** Size it reaches as it scatters out of frame. */
  heroFlyScale: number;
  heroHoverFrames: number;
  complexityStart: number;
  complexityStagger: number;
  scopeStart: number;
  scopeStagger: number;
  flyStart: number;
  flyScale: number;
};

export const profilePopulateDefaults: ProfilePopulateProps = {
  transparent: false,
  heroHoverScale: 2.6,
  heroFlyScale: 6.5,
  heroHoverFrames: 14,
  complexityStart: 110,
  complexityStagger: 5,
  scopeStart: 150,
  scopeStagger: 1.6,
  flyStart: 240,
  flyScale: 3.2,
};

const Tick: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size} viewBox="0 0 12 12">
    <rect width="12" height="12" rx="2.5" fill={CHECK_BLUE} />
    <path d="M3 6.2 L5.1 8.4 L9.2 3.9" fill="none" stroke="#FFF" strokeWidth="1.7"
      strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ProfilePopulate: React.FC<ProfilePopulateProps> = (props) => {
  const frame = useCurrentFrame();
  const {width, height, fps, durationInFrames} = useVideoConfig();

  const [handle] = useState(() => delayRender('satoshi'));
  useEffect(() => {
    const f = new FontFace('SatoshiFilm', `url(${staticFile('Satoshi-Light.woff2')}) format('woff2')`);
    f.load()
      .then((loaded) => {
        (document.fonts as unknown as {add: (x: FontFace) => void}).add(loaded);
        continueRender(handle);
      })
      .catch(() => continueRender(handle));
  }, [handle]);

  const FONT = 'SatoshiFilm, "Segoe UI", Helvetica, Arial, sans-serif';

  const open = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
  });
  const fly = interpolate(frame, [props.flyStart, durationInFrames - 1], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic),
  });

  const fit = Math.min(width / PAGE_W, height / PAGE_H) * 0.94;
  const push = 1 + 0.012 * (Math.min(frame, props.flyStart) / fps);
  const pageScale = fit * (0.95 + 0.05 * open) * push * (1 + (props.flyScale - 1) * fly);
  const pageOpacity = open * (1 - interpolate(fly, [0.45, 1], [0, 1], {extrapolateLeft: 'clamp'}));

  /** Racing highlight: two full passes over the options, then the pick. */
  const raceIndex = (at: number, step: number, count: number, pick: number) => {
    const i = Math.floor((frame - at) / step);
    if (i < 0) return -1;
    if (i >= count * 2) return pick;
    return i % count;
  };

  /** Subclass scrolls down the list and back up before settling. */
  const scrollIndex = () => {
    const n = SUBCLASS_Y.length;
    const i = Math.floor((frame - SUB_AT) / SUB_STEP);
    if (i < 0) return -1;
    const total = n * 2 - 2;
    if (i >= total) return SUBCLASS_PICK;
    return i < n ? i : total - i;
  };

  const settled = (at: number, dur = 4) =>
    interpolate(frame, [at, at + dur], [0, 1], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad),
    });

  const classIdx = raceIndex(CLASS_AT, CLASS_STEP, CLASS_CHIPS.length, 0);
  const workIdx = raceIndex(WORK_AT, WORK_STEP, WORK_CHIPS.length, 0);
  const subIdx = scrollIndex();

  // ---- the three hero lift-offs, each scattering its own way --------------
  const heroes = [
    {r: CLASS_CHIPS[0].r, at: classSettle + 2, dir: [-1, -0.75]},
    {r: WORK_CHIPS[0].r, at: workSettle + 2, dir: [0.15, -1]},
    {r: {x: 34, y: 481, w: 182, h: 18}, at: subSettle + 2, dir: [1, -0.7]},
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: props.transparent ? 'transparent' : '#FEFCF5',
        backgroundImage: props.transparent ? undefined
          : 'radial-gradient(120% 90% at 50% 42%, #FFFFFF 0%, #F4F0E5 100%)',
        alignItems: 'center', justifyContent: 'center', perspective: 1400,
      }}
    >
      <div style={{
        width: PAGE_W, height: PAGE_H, position: 'relative',
        transform: `scale(${pageScale})`, opacity: pageOpacity,
      }}>
        {/* ---------- the page ---------- */}
        <div style={{
          position: 'absolute', inset: 0, borderRadius: 10, overflow: 'hidden',
          boxShadow: props.transparent ? undefined
            : '0 40px 120px -40px rgba(45,43,43,0.45), 0 2px 8px rgba(45,43,43,0.10)',
        }}>
          <Img src={staticFile('profile-full.png')}
            style={{width: PAGE_W, height: PAGE_H, display: 'block'}} />

          {/* complexity: cover the stale "Not stated" for good, draw live text */}
          {COMPLEXITY.map((d, i) => {
            const at = props.complexityStart + i * props.complexityStagger;
            const step = 3;
            const k = Math.floor((frame - at) / step);
            const shown = k < 0 ? null
              : k >= 3 ? d.options[d.pick]
              : d.options[Math.floor(random(`cx-${i}-${k}`) * d.options.length)];
            return (
              <React.Fragment key={`cx${i}`}>
                <div style={{
                  position: 'absolute', left: d.x, top: d.y, width: 262, height: 26,
                  backgroundColor: INPUT_FILL,
                }} />
                {shown ? (
                  <div style={{
                    position: 'absolute', left: d.x + 4, top: d.y + 13,
                    transform: 'translateY(-50%)', font: `300 13px ${FONT}`, color: INK,
                    whiteSpace: 'nowrap',
                  }}>{shown}</div>
                ) : null}
                {k >= 0 && k < 3 ? (
                  <div style={{
                    position: 'absolute', left: d.x - 8, top: d.y - 3,
                    width: 278, height: 32, borderRadius: 6,
                    background: BLUE_TINT, outline: `1.5px solid ${BLUE}`, outlineOffset: -1,
                  }} />
                ) : null}
              </React.Fragment>
            );
          })}

          {/* CLASS: hide the real selection until the race lands on it */}
          {settled(classSettle) < 1 ? (
            <div style={{
              position: 'absolute', left: 29, top: 241, width: 412, height: 32,
              borderRadius: 7, background: CHIP_FILL, border: `1px solid ${CHIP_BORDER}`,
              display: 'flex', alignItems: 'center', paddingLeft: 14, boxSizing: 'border-box',
              font: `300 13.5px ${FONT}`, color: INK, opacity: 1 - settled(classSettle),
            }}>Residential</div>
          ) : null}
          {classIdx >= 0 && frame < classSettle + 4 ? (
            <div style={{
              position: 'absolute',
              left: CLASS_CHIPS[classIdx].r.x, top: CLASS_CHIPS[classIdx].r.y,
              width: CLASS_CHIPS[classIdx].r.w, height: CLASS_CHIPS[classIdx].r.h,
              borderRadius: 7, background: BLUE_TINT,
              outline: `1.5px solid ${BLUE}`, outlineOffset: -1,
            }} />
          ) : null}

          {/* WORK TYPE */}
          {settled(workSettle) < 1 ? (
            <div style={{
              position: 'absolute', left: 29, top: 344, width: 88, height: 31,
              borderRadius: 16, background: CHIP_FILL, border: `1px solid ${CHIP_BORDER}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxSizing: 'border-box', font: `300 13px ${FONT}`, color: INK,
              opacity: 1 - settled(workSettle),
            }}>New build</div>
          ) : null}
          {workIdx >= 0 && frame < workSettle + 4 ? (
            <div style={{
              position: 'absolute',
              left: WORK_CHIPS[workIdx].r.x, top: WORK_CHIPS[workIdx].r.y,
              width: WORK_CHIPS[workIdx].r.w, height: WORK_CHIPS[workIdx].r.h,
              borderRadius: 16, background: BLUE_TINT,
              outline: `1.5px solid ${BLUE}`, outlineOffset: -1,
            }} />
          ) : null}

          {/* SUBCLASS: empty the real radio, run a blue dot down the list */}
          {settled(subSettle) < 1 ? (
            <div style={{
              position: 'absolute', left: 40, top: 483, width: 12, height: 12,
              borderRadius: '50%', background: BOX_FILL, border: '1px solid #9E9E9D',
              boxSizing: 'border-box', opacity: 1 - settled(subSettle),
            }} />
          ) : null}
          {subIdx >= 0 && frame < subSettle + 4 ? (
            <>
              <div style={{
                position: 'absolute', left: 40, top: SUBCLASS_Y[subIdx] - 6,
                width: 12, height: 12, borderRadius: '50%',
                background: CHECK_BLUE, border: `1px solid ${CHECK_BLUE}`, boxSizing: 'border-box',
              }} />
              <div style={{
                position: 'absolute', left: 34, top: SUBCLASS_Y[subIdx] - 9,
                width: 182, height: 18, borderRadius: 4, background: BLUE_TINT,
              }} />
            </>
          ) : null}

          {/* SCOPE: empty boxes until each tick lands */}
          {CHECKBOXES.map(([bx, by], i) => {
            const t = settled(props.scopeStart + i * props.scopeStagger + 12, 3);
            if (t >= 1) return null;
            return (
              <div key={`b${i}`} style={{
                position: 'absolute', left: bx, top: by, width: 12, height: 12,
                background: BOX_FILL, border: `1px solid ${BOX_BORDER}`,
                borderRadius: 2.5, boxSizing: 'border-box', opacity: 1 - t,
              }} />
            );
          })}
        </div>

        {/* ---------- ticks flying in ---------- */}
        {CHECKBOXES.map(([bx, by], i) => {
          const at = props.scopeStart + i * props.scopeStagger;
          const t = interpolate(frame, [at, at + 12], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
          });
          if (t <= 0 || t >= 1) return null;
          const ang = random(`tick-a-${i}`) * Math.PI * 2;
          const dist = 90 + random(`tick-d-${i}`) * 150;
          return (
            <div key={`f${i}`} style={{
              position: 'absolute', left: bx, top: by,
              transform: `translate(${Math.cos(ang) * dist * (1 - t)}px, ${
                Math.sin(ang) * dist * (1 - t) - 30 * (1 - t)}px) scale(${1 + 2.2 * (1 - t)})`,
              opacity: Math.min(1, t * 4),
              filter: `drop-shadow(0 2px 6px rgba(0,117,252,${0.45 * (1 - t)}))`,
            }}><Tick size={12} /></div>
          );
        })}

        {/* ---------- the three decisions lifting off ---------- */}
        {heroes.map((h, i) => {
          const life = frame - h.at;
          const total = 7 + props.heroHoverFrames + 16;
          if (life < 0 || life > total) return null;

          const rise = interpolate(life, [0, 7], [0, 1], {
            extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
          });
          const go = interpolate(life, [7 + props.heroHoverFrames, total], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic),
          });
          const scale =
            1 + (props.heroHoverScale - 1) * rise +
            (props.heroFlyScale - props.heroHoverScale) * go;
          const bob = Math.sin((life / fps) * 3.4) * 5 * rise * (1 - go);
          const throwX = h.dir[0] * PAGE_W * 0.55 * go;
          const throwY = h.dir[1] * PAGE_H * 0.5 * go - 18 * rise;

          return (
            <div key={`h${i}`} style={{
              position: 'absolute', left: h.r.x, top: h.r.y, width: h.r.w, height: h.r.h,
              transform: `translate(${throwX}px, ${throwY + bob}px) scale(${scale})`,
              opacity: (1 - go) * Math.min(1, rise * 2.5),
              borderRadius: 7, overflow: 'hidden',
              boxShadow: `0 ${10 + 40 * go}px ${28 + 70 * go}px -10px rgba(30,60,110,${0.4 * (1 - go)})`,
              outline: `1.5px solid rgba(65,132,242,${0.9 - 0.5 * go})`, outlineOffset: -1,
            }}>
              <Img src={staticFile('profile-full.png')} style={{
                width: PAGE_W, height: PAGE_H, display: 'block',
                marginLeft: -h.r.x, marginTop: -h.r.y,
              }} />
              <div style={{position: 'absolute', inset: 0, background: BLUE_TINT}} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
