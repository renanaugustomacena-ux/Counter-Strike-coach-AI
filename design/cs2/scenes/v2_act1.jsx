// v2_act1.jsx — Cold open, problem, thesis
// ─────────────────────────────────────────

function V2_S1_ColdOpen({ start, dur }) {
  const end = start + dur;
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.bgDeep }} />
          <ParticleField count={80} seed={3} color={C.accent} speed={0.5} opacity={0.3}/>
          <div style={{ opacity: Easing.easeOutCubic(clamp(localTime / 0.6, 0, 1)) }}>
            <RadarSweep cx={960} cy={540} r={520} color={C.accent} speed={0.4}/>
          </div>

          <Sprite start={0.4} end={dur - 0.6} keepMounted>
            <TelemetryScroller x={1500} y={60} width={380} height={960} opacity={0.5}/>
          </Sprite>
          <Sprite start={0.6} end={dur - 0.6} keepMounted>
            <Oscilloscope x={80} y={880} width={880} height={140} color={C.accent} amp={0.35}/>
          </Sprite>

          <div style={{ opacity: Easing.easeOutCubic(clamp(localTime / 0.3, 0, 1)) }}>
            <Typewriter x={80} y={120} start={0.3} cps={55}
              text="initializing macena.coach_ai::boot" prefix="$" size={13} color={C.tx1}/>
            <Typewriter x={80} y={148} start={0.9} cps={55}
              text="mount /models/jepa_encoder.ckpt           [OK]" prefix="→" size={13} color={C.ok}/>
            <Typewriter x={80} y={176} start={1.5} cps={55}
              text="mount /models/hopfield_memory.ckpt        [OK]" prefix="→" size={13} color={C.ok}/>
            <Typewriter x={80} y={204} start={2.1} cps={55}
              text="mount /models/chronovisor_multiscale.ckpt [OK]" prefix="→" size={13} color={C.ok}/>
            <Typewriter x={80} y={232} start={2.7} cps={55}
              text="assemble rap_pipeline [7 layers]          [OK]" prefix="→" size={13} color={C.ok}/>
            <Typewriter x={80} y={260} start={3.3} cps={55}
              text="enforce humility_gate conf>=0.7           [OK]" prefix="→" size={13} color={C.accent}/>
            <Typewriter x={80} y={288} start={3.9} cps={55}
              text="system online ::" prefix="✓" size={13} color={C.accent}/>
          </div>

          <Sprite start={4.2} end={dur} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutQuart(clamp(lt / 0.8, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: '50%', top: '50%',
                  transform: 'translate(-50%, -50%)',
                  textAlign: 'center', opacity: p,
                }}>
                  <div style={{ width: 140 * p, height: 3, background: C.accent, margin: '0 auto 36px' }}/>
                  <div style={{
                    fontFamily: F.display, fontSize: 260, fontWeight: 400, color: C.tx1,
                    letterSpacing: '-0.04em', lineHeight: 0.85,
                    textShadow: `0 0 40px ${C.accent}88`,
                  }}>MACENA</div>
                  <div style={{
                    fontFamily: F.mono, fontSize: 18, letterSpacing: '0.6em',
                    color: C.accent, textTransform: 'uppercase', marginTop: 28,
                    opacity: Easing.easeOutCubic(clamp((lt - 0.5) / 0.5, 0, 1)),
                  }}>CS2 &middot; COACH &middot; AI</div>
                </div>
              );
            }}
          </Sprite>

          <Vignette strength={0.75}/>
          <Scanlines opacity={0.05}/>
        </>
      )}
    </Sprite>
  );
}

function V2_S2_Problem({ start, dur }) {
  const end = start + dur;
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.base }} />
          <ParticleField count={40} seed={9} color={C.err} speed={0.3} opacity={0.2}/>

          <Sprite start={0.2} end={dur - 0.3} keepMounted>
            <KineticNumber x={120} y={240} to={32} dur={1.4} size={340}
              color={C.tx1} suffix="M" format={v => v.toFixed(1)}/>
          </Sprite>
          <Sprite start={1.0} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 120, top: 560,
                  opacity: p, transform: `translateY(${(1 - p) * 14}px)`,
                  fontFamily: F.display, fontSize: 64, color: C.tx1,
                  letterSpacing: '-0.01em', textTransform: 'uppercase', lineHeight: 0.95,
                }}>players grinding.</div>
              );
            }}
          </Sprite>

          <Sprite start={2.2} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => (
              <div style={{ position: 'absolute', left: 120, top: 680 }}>
                <div style={{ width: 1680 * Easing.easeOutCubic(clamp(lt / 0.8, 0, 1)), height: 1, background: C.border }}/>
              </div>
            )}
          </Sprite>

          <Sprite start={2.6} end={dur - 0.3} keepMounted>
            <KineticNumber x={120} y={720} to={0.001} dur={1.2} size={160}
              color={C.err} prefix="< " suffix=" %" format={v => v.toFixed(3)}/>
          </Sprite>
          <Sprite start={3.3} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 820, top: 780, opacity: p,
                  fontFamily: F.sans, fontSize: 26, fontWeight: 300,
                  color: C.tx2, lineHeight: 1.25,
                }}>
                  have ever worked with<br/>
                  <span style={{ color: C.tx1, fontWeight: 600 }}>a professional coach.</span>
                </div>
              );
            }}
          </Sprite>

          <Sprite start={1.5} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.7, 0, 1));
              return (
                <div style={{
                  position: 'absolute', right: 100, top: 280, width: 560,
                  opacity: p, transform: `translateY(${(1 - p) * 20}px)`,
                }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 12, letterSpacing: '0.3em',
                    color: C.accent, textTransform: 'uppercase', marginBottom: 32,
                  }}>— THE GAP —</div>
                  <div style={{
                    fontFamily: F.serif, fontSize: 54, fontWeight: 300,
                    color: C.tx1, lineHeight: 1.2, letterSpacing: '-0.015em', fontStyle: 'italic',
                  }}>
                    You can watch a thousand demos<br/>
                    and still not know<br/>
                    <span style={{ color: C.accent, fontStyle: 'normal', fontWeight: 600 }}>
                      what to fix next.
                    </span>
                  </div>
                </div>
              );
            }}
          </Sprite>

          <Chyron number="01" title="THE PROBLEM" subtitle="signal lost in opinion."/>
          <PersistentHud/>
        </>
      )}
    </Sprite>
  );
}

function V2_S3_Thesis({ start, dur }) {
  const end = start + dur;
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.sunken }} />
          <ParticleField count={80} seed={17} color={C.accent} speed={0.4} opacity={0.3}/>
          <RadarSweep cx={1500} cy={540} r={420} color={C.accent} speed={0.2}/>

          <Sprite start={0.2} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const words = ['RELIABILITY', 'THROUGH', 'SELF-', 'CORRECTION.'];
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 200, width: 1200,
                  fontFamily: F.display, fontSize: 170, fontWeight: 400,
                  color: C.tx1, letterSpacing: '-0.04em', lineHeight: 0.9,
                }}>
                  {words.map((w, i) => {
                    const wp = Easing.easeOutQuart(clamp((lt - i * 0.15) / 0.6, 0, 1));
                    const isAccent = w.includes('SELF') || w.includes('CORRECTION');
                    return (
                      <div key={i} style={{ overflow: 'hidden' }}>
                        <div style={{
                          transform: `translateY(${(1 - wp) * 100}%)`,
                          color: isAccent ? C.accent : C.tx1,
                        }}>{w}</div>
                      </div>
                    );
                  })}
                </div>
              );
            }}
          </Sprite>

          <Sprite start={2.1} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.6, 0, 1));
              const strike = Easing.easeInOutCubic(clamp((lt - 0.5) / 0.6, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 860,
                  display: 'flex', alignItems: 'center', gap: 18,
                  opacity: p,
                }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 12, letterSpacing: '0.4em',
                    color: C.tx3, textTransform: 'uppercase',
                  }}>NOT THROUGH</div>
                  <div style={{
                    position: 'relative', fontFamily: F.display, fontSize: 48,
                    color: C.tx3, letterSpacing: '-0.02em', lineHeight: 1, textTransform: 'uppercase',
                  }}>
                    SCALE
                    <div style={{
                      position: 'absolute', left: 0, top: '50%',
                      width: `${strike * 100}%`, height: 4, background: C.accent,
                    }}/>
                  </div>
                </div>
              );
            }}
          </Sprite>

          <Sprite start={1.0} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.6, 0, 1));
              const N = 50; const pts = [];
              for (let i = 0; i < N; i++) {
                const x = i / (N - 1);
                const phase = (lt * 0.5 - x) * 3;
                pts.push(0.5 + 0.35 * Math.sin(phase) + 0.1 * Math.sin(phase * 3.2));
              }
              const W = 540, H = 300;
              const path = pts.map((v, i) => `${i === 0 ? 'M' : 'L'} ${(i / (N - 1)) * W} ${H - v * H}`).join(' ');
              const gateY = H - 0.7 * H;
              return (
                <div style={{ position: 'absolute', right: 100, top: 260, width: 600, opacity: p }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 12, letterSpacing: '0.25em',
                    color: C.accent, textTransform: 'uppercase', marginBottom: 16,
                  }}>LIVE · CONFIDENCE SIGNAL</div>
                  <div style={{ position: 'relative', width: W, height: H, border: `1px solid ${C.border}`, background: 'rgba(0,0,0,0.3)' }}>
                    <svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}>
                      {[0.25, 0.5, 0.75].map((g, i) => (
                        <line key={i} x1="0" y1={H - g * H} x2={W} y2={H - g * H}
                          stroke={C.border} strokeWidth="1" strokeDasharray="2 6" opacity="0.5"/>
                      ))}
                      <line x1="0" y1={gateY} x2={W} y2={gateY}
                        stroke={C.accent} strokeWidth="2" strokeDasharray="6 3" opacity="0.8"/>
                      <text x={W - 8} y={gateY - 6} fill={C.accent}
                        fontFamily={F.mono} fontSize="11" textAnchor="end" letterSpacing="2">GATE · 0.70</text>
                      <path d={`${path} L ${W} ${H} L 0 ${H} Z`} fill={C.accent} opacity="0.15"/>
                      <path d={path} fill="none" stroke={C.accent} strokeWidth="2"/>
                    </svg>
                  </div>
                  <div style={{
                    marginTop: 12, display: 'flex', justifyContent: 'space-between',
                    fontFamily: F.mono, fontSize: 11, letterSpacing: '0.2em',
                    color: C.tx3, textTransform: 'uppercase',
                  }}>
                    <span>conf &lt; 0.7 <span style={{ color: C.warn }}>→ silent</span></span>
                    <span>conf &ge; 0.7 <span style={{ color: C.ok }}>→ speak</span></span>
                  </div>
                </div>
              );
            }}
          </Sprite>

          <Chyron number="02" title="THE THESIS" subtitle="humility as a feature."/>
          <PersistentHud/>
          <Vignette strength={0.55}/>
        </>
      )}
    </Sprite>
  );
}

Object.assign(window, { V2_S1_ColdOpen, V2_S2_Problem, V2_S3_Thesis });
