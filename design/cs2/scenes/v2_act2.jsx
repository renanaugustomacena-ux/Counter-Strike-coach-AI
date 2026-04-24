// v2_act2.jsx — ACT 2: Product reel (cinematic showcase)
// ───────────────────────────────────────────────────────
// Strategy: treat each screen as a "specimen" — fullbleed,
// tilted slightly, with active telemetry/annotations overlaid.

// A cinematic product screen card
function ProductSpecimen({ src, caption, kicker, color = C.accent, side = 'left', lt, dur }) {
  const p  = Easing.easeOutCubic(clamp(lt / 0.5, 0, 1));
  const x  = Easing.easeInOutCubic(clamp(lt / dur, 0, 1));
  const exit = 1 - Easing.easeInCubic(clamp((lt - dur + 0.4) / 0.4, 0, 1));
  // Slow ken-burns
  const sc = 1.03 + 0.04 * x;
  const py = -8 * x;

  const imgStyle = {
    position: 'absolute',
    left: side === 'left' ? 80 : 720,
    top: 120,
    width: 1120, height: 780,
    border: `1px solid ${color}55`,
    background: '#000',
    overflow: 'hidden',
    opacity: p * exit,
    transform: `translateY(${(1 - p) * 20}px)`,
    boxShadow: `0 40px 100px rgba(0,0,0,0.7), 0 0 0 1px ${color}22`,
  };
  const textX = side === 'left' ? 1250 : 80;

  return (
    <>
      <div style={imgStyle}>
        <div style={{
          position: 'absolute', inset: 0,
          transform: `scale(${sc}) translateY(${py}px)`,
          transformOrigin: 'center',
        }}>
          <img src={src} style={{
            width: '100%', height: '100%', objectFit: 'contain',
            background: '#0f0f2e',
          }}/>
        </div>
        {/* corner ticks */}
        <div style={{ position: 'absolute', top: 6, left: 6, width: 14, height: 14, borderTop: `2px solid ${color}`, borderLeft: `2px solid ${color}` }}/>
        <div style={{ position: 'absolute', top: 6, right: 6, width: 14, height: 14, borderTop: `2px solid ${color}`, borderRight: `2px solid ${color}` }}/>
        <div style={{ position: 'absolute', bottom: 6, left: 6, width: 14, height: 14, borderBottom: `2px solid ${color}`, borderLeft: `2px solid ${color}` }}/>
        <div style={{ position: 'absolute', bottom: 6, right: 6, width: 14, height: 14, borderBottom: `2px solid ${color}`, borderRight: `2px solid ${color}` }}/>

        {/* scan reveal */}
        <div style={{
          position: 'absolute', inset: 0,
          background: `linear-gradient(90deg, transparent ${x * 100}%, ${color}66 ${x * 100}%, transparent ${x * 100 + 1}%)`,
          opacity: x < 1 ? 0.8 : 0,
          pointerEvents: 'none',
        }}/>
      </div>

      <div style={{
        position: 'absolute',
        left: textX, top: 180, width: 550,
        opacity: p * exit,
        transform: `translateY(${(1 - p) * 20}px)`,
      }}>
        <div style={{
          fontFamily: F.mono, fontSize: 11, letterSpacing: '0.35em',
          color, textTransform: 'uppercase', marginBottom: 24,
        }}>{kicker}</div>
        <div style={{
          fontFamily: F.display, fontSize: 108, color: C.tx1,
          letterSpacing: '-0.035em', lineHeight: 0.86,
          textTransform: 'uppercase',
        }}>
          {caption.split(' ').map((w, i) => {
            const wp = Easing.easeOutQuart(clamp((lt - 0.3 - i * 0.08) / 0.5, 0, 1));
            return (
              <span key={i} style={{ display: 'inline-block', overflow: 'hidden', marginRight: 14 }}>
                <span style={{
                  display: 'inline-block',
                  transform: `translateY(${(1 - wp) * 100}%)`,
                }}>{w}</span>
              </span>
            );
          })}
        </div>
      </div>
    </>
  );
}

function V2_S4_ProductReel({ start, dur }) {
  const end = start + dur;
  // 5 specimens, ~6s each with overlap
  const specimens = [
    { src: 'assets/06_coach.svg',            k: 'SCREEN · 06 · COACH',         cap: 'the cockpit.',     side: 'left',  color: C.accent, s: 0.2,  d: 6.5 },
    { src: 'assets/09_match_detail_overview.svg', k: 'SCREEN · 09 · MATCH',   cap: 'autopsy, not replay.', side: 'right', color: C.info,   s: 6.5,  d: 6.5 },
    { src: 'assets/13_tactical_viewer.svg',  k: 'SCREEN · 13 · TACTICAL',      cap: 'see the map.',     side: 'left',  color: C.cyan,   s: 13.0, d: 6.5 },
    { src: 'assets/15_pro_comparison.svg',   k: 'SCREEN · 15 · COMPARE',       cap: 'pro vs. you.',     side: 'right', color: C.warn,   s: 19.5, d: 6.5 },
    { src: 'assets/12_performance.svg',      k: 'SCREEN · 12 · PROGRESS',      cap: 'skill over time.', side: 'left',  color: C.ok,     s: 26.0, d: 6.5 },
  ];

  return (
    <Sprite start={start} end={end}>
      {({ localTime }) => (
        <>
          <div style={{ position: 'absolute', inset: 0, background: C.bgDeep }} />
          <ParticleField count={35} seed={5} color={C.accent} speed={0.25} opacity={0.15}/>

          {/* scene-specific counter (top-right), below hud */}
          <div style={{
            position: 'absolute', right: 80, top: 100,
            fontFamily: F.mono, fontSize: 11, letterSpacing: '0.3em',
            color: C.tx3, textTransform: 'uppercase', textAlign: 'right',
          }}>
            SPEC · {String(Math.min(5, Math.floor(localTime / 6.5) + 1)).padStart(2,'0')} / 05
          </div>

          {/* running specimens */}
          {specimens.map((sp, i) => {
            const spEnd = sp.s + sp.d;
            if (localTime < sp.s - 0.3 || localTime > spEnd) return null;
            const lt = localTime - sp.s;
            return (
              <ProductSpecimen
                key={i}
                src={sp.src}
                caption={sp.cap}
                kicker={sp.k}
                color={sp.color}
                side={sp.side}
                lt={lt}
                dur={sp.d}
              />
            );
          })}

          {/* live telemetry always on — above chyron zone */}
          <div style={{ position: 'absolute', left: 80, top: 920 }}>
            <div style={{
              fontFamily: F.mono, fontSize: 10, letterSpacing: '0.3em',
              color: C.tx3, textTransform: 'uppercase', marginBottom: 6,
            }}>LIVE · INFERENCE</div>
            <LiveBars x={0} y={0} width={420} height={28} bars={32} color={C.accent} seed={7}/>
          </div>
          <div style={{ position: 'absolute', right: 80, top: 920 }}>
            <div style={{
              fontFamily: F.mono, fontSize: 10, letterSpacing: '0.3em',
              color: C.tx3, textTransform: 'uppercase', marginBottom: 6, textAlign: 'right',
            }}>CONFIDENCE · SIGNAL</div>
            <Oscilloscope x={0} y={0} width={420} height={28} color={C.accent} amp={0.4}/>
          </div>

          <Chyron number="03" title="THE PRODUCT" subtitle="ten screens. one cockpit."/>
          <PersistentHud/>
          <Vignette strength={0.5}/>
        </>
      )}
    </Sprite>
  );
}

Object.assign(window, { V2_S4_ProductReel });
