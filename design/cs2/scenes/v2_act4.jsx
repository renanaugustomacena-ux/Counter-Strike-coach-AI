// v2_act4.jsx — ACT 4: RAP self-correction loop
// ──────────────────────────────────────────────
// Strategy: animate the loop — draft → critique → rewrite — with
// a running transcript that self-corrects in real time.

function V2_S8_RAP({ start, dur }) {
  const end = start + dur;

  // Loop stages with timing
  const stages = [
    { label: 'DRAFT',    s: 1.5,  c: C.info,   text: 'You should push A.' },
    { label: 'CRITIQUE', s: 3.5,  c: C.warn,   text: 'conf 0.42 · below gate · reason missing' },
    { label: 'REWRITE',  s: 5.5,  c: C.cyan,   text: 'On round 7 you overpeeked long from CT. Hold angle.' },
    { label: 'GATE · PASS', s: 7.8, c: C.ok,   text: 'conf 0.83 · ≥ 0.70 · SHIP' },
  ];

  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.sunken }} />
          <ParticleField count={50} seed={47} color={C.accent} speed={0.35} opacity={0.2}/>

          {/* Title */}
          <Sprite start={0.1} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 100, opacity: p,
                }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 12, letterSpacing: '0.35em',
                    color: C.accent, textTransform: 'uppercase', marginBottom: 24,
                  }}>RAP · REFLEX-AUDIT-PROMPT</div>
                  <div style={{
                    fontFamily: F.display, fontSize: 160, color: C.tx1,
                    letterSpacing: '-0.04em', lineHeight: 0.86, textTransform: 'uppercase',
                  }}>
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ transform: `translateY(${(1 - clamp(lt / 0.5, 0, 1)) * 100}%)` }}>
                        IT CRITIQUES
                      </div>
                    </div>
                    <div style={{ overflow: 'hidden', color: C.accent }}>
                      <div style={{ transform: `translateY(${(1 - clamp((lt - 0.15) / 0.5, 0, 1)) * 100}%)` }}>
                        ITSELF.
                      </div>
                    </div>
                  </div>
                </div>
              );
            }}
          </Sprite>

          {/* Loop diagram — left */}
          <div style={{
            position: 'absolute', left: 80, top: 540,
            width: 720, height: 420,
          }}>
            <svg width="720" height="420" style={{ position: 'absolute', inset: 0 }}>
              <defs>
                <marker id="rap-arrow" viewBox="0 0 10 10" refX="8" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto">
                  <path d="M0,0 L10,5 L0,10 z" fill={C.accent}/>
                </marker>
              </defs>
              {/* three stations */}
              {[
                { x: 120, y: 100, label: 'DRAFT' },
                { x: 600, y: 100, label: 'CRITIQUE' },
                { x: 360, y: 320, label: 'REWRITE' },
              ].map((st, i) => {
                const active = localTime >= stages[i]?.s && localTime < (stages[i + 1]?.s || dur);
                const c = active ? C.accent : C.border;
                return (
                  <g key={i}>
                    <circle cx={st.x} cy={st.y} r="54" fill="rgba(0,0,0,0.6)" stroke={c} strokeWidth={active ? 3 : 1.5}/>
                    {active && <circle cx={st.x} cy={st.y} r={54 + (localTime * 4) % 20} fill="none" stroke={c} strokeWidth="1" opacity={1 - ((localTime * 4) % 20) / 20}/>}
                    <text x={st.x} y={st.y + 5} textAnchor="middle"
                      fill={active ? C.tx1 : C.tx3}
                      fontFamily={F.mono} fontSize="12" letterSpacing="3" fontWeight="600">{st.label}</text>
                  </g>
                );
              })}
              {/* arrows */}
              <path d="M 180 100 Q 360 60 540 100" fill="none" stroke={C.accent} strokeWidth="1.5" markerEnd="url(#rap-arrow)" opacity="0.7"/>
              <path d="M 580 150 Q 480 260 400 290" fill="none" stroke={C.accent} strokeWidth="1.5" markerEnd="url(#rap-arrow)" opacity="0.7"/>
              <path d="M 310 290 Q 200 200 140 150" fill="none" stroke={C.accent} strokeWidth="1.5" strokeDasharray="4 4" markerEnd="url(#rap-arrow)" opacity="0.5"/>
              <text x="360" y="50" textAnchor="middle" fill={C.tx3} fontFamily={F.mono} fontSize="10" letterSpacing="3">1 · propose</text>
              <text x="530" y="230" fill={C.tx3} fontFamily={F.mono} fontSize="10" letterSpacing="3">2 · audit</text>
              <text x="175" y="220" fill={C.tx3} fontFamily={F.mono} fontSize="10" letterSpacing="3">3 · revise</text>
            </svg>
            <div style={{
              position: 'absolute', top: 0, right: 0,
              fontFamily: F.mono, fontSize: 10, letterSpacing: '0.3em',
              color: C.accent, textTransform: 'uppercase',
              padding: '4px 10px', border: `1px solid ${C.accent}`,
              background: 'rgba(0,0,0,0.5)',
            }}>LOOP · LIVE</div>
          </div>

          {/* Transcript — right */}
          <div style={{
            position: 'absolute', right: 80, top: 540, width: 1020, height: 420,
            border: `1px solid ${C.border}`,
            background: 'rgba(0,0,0,0.5)',
            padding: 28, fontFamily: F.mono,
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              fontSize: 10, letterSpacing: '0.25em',
              color: C.tx3, textTransform: 'uppercase',
              paddingBottom: 16, borderBottom: `1px solid ${C.border}`,
              marginBottom: 20,
            }}>
              <span>coach_ai :: transcript</span>
              <span style={{ color: C.accent }}>
                STAGE {String(Math.min(4, Math.max(1, stages.filter(s => localTime >= s.s).length))).padStart(2,'0')} / 04
              </span>
            </div>
            {stages.map((s, i) => {
              if (localTime < s.s) return null;
              const lt = localTime - s.s;
              const p = Easing.easeOutCubic(clamp(lt / 0.4, 0, 1));
              // strikethrough the draft once critique arrives
              const isStrike = i === 0 && localTime >= stages[1].s;
              const isReplace = i === 0 && localTime >= stages[2].s;
              return (
                <div key={i} style={{
                  opacity: p, marginBottom: 18,
                  transform: `translateY(${(1 - p) * 8}px)`,
                }}>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    fontSize: 10, letterSpacing: '0.25em',
                    color: s.c, textTransform: 'uppercase', marginBottom: 6,
                  }}>
                    <span style={{ width: 6, height: 6, background: s.c }}/>
                    <span>{s.label}</span>
                    <span style={{ color: C.tx3, letterSpacing: '0.2em' }}>
                      t+{(s.s - stages[0].s).toFixed(2)}s
                    </span>
                  </div>
                  <div style={{
                    fontSize: i === 2 ? 22 : 18, color: isReplace ? C.tx3 : C.tx1,
                    textDecoration: isStrike ? 'line-through' : 'none',
                    textDecorationColor: C.err,
                    opacity: isReplace ? 0.4 : 1,
                    fontFamily: i === 2 ? F.serif : F.mono,
                    fontStyle: i === 2 ? 'italic' : 'normal',
                    lineHeight: 1.4,
                  }}>{s.text}</div>
                </div>
              );
            })}
          </div>

          {/* frame reference moved into chyron subtitle area via a small tag top-right of diagram */}

          <Chyron number="05" title="THE LOOP" subtitle="confidence, not confidence-tricks."/>
          <PersistentHud/>
        </>
      )}
    </Sprite>
  );
}

Object.assign(window, { V2_S8_RAP });
