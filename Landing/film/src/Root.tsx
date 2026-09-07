import React from 'react';
import {Composition} from 'remotion';
import {RingBurst, ringBurstDefaults} from './RingBurst';
import {FlyingIcons, flyingIconsDefaults} from './FlyingIcons';
import {ProfilePopulate, profilePopulateDefaults} from './ProfilePopulate';

// 30fps and 1920x1080 to match the reference film exactly.
const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Clip 4 on pure black — Screen-blend this over anything in CapCut. */}
      <Composition
        id="RingBurst"
        component={RingBurst}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={ringBurstDefaults}
      />

      {/* Same clip with a real alpha channel, for editors that accept it. */}
      <Composition
        id="RingBurstAlpha"
        component={RingBurst}
        durationInFrames={5 * FPS}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{...ringBurstDefaults, transparent: true}}
      />

      {/* The transition the reference actually uses — the shell hands the
          frame over to the bone ground instead of dying away. Shorter,
          because a wipe that lingers stops reading as a wipe. */}
      <Composition
        id="RingWipeToBone"
        component={RingBurst}
        durationInFrames={Math.round(1.6 * FPS)}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{
          ...ringBurstDefaults,
          wipeTo: '#FEFCF5',
          peakOut: 1,
          falloff: 0.4,
          strokeEnd: 90,
          // Far enough past the corners that the fill closes completely, and a
          // gentler ease so the radius grows evenly instead of finishing early.
          overshoot: 1.8,
          ease: 1.6,
        }}
      />
      {/* Clip 3 — icons fly in oversized, recede into place, then rise out. */}
      <Composition
        id="FlyingIcons"
        component={FlyingIcons}
        durationInFrames={7 * FPS}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={flyingIconsDefaults}
      />

      {/* Same, with a real alpha channel for compositing over a light ground. */}
      <Composition
        id="FlyingIconsAlpha"
        component={FlyingIcons}
        durationInFrames={7 * FPS}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{"transparent":true,"seed":"sitewise-01","baseSize":150,"minScale":0.34,"maxScale":2.05,"scaleBias":1.5,"startScaleMin":2.8,"startScaleMax":5.5,"flyInFrames":42,"stagger":5,"riseStart":140,"riseFrames":46,"riseDistance":1.15,"safeWidth":0.46,"safeHeight":0.24,"opacity":0.92,"showTile":true}}
      />
      {/* Profile page filling itself in, then rushing past the lens. */}
      <Composition
        id="ProfilePopulate"
        component={ProfilePopulate}
        durationInFrames={9 * FPS}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={profilePopulateDefaults}
      />

      <Composition
        id="ProfilePopulateAlpha"
        component={ProfilePopulate}
        durationInFrames={9 * FPS}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{...profilePopulateDefaults, transparent: true}}
      />
    </>
  );
};
