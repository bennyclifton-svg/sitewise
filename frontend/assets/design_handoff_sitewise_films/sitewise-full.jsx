/* Sitewise — the full film. The logo reveal opens it, the invoice act follows on
   the same cube, then the project profile and the basement transmittal. Two cube
   stages share the frame. The film stage carries reveal + invoice and lifts back
   to the roof; the transmittal stage is picked up on that same roof frame through
   a short dissolve, plays the profile's second half, hands the roof frame back to
   itself, and runs the transmittal from there. Every join is a state match. */
const { CompositionStage, useComposition, interpolate, Easing, clamp } = window;

const W = 1920, H = 1080;

/* The transmittal stage's own clock reaches the parked roof frame 7.6s in; the
   film stage is standing on that same frame when the invoice act ends, and the
   profile pass is authored to hand that frame back. */
const HANDOFF = 7.6;
const DISSOLVE = 0.9;
/* Where the profile picks up in the sheet's own clock — the first half is cut. */
const PROF_SHEET_IN = 65.6;   // the transmittal stage's local time
const PROF_HANDBACK = 2.2;    // profile → transmittal, camera and light
const PROF_END_LOCAL = 93.0;  // the stage's own end-of-profile mark

const MOTION = {
  enter: (at) => interpolate([at, at + 0.9], [0, 1], Easing.easeOutCubic),
  exit: (at) => interpolate([at, at + 1.3], [1, 0], Easing.easeInOutCubic),
  lift: (at) => interpolate([at, at + 1.1], [18, 0], Easing.easeOutCubic)
};

const HEAD = { color: '#E8E8E4', fontWeight: 200, letterSpacing: '-0.028em', lineHeight: 1.14 };
const BODY = { color: '#A8AEB7', fontWeight: 300, fontSize: 28, lineHeight: 1.5, letterSpacing: '-0.005em' };

function Unit({ T, at, out, style, children }) {
  const o = MOTION.enter(at)(T) * MOTION.exit(out)(T);
  return (
    <div style={{
      opacity: o,
      transform: `translate3d(0, ${MOTION.lift(at)(T)}px, 0)`,
      willChange: 'opacity, transform',
      ...style
    }}>{children}</div>
  );
}

function Beat({ T, cue, out, label, head, headSize, body }) {
  const blockOut = cue + out;
  return (
    <div style={{
      position: 'absolute', left: 132, top: '50%', width: 880,
      transform: 'translateY(-50%)', display: 'flex', flexDirection: 'column', gap: 42
    }}>
      <Unit T={T} at={cue} out={blockOut} style={{
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, letterSpacing: '0.24em',
        textTransform: 'uppercase', color: '#7FB0E4'
      }}>{label}</Unit>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {head.map((l) => (
          <Unit key={l.id} T={T} at={cue + l.at} out={blockOut}
                style={{ ...HEAD, fontSize: headSize }}>{l.text}</Unit>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
        {body.map((l) => (
          <Unit key={l.id} T={T} at={cue + l.at} out={blockOut}
                style={{ ...BODY, color: l.lead ? '#E8E8E4' : BODY.color }}>{l.text}</Unit>
        ))}
      </div>
    </div>
  );
}

/* Both stages are mounted. They stand on the same frame across the hand-off, so
   the second is simply dissolved over the first. The transmittal stage is then
   run twice, at two offsets, switching on a frame where its state is identical. */
function Cubes({ T, CA, CB1, CB2, at, swap }) {
  const hostA = React.useRef(null), hostB = React.useRef(null);
  const [, tick] = React.useState(0);
  const kA = window.SitewiseFilmCube, kB = window.SitewiseTransmittalCube;

  React.useEffect(() => {
    if (kA && kB) return;
    const id = setInterval(() => {
      if (window.SitewiseFilmCube && window.SitewiseTransmittalCube) { clearInterval(id); tick((n) => n + 1); }
    }, 60);
    return () => clearInterval(id);
  }, [kA, kB]);

  React.useEffect(() => {
    if (kA && hostA.current && kA.canvas.parentNode !== hostA.current) hostA.current.appendChild(kA.canvas);
    if (kB && hostB.current && kB.canvas.parentNode !== hostB.current) hostB.current.appendChild(kB.canvas);
  }, [kA, kB]);

  const x = clamp((T - (at - DISSOLVE / 2)) / DISSOLVE, 0, 1);
  if (x < 1 && kA) kA.drawAt(T, CA);
  if (x > 0 && kB) kB.drawAt(T, T >= swap ? CB2 : CB1);

  const box = { position: 'absolute', inset: 0, width: W, height: H };
  return (
    <React.Fragment>
      <div ref={hostA} style={{ ...box, opacity: x < 1 ? 1 : 0 }} />
      <div ref={hostB} style={{ ...box, opacity: x }} />
    </React.Fragment>
  );
}

function Piece() {
  const { T, CUES, authoredTotal } = useComposition();
  const X = CUES.Profile;              // film stage → transmittal stage
  const S = CUES.Transmittal;          // profile pass → transmittal pass
  const CA = { promise: CUES.Reveal };
  // the profile pass: entered from the roof frame, handed back to it at S
  const CB1 = {
    reveal: X - PROF_SHEET_IN,
    total: S + 0.1,
    enterAt: X,
    closeTo: 'roof'
  };
  const CB2 = { reveal: S - HANDOFF, total: authoredTotal, act: 'transmittal' };

  return (
    <div style={{
      position: 'absolute', inset: 0, background: '#060608', overflow: 'hidden',
      fontFamily: "'Hanken Grotesk', Helvetica, sans-serif"
    }}>
      <Cubes T={T} CA={CA} CB1={CB1} CB2={CB2} at={X} swap={S} />

      <div style={{
        position: 'absolute', left: 0, top: 0, width: 1180, height: H,
        background: 'linear-gradient(90deg, #060608 68%, rgba(6,6,8,0) 100%)'
      }} />

      <Beat T={T} cue={CUES.Invoice} out={30.8} label="01 — Invoice" headSize={74}
        head={[
          { id: 'H1a', at: 0, text: 'You do the judgement.' },
          { id: 'H1b', at: 2, text: 'SiteWise does the assembly.' }
        ]}
        body={[
          { id: 'B1a', at: 5, text: 'Drop in the drawings, specs, site notes and invoices as they land.' },
          { id: 'B1b', at: 10, text: 'SiteWise reads them, files them, and builds the plan, report or comparison you were going to write by hand —' },
          { id: 'B1c', at: 25, lead: true, text: 'every detail considered, to shape your next move.' }
        ]} />

      <Beat T={T} cue={CUES.Profile} out={25.8} label="02 — Project profile" headSize={62}
        head={[
          { id: 'C1a', at: 0, text: "You don't fill in the profile." },
          { id: 'C1b', at: 1.4, text: 'You correct it.' }
        ]}
        body={[
          { id: 'P2b', at: 4.5, text: 'Nothing to upload yet? Describe the project in a sentence and watch the same profile build itself from that instead.' },
          { id: 'C2a', at: 11, text: 'Class, subclass, scale, complexity, scope — the handful of attributes every new project starts with. Ask SiteWise to populate them, and it drafts the profile in seconds.' },
          { id: 'C2b', at: 19, lead: true, text: "Override what's wrong, confirm what's right, and you're straight into the project — not stuck in the intake form." }
        ]} />

      <Beat T={T} cue={S} out={29} label="03 — Basement transmittal" headSize={68}
        head={[
          { id: 'T1a', at: 0, text: 'One instruction.' },
          { id: 'T1b', at: 1.6, text: 'Nineteen drawings, found and drafted.' }
        ]}
        body={[
          { id: 'T2a', at: 5, text: 'SiteWise reads the whole document register — architectural, structural, hydraulic, mechanical, electrical.' },
          { id: 'T2b', at: 9, text: 'Every basement drawing is picked out on its current revision, across all five disciplines.' },
          { id: 'T2c', at: 17, text: 'The transmittal drafts itself: recipient, purpose, and the nineteen documents listed with their revisions.' },
          { id: 'T2d', at: 23, lead: true, text: 'Draft only. Nothing is issued without you.' }
        ]} />

      <Unit T={T} at={authoredTotal - 5.4} out={authoredTotal - 2.2} style={{
        position: 'absolute', left: 132, bottom: 96, width: 880,
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 14, letterSpacing: '0.2em',
        textTransform: 'uppercase', color: '#7FB0E4'
      }}>You do the judgement. SiteWise does the assembly.</Unit>

      <div style={{ position: 'absolute', left: 0, bottom: 0, height: 1, width: W, background: 'rgba(255,255,255,0.07)' }} />
      <div style={{
        position: 'absolute', left: 0, bottom: 0, height: 1,
        width: clamp(T / authoredTotal, 0, 1) * W,
        background: 'linear-gradient(90deg, #1F5DAB, #7FB0E4)'
      }} />
    </div>
  );
}

function SitewiseFullFilm() {
  return (
    <CompositionStage width={W} height={H} bg="#060608"
      scenes={window.OM_SCENES} playback={window.OM_PLAYBACK}>
      <Piece />
    </CompositionStage>
  );
}

window.SitewiseFullFilm = SitewiseFullFilm;
