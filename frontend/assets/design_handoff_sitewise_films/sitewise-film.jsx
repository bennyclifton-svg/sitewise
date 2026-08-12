/* Sitewise — landing film. Three beats, one continuous composition.
   Copy is verbatim from docs/plans/2026-08-08 iteration beats; unit ids from the
   transcript are kept as the `id` on each line so animation and copy stay mapped. */
const { CompositionStage, useComposition, interpolate, Easing, clamp } = window;

const W = 1920, H = 1080;

/* Three motion helpers, and nothing eases outside them. */
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

function Cube({ T, C }) {
  const host = React.useRef(null);
  const [, tick] = React.useState(0);
  const kit = window.SitewiseFilmCube;

  React.useEffect(() => {
    if (kit) return;
    const id = setInterval(() => { if (window.SitewiseFilmCube) { clearInterval(id); tick((n) => n + 1); } }, 60);
    return () => clearInterval(id);
  }, [kit]);

  React.useEffect(() => {
    if (kit && host.current && kit.canvas.parentNode !== host.current) host.current.appendChild(kit.canvas);
  }, [kit]);

  // Drawn synchronously with the render, so a seeked frame is an exported frame.
  if (kit) kit.drawAt(T, C);

  return <div ref={host} style={{ position: 'absolute', inset: 0, width: W, height: H }} />;
}

/* Beat 3: as each sector lights again, the source it came from is named under
   the mark. One line at a time — provenance, not a legend. */
function Trace({ T, at }) {
  const kit = window.SitewiseFilmCube;
  const names = (kit && kit.sources) || [];
  const step = 2.4, lead = 2.6;
  const raw = Math.floor((T - at - lead) / step);
  if (raw < 0 || !names.length) return null;
  const i = Math.min(raw, names.length - 1);
  const s0 = at + lead + i * step;
  // the last source stays named for as long as its sector is still being lit
  const out = i === names.length - 1 ? s0 + 5.4 : s0 + step - 0.6;
  const o = MOTION.enter(s0)(T) * MOTION.exit(out)(T);
  return (
    <div style={{
      position: 'absolute', left: 132, top: 902, width: 780, opacity: o,
      display: 'flex', alignItems: 'center', gap: 14
    }}>
      <div style={{ width: 46, height: 1, background: '#2F72C4', flex: 'none' }} />
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 17, letterSpacing: '0.16em',
        textTransform: 'uppercase', color: '#93BEEC', whiteSpace: 'nowrap'
      }}>{names[i]}</div>
    </div>
  );
}

function Piece() {
  const { T, CUES, authoredTotal } = useComposition();
  const C = {
    promise: CUES.Promise, iteration: CUES.Iteration,
    payoff: CUES.Payoff, total: authoredTotal
  };

  return (
    <div style={{
      position: 'absolute', inset: 0, background: '#060608', overflow: 'hidden',
      fontFamily: "'Hanken Grotesk', Helvetica, sans-serif"
    }}>
      <Cube T={T} C={C} />
      <Trace T={T} at={CUES.Payoff} />

      {/* the copy column sits over the cube's falloff, never over its lit face */}
      <div style={{
        position: 'absolute', left: 0, top: 0, width: 1180, height: H,
        background: 'linear-gradient(90deg, #060608 68%, rgba(6,6,8,0) 100%)'
      }} />

      <Beat T={T} cue={CUES.Promise} out={30.8} label="01 — The promise" headSize={74}
        head={[
          { id: 'H1a', at: 0, text: 'You do the judgement.' },
          { id: 'H1b', at: 2, text: 'SiteWise does the assembly.' }
        ]}
        body={[
          { id: 'B1a', at: 5, text: 'Drop in the drawings, specs, site notes and invoices as they land.' },
          { id: 'B1b', at: 10, text: 'SiteWise reads them, files them, and builds the plan, report or comparison you were going to write by hand —' },
          { id: 'B1c', at: 25, lead: true, text: 'every detail considered, to shape your next move.' }
        ]} />

      <Beat T={T} cue={CUES.Iteration} out={28.6} label="02 — The iteration" headSize={56}
        head={[
          { id: 'H2a', at: 0, text: 'Layer on the detail.' },
          { id: 'H2b', at: 2, text: 'More consultants, more design.' },
          { id: 'H2c', at: 4, text: 'SiteWise keeps up with your pace.' }
        ]}
        body={[
          { id: 'B2a', at: 7, text: 'As the project evolves, so do the details and complexity.' },
          { id: 'B2b', at: 10, text: 'More consultants join, more drawings land, more interfaces to align.' },
          { id: 'B2c', at: 14, text: 'New information is weighed against what’s already been decided. SiteWise doesn’t tire of that.' },
          { id: 'B2d', at: 18, text: 'Two consultants or twenty, five drawings or five hundred, a ten-line cost plan or a thousand —' },
          { id: 'B2e', at: 22, text: 'it re-reads, re-checks and rebuilds every time something changes, staying current instead of catching up.' },
          { id: 'B2f', at: 26, lead: true, text: 'Every detail shaping the next move.' }
        ]} />

      <Beat T={T} cue={CUES.Payoff} out={23.5} label="03 — The payoff" headSize={60}
        head={[
          { id: 'H3', at: 0, text: 'Tender time, and the cheap number isn’t always the safe one.' }
        ]}
        body={[
          { id: 'B3a', at: 4, text: 'Every consultant, contractor and trade prices the same scope, and it’s rarely obvious which quote is complete and which one quietly left something out.' },
          { id: 'B3b', at: 9, text: 'SiteWise already holds the detail — every drawing, spec and revision that built the design —' },
          { id: 'B3c', at: 12, text: 'so it checks each tender against that scope, not just against its price.' },
          { id: 'B3d', at: 16, text: 'Consultants, contractors, trades: one comparison engine, line by line, exclusions flagged.' },
          { id: 'B3e', at: 20, lead: true, text: 'Evaluation in moments, grounded and traced.' }
        ]} />

      {/* the spine, held under everything, arriving only as the film settles */}
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

function SitewiseFilm() {
  return (
    <CompositionStage width={W} height={H} bg="#060608"
      scenes={window.OM_SCENES} playback={window.OM_PLAYBACK}>
      <Piece />
    </CompositionStage>
  );
}

window.SitewiseFilm = SitewiseFilm;
