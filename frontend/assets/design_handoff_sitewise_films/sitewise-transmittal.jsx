/* Sitewise — basement transmittal. One instruction, one continuous composition:
   the mark opens, the assistant takes the question on the roof face, the
   register searches itself on the glazing, and the draft is opened by hand. */
const { CompositionStage, useComposition, interpolate, Easing, clamp } = window;

const W = 1920, H = 1080;

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
  const kit = window.SitewiseTransmittalCube;

  React.useEffect(() => {
    if (kit) return;
    const id = setInterval(() => {
      if (window.SitewiseTransmittalCube) { clearInterval(id); tick((n) => n + 1); }
    }, 60);
    return () => clearInterval(id);
  }, [kit]);

  React.useEffect(() => {
    if (kit && host.current && kit.canvas.parentNode !== host.current) host.current.appendChild(kit.canvas);
  }, [kit]);

  if (kit) kit.drawAt(T, C);

  return <div ref={host} style={{ position: 'absolute', inset: 0, width: W, height: H }} />;
}

function Piece() {
  const { T, CUES, authoredTotal } = useComposition();
  const C = { reveal: CUES.Reveal, transmittal: CUES.Transmittal, total: authoredTotal };

  return (
    <div style={{
      position: 'absolute', inset: 0, background: '#060608', overflow: 'hidden',
      fontFamily: "'Hanken Grotesk', Helvetica, sans-serif"
    }}>
      <Cube T={T} C={C} />

      <div style={{
        position: 'absolute', left: 0, top: 0, width: 1180, height: H,
        background: 'linear-gradient(90deg, #060608 68%, rgba(6,6,8,0) 100%)'
      }} />

      <Beat T={T} cue={CUES.Transmittal} out={29} label="Basement transmittal" headSize={68}
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

      <Beat T={T} cue={40} out={30} label="Project Initiation" headSize={68}
        head={[
          { id: 'P1a', at: 0, text: 'Just tell it' },
          { id: 'P1b', at: 1.4, text: "what you're building." }
        ]}
        body={[
          { id: 'P2a', at: 5, text: 'Drop in a site plan, a feasibility report, an old brief — SiteWise reads them and drafts the project profile itself: classification, scale, location, work type, filling in as the documents land.' },
          { id: 'P2b', at: 24, text: 'Nothing to upload yet? Describe the project in a sentence and watch the same profile build itself from that instead.' },
        ]} />

      <Beat T={T} cue={72} out={17} label="Project profile" headSize={62}
        head={[
          { id: 'C1a', at: 0, text: "You don't fill in the profile." },
          { id: 'C1b', at: 1.3, text: 'You correct it.' }
        ]}
        body={[
          { id: 'C2a', at: 4, text: 'Class, subclass, scale, complexity, scope — the handful of attributes every new project starts with. Ask SiteWise to populate them, and it drafts the profile in seconds.' },
          { id: 'C2b', at: 11, lead: true, text: "Override what's wrong, confirm what's right, and you're straight into the project — not stuck in the intake form." }
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

function SitewiseTransmittal() {
  return (
    <CompositionStage width={W} height={H} bg="#060608"
      scenes={window.OM_SCENES} playback={window.OM_PLAYBACK}>
      <Piece />
    </CompositionStage>
  );
}

window.SitewiseTransmittal = SitewiseTransmittal;
