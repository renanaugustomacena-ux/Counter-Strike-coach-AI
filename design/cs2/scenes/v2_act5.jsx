// v2_act5.jsx — ACT 5: Design system flash + closing
// ────────────────────────────────────────────────────

function V2_S9_DesignSystem({ start, dur }) {
  const end = start + dur;
  const tiles = [
    { src: 'assets/31_token_system.svg',   label: 'TOKENS',     sub: 'colors · space · radii' },
    { src: 'assets/32_theme_grid.svg',     label: 'THEMES',     sub: 'dark · accent · semantics' },
    { src: 'assets/33_component_library.svg', label: 'COMPONENTS', sub: 'buttons · cards · forms' },
    { src: 'assets/34_chart_library.svg',  label: 'CHARTS',     sub: 'live data surfaces' },
    { src: 'assets/35_icon_grid.svg',      label: 'ICONS',      sub: 'sharp · 1.5px stroke' },
    { src: 'assets/36_typography_specimen.svg', label: 'TYPE',   sub: 'display · serif · mono' },
  ];
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.base }} />
          <ParticleField count={30} seed={61} color={C.accent} speed={0.25} opacity={0.12}/>

          {/* Title */}
          <Sprite start={0.1} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 90, opacity: p,
                }}>
                  <div style={{
                    fontFamily: F.mono, fontSize: 12, letterSpacing: '0.35em',
                    color: C.accent, textTransform: 'uppercase', marginBottom: 20,
                  }}>THE SYSTEM</div>
                  <div style={{
                    fontFamily: F.display, fontSize: 130, color: C.tx1,
                    letterSpacing: '-0.03em', lineHeight: 0.9, textTransform: 'uppercase',
                    display: 'flex', alignItems: 'baseline', gap: 32,
                  }}>
                    <span>ONE LANGUAGE.</span>
                    <span style={{ color: C.accent, fontSize: 76 }}>—</span>
                    <span style={{ color: C.accent }}>EVERY SURFACE.</span>
                  </div>
                </div>
              );
            }}
          </Sprite>

          {/* Tiles row */}
          {tiles.map((t, i) => {
            const tStart = 0.7 + i * 0.15;
            return (
              <Sprite key={i} start={tStart} end={dur - 0.3} keepMounted>
                {({ localTime: lt }) => {
                  const p = Easing.easeOutQuart(clamp(lt / 0.6, 0, 1));
                  return (
                    <div style={{
                      position: 'absolute',
                      left: 80 + i * 298, top: 370,
                      width: 280, height: 560,
                      opacity: p,
                      transform: `translateY(${(1 - p) * 30}px)`,
                      border: `1px solid ${C.border}`,
                      background: C.raised,
                      overflow: 'hidden',
                      display: 'flex', flexDirection: 'column',
                    }}>
                      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', background: C.sunken }}>
                        <img src={t.src} style={{
                          position: 'absolute', inset: 0,
                          width: '100%', height: '100%', objectFit: 'cover',
                          objectPosition: 'top left',
                          transform: `scale(${1.1 + 0.05 * Math.sin(lt * 0.8 + i)})`,
                          transformOrigin: 'top left',
                        }}/>
                        <div style={{
                          position: 'absolute', inset: 0,
                          background: `linear-gradient(180deg, transparent 60%, ${C.raised} 100%)`,
                        }}/>
                      </div>
                      <div style={{ padding: '22px 24px', borderTop: `1px solid ${C.border}` }}>
                        <div style={{
                          fontFamily: F.mono, fontSize: 10, letterSpacing: '0.3em',
                          color: C.accent, textTransform: 'uppercase',
                        }}>FRAME · {31 + i}</div>
                        <div style={{
                          fontFamily: F.display, fontSize: 38,
                          color: C.tx1, letterSpacing: '-0.015em',
                          lineHeight: 1, marginTop: 8,
                          textTransform: 'uppercase',
                        }}>{t.label}</div>
                        <div style={{
                          fontFamily: F.mono, fontSize: 11, letterSpacing: '0.15em',
                          color: C.tx2, marginTop: 6,
                        }}>{t.sub}</div>
                      </div>
                    </div>
                  );
                }}
              </Sprite>
            );
          })}

          <Chyron number="06" title="THE SYSTEM" subtitle="pixel-perfect, end to end."/>
          <PersistentHud/>
        </>
      )}
    </Sprite>
  );
}

function V2_S10_Closing({ start, dur }) {
  const end = start + dur;
  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.bgDeep }} />
          <ParticleField count={100} seed={99} color={C.accent} speed={0.5} opacity={0.35}/>
          <RadarSweep cx={960} cy={540} r={700} color={C.accent} speed={0.3}/>

          {/* Stat line */}
          <Sprite start={0.1} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 120, opacity: p,
                  display: 'flex', gap: 80,
                }}>
                  {[
                    { k: '41', u: 'FRAMES' },
                    { k: '7', u: 'LAYERS' },
                    { k: '25', u: 'DIMS' },
                    { k: '0.70', u: 'GATE' },
                  ].map((s, i) => {
                    const sp = Easing.easeOutQuart(clamp((lt - i * 0.1) / 0.6, 0, 1));
                    return (
                      <div key={i} style={{ opacity: sp, transform: `translateY(${(1 - sp) * 10}px)` }}>
                        <div style={{
                          fontFamily: F.display, fontSize: 86, color: C.tx1,
                          letterSpacing: '-0.03em', lineHeight: 0.9,
                          fontVariantNumeric: 'tabular-nums',
                        }}>{s.k}</div>
                        <div style={{
                          fontFamily: F.mono, fontSize: 10, letterSpacing: '0.35em',
                          color: C.accent, textTransform: 'uppercase', marginTop: 6,
                        }}>{s.u}</div>
                      </div>
                    );
                  })}
                </div>
              );
            }}
          </Sprite>

          {/* Big close line */}
          <Sprite start={1.2} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const lines = ['COACHING', 'THAT KNOWS', 'WHEN TO STAY', 'SILENT.'];
              // Fade heading OUT as lockup fades IN (handover at lt≈3.3, since local start=1.2)
              const fadeOut = 1 - Easing.easeInCubic(clamp((lt - 3.0) / 0.8, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 250,
                  fontFamily: F.display, fontSize: 160, color: C.tx1,
                  letterSpacing: '-0.04em', lineHeight: 0.92,
                  textTransform: 'uppercase',
                  opacity: fadeOut,
                }}>
                  {lines.map((w, i) => {
                    const wp = Easing.easeOutQuart(clamp((lt - i * 0.2) / 0.7, 0, 1));
                    const isAccent = i === 3;
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

          {/* Bottom logo lockup — appears AFTER heading fades out */}
          <Sprite start={4.5} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.8, 0, 1));
              return (
                <div style={{
                  position: 'absolute', left: 80, top: 280,
                  display: 'flex', alignItems: 'flex-end', gap: 60,
                  opacity: p,
                }}>
                  <div>
                    <div style={{ width: p * 220, height: 4, background: C.accent, marginBottom: 28 }}/>
                    <div style={{
                      fontFamily: F.display, fontSize: 180, color: C.tx1,
                      letterSpacing: '-0.03em', lineHeight: 0.88, textTransform: 'uppercase',
                      textShadow: `0 0 40px ${C.accent}66`,
                    }}>MACENA</div>
                    <div style={{
                      fontFamily: F.mono, fontSize: 16, letterSpacing: '0.6em',
                      color: C.accent, textTransform: 'uppercase', marginTop: 20,
                    }}>CS2 · COACH · AI</div>
                  </div>
                  <div style={{
                    fontFamily: F.serif, fontStyle: 'italic', fontSize: 30,
                    color: C.tx2, fontWeight: 300,
                    maxWidth: 500, lineHeight: 1.3,
                    paddingLeft: 40, borderLeft: `1px solid ${C.border}`,
                    marginBottom: 20,
                  }}>
                    &ldquo;We'd rather ship silence<br/>than confident noise.&rdquo;
                  </div>
                </div>
              );
            }}
          </Sprite>

          {/* timecode marker */}
          <Sprite start={6.0} end={dur - 0.3} keepMounted>
            {({ localTime: lt }) => {
              const p = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
              return (
                <div style={{
                  position: 'absolute', right: 80, top: 720, opacity: p,
                  fontFamily: F.mono, fontSize: 11, letterSpacing: '0.3em',
                  color: C.tx3, textTransform: 'uppercase', textAlign: 'right',
                }}>
                  <div style={{ color: C.accent, marginBottom: 8 }}>END OF REEL</div>
                  <div>macena.coach_ai · build 2026.04</div>
                  <div>reel v2 · 02:00</div>
                </div>
              );
            }}
          </Sprite>

          <Vignette strength={0.7}/>
          <Scanlines opacity={0.04}/>
          <PersistentHud/>
        </>
      )}
    </Sprite>
  );
}

Object.assign(window, { V2_S9_DesignSystem, V2_S10_Closing });
