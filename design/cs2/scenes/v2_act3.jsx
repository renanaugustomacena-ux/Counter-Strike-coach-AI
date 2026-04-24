// v2_act3.jsx — ACT 3: Architecture deep-dive using the real SVG frames
// ──────────────────────────────────────────────────────────────────────
// Strategy: use the real architecture SVGs (37, 22, 24) as the visual
// anchor, framed like technical documents being examined under a lens.

// Helper — animated SVG framed viewer with scan-line reveal + zoom
function FramedDoc({ src, revealStart = 0, revealDur = 1.0, zoomStart = 0.5, zoomFrom = 1.0, zoomTo = 1.06 }) {
  const { localTime, duration } = useSprite();
  const fade = Easing.easeOutCubic(clamp((localTime - revealStart) / 0.5, 0, 1));
  const maskP = Easing.easeInOutCubic(clamp((localTime - revealStart) / revealDur, 0, 1));
  const zoomP = Easing.easeInOutCubic(clamp((localTime - zoomStart) / (duration - zoomStart - 0.3), 0, 1));
  const sc = zoomFrom + (zoomTo - zoomFrom) * zoomP;
  const exit = 1 - Easing.easeInCubic(clamp((localTime - duration + 0.5) / 0.5, 0, 1));
  return (
    <div style={{
      position: 'absolute', inset: 0,
      opacity: fade * exit,
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        WebkitMaskImage: `linear-gradient(90deg, black 0%, black ${maskP * 100}%, transparent ${maskP * 100 + 1.5}%)`,
        maskImage: `linear-gradient(90deg, black 0%, black ${maskP * 100}%, transparent ${maskP * 100 + 1.5}%)`,
        transform: `scale(${sc})`, transformOrigin: 'center',
      }}>
        <img src={src} style={{
          position: 'absolute', left: '50%', top: '50%',
          transform: 'translate(-50%, -50%)',
          width: '100%', height: '100%', objectFit: 'contain',
        }}/>
      </div>

      {/* scanning line */}
      {maskP > 0 && maskP < 1 && (
        <div style={{
          position: 'absolute', top: 0, bottom: 0,
          left: `${maskP * 100}%`, width: 2,
          background: C.accent,
          boxShadow: `0 0 20px ${C.accent}, 0 0 40px ${C.accent}`,
        }}/>
      )}
    </div>
  );
}

// ─── V2 · S5 · PIPELINE — using real frame 37 ─────────────────
function V2_S5_Pipeline({ start, dur }) {
  const end = start + dur;
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.bgDeep }} />
          <ParticleField count={40} seed={11} color={C.accent} speed={0.3} opacity={0.15}/>

          {/* Top kicker */}
          <Sprite start={0.1} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 100,
                  opacity: p,
                  display: 'flex', alignItems: 'center', gap: 32,
                }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 11, letterSpacing: '0.35em',
                    color: C.accent, textTransform: 'uppercase',
                  }}>ARCHITECTURE · FRAME 37/41</div>
                  <div style={{
                    width: 80, height: 1, background: C.border,
                  }}/>
                  <div style={{
                    fontFamily: F.mono, fontSize: 11, letterSpacing: '0.25em',
                    color: C.tx3, textTransform: 'uppercase',
                  }}>RAP · 7-LAYER PIPELINE</div>
                </div>
              );
            }}
          </Sprite>

          {/* Big display title */}
          <Sprite start={0.2} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 120,
                  fontFamily: F.display, fontSize: 120,
                  letterSpacing: '-0.035em', lineHeight: 0.88,
                  textTransform: 'uppercase', color: C.tx1,
                }}>
                  <div style={{ overflow: 'hidden' }}>
                    <div style={{ transform: `translateY(${(1 - clamp(lt / 0.5, 0, 1)) * 100}%)` }}>SEVEN LAYERS.</div>
                  </div>
                  <div style={{ overflow: 'hidden', color: C.accent }}>
                    <div style={{ transform: `translateY(${(1 - clamp((lt - 0.15) / 0.5, 0, 1)) * 100}%)` }}>ONE LOOP.</div>
                  </div>
                </div>
              );
            }}
          </Sprite>

          {/* THE DIAGRAM — framed, centered-bottom, large */}
          <div style={{
            position: 'absolute', left: 80, top: 360,
            width: 1760, height: 580,
            border: `1px solid ${C.border}`,
            background: 'rgba(0,0,0,0.35)',
            overflow: 'hidden',
          }}>
            <FramedDoc src="assets/37_rap_7_layer_pipeline.svg"
              revealStart={1.0} revealDur={2.0}
              zoomStart={3.0} zoomFrom={1.0} zoomTo={1.06}/>

            {/* corner crops */}
            <div style={{ position: 'absolute', top: 6, left: 6, width: 16, height: 16, borderTop: `2px solid ${C.accent}`, borderLeft: `2px solid ${C.accent}` }}/>
            <div style={{ position: 'absolute', top: 6, right: 6, width: 16, height: 16, borderTop: `2px solid ${C.accent}`, borderRight: `2px solid ${C.accent}` }}/>
            <div style={{ position: 'absolute', bottom: 6, left: 6, width: 16, height: 16, borderBottom: `2px solid ${C.accent}`, borderLeft: `2px solid ${C.accent}` }}/>
            <div style={{ position: 'absolute', bottom: 6, right: 6, width: 16, height: 16, borderBottom: `2px solid ${C.accent}`, borderRight: `2px solid ${C.accent}` }}/>

            {/* label bar */}
            <div style={{
              position: 'absolute', top: 0, right: 0,
              background: C.accent, color: C.bgDeep,
              fontFamily: F.mono, fontSize: 10, letterSpacing: '0.2em',
              padding: '4px 12px', fontWeight: 700,
              textTransform: 'uppercase',
            }}>ACTIVE · DIAGRAM</div>
          </div>

          {/* Side metrics that annotate the diagram */}
          <Sprite start={3.5} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const metrics = [
                { v: '25', u: 'DIM', l: 'FEATURE VEC', c: C.info },
                { v: '512', u: 'NCP', l: 'LTC UNITS',   c: C.cyan },
                { v: '32×4', u: 'HEAD', l: 'HOPFIELD',   c: C.accent },
                { v: '0.70', u: 'GATE', l: 'HUMILITY',   c: C.ok },
              ];
              return (
                <div style={{
                  position: 'absolute', right: 80, top: 220,
                  display: 'flex', flexDirection: 'column', gap: 14,
                }}>
                  {metrics.map((m, i) => {
                    const p = Easing.easeOutBack(clamp((lt - i * 0.1) / 0.5, 0, 1));
                    return (
                      <div key={i} style={{
                        opacity: p,
                        transform: `translateX(${(1 - p) * 20}px) scale(${0.9 + 0.1 * p})`,
                        padding: '14px 20px',
                        border: `1px solid ${m.c}66`,
                        background: `${m.c}0a`,
                        minWidth: 170,
                        fontFamily: F.mono,
                      }}>
                        <div style={{
                          fontSize: 10, letterSpacing: '0.3em',
                          color: m.c, textTransform: 'uppercase',
                        }}>{m.l}</div>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 6 }}>
                          <div style={{
                            fontFamily: F.display, fontSize: 40, lineHeight: 0.9,
                            color: C.tx1, letterSpacing: '-0.02em',
                          }}>{m.v}</div>
                          <div style={{ fontSize: 10, color: C.tx3, letterSpacing: '0.2em' }}>{m.u}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            }}
          </Sprite>

          <Chyron number="04" title="THE PIPELINE" subtitle="signal in. coaching out."/>
          <PersistentHud/>
        </>
      )}
    </Sprite>
  );
}

// ─── V2 · S6 · JEPA — using real frame 22 ────────────────────
function V2_S6_JEPA({ start, dur }) {
  const end = start + dur;
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.sunken }} />
          <ParticleField count={40} seed={21} color={C.cyan} speed={0.3} opacity={0.18}/>

          {/* Split layout: text left, diagram right */}
          <Sprite start={0.1} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 120,
                  width: 760,
                  opacity: p,
                }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 12, letterSpacing: '0.35em',
                    color: C.cyan, textTransform: 'uppercase', marginBottom: 28,
                  }}>JEPA · JOINT-EMBEDDING PREDICTIVE</div>
                  <div style={{
                    fontFamily: F.display, fontSize: 120, color: C.tx1,
                    letterSpacing: '-0.035em', lineHeight: 0.86, textTransform: 'uppercase',
                  }}>
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ transform: `translateY(${(1 - clamp(lt / 0.5, 0, 1)) * 100}%)` }}>PREDICT IN</div>
                    </div>
                    <div style={{ overflow: 'hidden', color: C.accent }}>
                      <div style={{ transform: `translateY(${(1 - clamp((lt - 0.15) / 0.5, 0, 1)) * 100}%)` }}>LATENT SPACE.</div>
                    </div>
                  </div>
                  <div style={{
                    marginTop: 48,
                    fontFamily: F.serif, fontSize: 30, fontStyle: 'italic',
                    color: C.tx2, lineHeight: 1.35, fontWeight: 300,
                    letterSpacing: '-0.005em',
                    opacity: Easing.easeOutCubic(clamp((lt - 0.8) / 0.6, 0, 1)),
                  }}>
                    No pixel reconstruction.<br/>
                    No wasted compute.<br/>
                    Just <span style={{ color: C.accent, fontStyle: 'normal', fontWeight: 600 }}>intent</span>, encoded.
                  </div>

                  {/* pill row */}
                  <div style={{
                    marginTop: 48,
                    display: 'flex', flexWrap: 'wrap', gap: 10,
                    opacity: Easing.easeOutCubic(clamp((lt - 1.3) / 0.6, 0, 1)),
                  }}>
                    {['target_encoder frozen', 'EMA update', 'requires_grad=False', 'NN-JM-04'].map((tag, i) => (
                      <div key={i} style={{
                        fontFamily: F.mono, fontSize: 11, letterSpacing: '0.15em',
                        color: C.cyan, padding: '6px 14px',
                        border: `1px solid ${C.cyan}66`,
                        background: 'rgba(0,204,255,0.05)',
                        textTransform: 'uppercase',
                      }}>{tag}</div>
                    ))}
                  </div>
                </div>
              );
            }}
          </Sprite>

          {/* Diagram right side */}
          <div style={{
            position: 'absolute', right: 80, top: 120,
            width: 940, height: 720,
            border: `1px solid ${C.border}`,
            background: 'rgba(0,0,0,0.35)',
            overflow: 'hidden',
          }}>
            <FramedDoc src="assets/22_jepa_architecture.svg"
              revealStart={0.8} revealDur={1.6}
              zoomStart={2.5} zoomFrom={1.0} zoomTo={1.04}/>
            <div style={{
              position: 'absolute', top: 0, right: 0,
              background: C.cyan, color: C.bgDeep,
              fontFamily: F.mono, fontSize: 10, letterSpacing: '0.2em',
              padding: '4px 12px', fontWeight: 700,
              textTransform: 'uppercase',
            }}>FRAME · 22</div>
          </div>

          <Chyron number="04" title="JEPA" subtitle="embedding over reconstruction."/>
          <PersistentHud/>
        </>
      )}
    </Sprite>
  );
}

// ─── V2 · S7 · INVARIANTS + feature vector using frames 24 + 29 ───
function V2_S7_Invariants({ start, dur }) {
  const end = start + dur;
  const items = [
    { code: 'P-RSB-03',     rule: 'round_won EXCLUDED from all 25 dims',       c: C.err },
    { code: 'NN-MEM-01',    rule: 'Hopfield bypassed until ≥2 forwards',        c: C.warn },
    { code: 'NN-16',        rule: 'EMA apply_shadow() must .clone()',           c: C.accent },
    { code: 'NN-JM-04',     rule: 'target_encoder requires_grad=False',         c: C.cyan },
    { code: 'DS-12',        rule: 'MIN_DEMO_SIZE = 10 MB',                      c: C.info },
    { code: 'P-VEC-02',     rule: 'NaN/Inf clamp · >5% → DataQualityError',     c: C.err },
    { code: 'METADATA_DIM', rule: 'sole source: vectorizer.py:32',              c: C.ok },
  ];
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.base }} />
          <ParticleField count={30} seed={37} color={C.err} speed={0.2} opacity={0.12}/>

          {/* Title */}
          <Sprite start={0.1} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 120, opacity: p,
                }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 12, letterSpacing: '0.35em',
                    color: C.err, textTransform: 'uppercase', marginBottom: 24,
                  }}>RULES · HARDCODED · NON-NEGOTIABLE</div>
                  <div style={{
                    fontFamily: F.display, fontSize: 140, color: C.tx1,
                    letterSpacing: '-0.04em', lineHeight: 0.88, textTransform: 'uppercase',
                  }}>
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ transform: `translateY(${(1 - clamp(lt / 0.5, 0, 1)) * 100}%)` }}>SEVEN</div>
                    </div>
                    <div style={{ overflow: 'hidden', color: C.accent }}>
                      <div style={{ transform: `translateY(${(1 - clamp((lt - 0.15) / 0.5, 0, 1)) * 100}%)` }}>INVARIANTS.</div>
                    </div>
                  </div>
                </div>
              );
            }}
          </Sprite>

          {/* 25-dim vector visual on left-bottom */}
          <Sprite start={1.0} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.8, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 620, width: 720, height: 320,
                  opacity: p,
                  border: `1px solid ${C.border}`,
                  background: 'rgba(0,0,0,0.3)',
                  overflow: 'hidden',
                }}>
                  <FramedDoc src="assets/24_feature_vector_25dim.svg"
                    revealStart={0} revealDur={1.2}
                    zoomStart={1.5} zoomFrom={1.0} zoomTo={1.04}/>
                  <div style={{
                    position: 'absolute', top: 10, left: 14,
                    fontFamily: F.mono, fontSize: 10, letterSpacing: '0.25em',
                    color: C.accent, textTransform: 'uppercase',
                    background: 'rgba(20,20,30,0.85)',
                    padding: '4px 10px',
                  }}>FRAME 24 · 25-DIM VECTOR</div>
                </div>
              );
            }}
          </Sprite>

          {/* Invariants list right */}
          {items.map((it, i) => {
            const iStart = 1.0 + i * 0.15;
            return (
              <Sprite key={it.code} start={iStart} end={dur - 0.3} keepMounted>
                {({ localTime: lt }) => {
                  const p = Easing.easeOutQuart(clamp(lt / 0.5, 0, 1));
                  return (
                    <div style={{
                      position: 'absolute',
                      left: 920, top: 220 + i * 78,
                      width: 920,
                      display: 'flex', alignItems: 'center', gap: 18,
                      fontFamily: F.mono,
                      opacity: p, transform: `translateX(${(1 - p) * -30}px)`,
                    }}>
                      <div style={{
                        fontSize: 12, letterSpacing: '0.15em',
                        color: it.c,
                        padding: '10px 16px',
                        border: `1px solid ${it.c}`,
                        minWidth: 170, textAlign: 'center',
                        background: `${it.c}0a`,
                      }}>{it.code}</div>
                      <div style={{
                        flex: 1, height: 1, background: C.border,
                        transform: `scaleX(${clamp((lt - 0.2) / 0.4, 0, 1)})`,
                        transformOrigin: 'left',
                      }}/>
                      <div style={{
                        fontSize: 17, color: C.tx1,
                        letterSpacing: '0.02em',
                        opacity: clamp((lt - 0.3) / 0.4, 0, 1),
                      }}>{it.rule}</div>
                    </div>
                  );
                }}
              </Sprite>
            );
          })}

          <Chyron number="04" title="GUARDRAILS" subtitle="the non-negotiables."/>
          <PersistentHud/>
        </>
      )}
    </Sprite>
  );
}

Object.assign(window, { V2_S5_Pipeline, V2_S6_JEPA, V2_S7_Invariants });
