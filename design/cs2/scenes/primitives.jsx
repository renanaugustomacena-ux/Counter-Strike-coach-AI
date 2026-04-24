// primitives.jsx — v2 animation primitives
// ──────────────────────────────────────────

const F = {
  display: "'Anton', 'Oswald', 'Arial Narrow', Impact, sans-serif",
  serif:   "'Fraunces', 'Playfair Display', Georgia, serif",
  sans:    "'Roboto', Inter, system-ui, sans-serif",
  mono:    "'JetBrains Mono', 'Fira Code', Consolas, monospace",
};

const C = {
  ...T,
  bgDeep:  '#0a0a14',
  glow:    '#ff8833',
  hot:     '#ff5522',
};

// Drifting particle field
function ParticleField({ count = 60, seed = 1, color = C.accent, speed = 0.3, opacity = 0.25 }) {
  const t = useTime();
  const particles = React.useMemo(() => {
    const ps = []; let s = seed * 9301 + 49297;
    const rand = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    for (let i = 0; i < count; i++) {
      ps.push({
        x: rand() * 1920, y: rand() * 1080,
        r: 1 + rand() * 2.5,
        vx: (rand() - 0.5) * 20, vy: (rand() - 0.5) * 20,
        ph: rand() * Math.PI * 2, freq: 0.3 + rand() * 1.5,
      });
    }
    return ps;
  }, [count, seed]);
  return (
    <svg style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} width="1920" height="1080">
      {particles.map((p, i) => {
        const x = ((p.x + p.vx * t * speed) % 1920 + 1920) % 1920;
        const y = ((p.y + p.vy * t * speed) % 1080 + 1080) % 1080;
        const o = opacity * (0.4 + 0.6 * (0.5 + 0.5 * Math.sin(t * p.freq + p.ph)));
        return <circle key={i} cx={x} cy={y} r={p.r} fill={color} opacity={o}/>;
      })}
    </svg>
  );
}

// Live telemetry scroller
function TelemetryScroller({ x, y, width = 320, height = 400, opacity = 0.5 }) {
  const t = useTime();
  const lines = React.useMemo(() => {
    const out = [];
    const tags = ['PERC', 'MEM', 'POL', 'CHR', 'GATE', 'VEC', 'LTC', 'HOP', 'EMA'];
    const ops  = ['forward', 'target_encode', 'scan_192', 'scan_64', 'scan_640', 'recall', 'clamp', 'critique', 'score'];
    let s = 1;
    const r = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    for (let i = 0; i < 80; i++) {
      const conf = (0.3 + r() * 0.7).toFixed(3);
      out.push({
        ts: (i * 0.13).toFixed(2),
        tag: tags[Math.floor(r() * tags.length)],
        op:  ops[Math.floor(r() * ops.length)],
        dim: Math.floor(r() * 154),
        conf, pass: parseFloat(conf) >= 0.7,
      });
    }
    return out;
  }, []);
  const scroll = (t * 30) % (lines.length * 22);
  return (
    <div style={{
      position: 'absolute', left: x, top: y, width, height,
      overflow: 'hidden', opacity,
      fontFamily: F.mono, fontSize: 11, lineHeight: '22px',
      color: C.tx2,
      maskImage: 'linear-gradient(180deg, transparent, black 20%, black 80%, transparent)',
      WebkitMaskImage: 'linear-gradient(180deg, transparent, black 20%, black 80%, transparent)',
    }}>
      <div style={{ transform: `translateY(-${scroll}px)` }}>
        {[...lines, ...lines].map((l, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, height: 22, whiteSpace: 'nowrap' }}>
            <span style={{ color: C.tx3, width: 42 }}>{l.ts}</span>
            <span style={{ color: C.accent, width: 44 }}>{l.tag}</span>
            <span style={{ color: C.tx2, flex: 1 }}>{l.op}</span>
            <span style={{ color: C.tx3, width: 30 }}>d{l.dim}</span>
            <span style={{ color: l.pass ? C.ok : C.warn, width: 44, textAlign: 'right' }}>{l.conf}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Oscilloscope — loops
function Oscilloscope({ x, y, width, height, color = C.accent, amp = 0.4 }) {
  const t = useTime();
  const points = []; const N = 120;
  for (let i = 0; i < N; i++) {
    const px = (i / (N - 1)) * width;
    const py = height / 2
      + Math.sin(i * 0.15 + t * 3) * height * amp * 0.5
      + Math.sin(i * 0.45 + t * 5) * height * amp * 0.25
      + Math.sin(i * 0.08 + t * 1.8) * height * amp * 0.15;
    points.push(`${px},${py}`);
  }
  return (
    <svg style={{ position: 'absolute', left: x, top: y }} width={width} height={height}>
      <polyline points={points.join(' ')} fill="none" stroke={color} strokeWidth="1.5" opacity="0.7"/>
      <polyline points={points.join(' ')} fill="none" stroke={color} strokeWidth="4" opacity="0.2"/>
    </svg>
  );
}

function LiveBars({ x, y, width, height, bars = 24, color = C.accent, seed = 1 }) {
  const t = useTime();
  const values = React.useMemo(() => {
    const out = []; let s = seed * 9301 + 49297;
    const r = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    for (let i = 0; i < bars; i++) out.push({ base: 0.2 + r() * 0.8, ph: r() * Math.PI * 2, freq: 0.5 + r() * 1.5 });
    return out;
  }, [bars, seed]);
  const gap = 3, bw = (width - gap * (bars - 1)) / bars;
  return (
    <svg style={{ position: 'absolute', left: x, top: y }} width={width} height={height}>
      {values.map((v, i) => {
        const h = height * v.base * (0.6 + 0.4 * (0.5 + 0.5 * Math.sin(t * v.freq + v.ph)));
        return <rect key={i} x={i * (bw + gap)} y={height - h} width={bw} height={h} fill={color} opacity={0.3 + v.base * 0.5}/>;
      })}
    </svg>
  );
}

// Typewriter
function Typewriter({ x, y, text, start = 0, cps = 40, size = 16, color = C.tx1, font = F.mono, prefix = '' }) {
  const { localTime } = useSprite();
  const chars = Math.floor(Math.max(0, localTime - start) * cps);
  const shown = text.slice(0, chars);
  const cursor = localTime >= start && Math.floor(localTime * 2) % 2 === 0;
  return (
    <div style={{
      position: 'absolute', left: x, top: y,
      fontFamily: font, fontSize: size, color, whiteSpace: 'pre',
    }}>
      {prefix && <span style={{ color: C.accent, marginRight: 8 }}>{prefix}</span>}
      {shown}
      {cursor && chars < text.length && <span style={{
        display: 'inline-block', width: 8, height: '1em',
        background: C.accent, verticalAlign: 'middle',
      }}/>}
    </div>
  );
}

// Radar sweep
function RadarSweep({ cx, cy, r, color = C.accent, speed = 1 }) {
  const t = useTime();
  const angle = (t * speed * 60) % 360;
  return (
    <svg style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} width="1920" height="1080">
      <defs>
        <radialGradient id="radar-grad" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor={color} stopOpacity="0.3"/>
          <stop offset="100%" stopColor={color} stopOpacity="0"/>
        </radialGradient>
      </defs>
      {[0.3, 0.6, 1].map((m, i) => (
        <circle key={i} cx={cx} cy={cy} r={r * m}
          fill="none" stroke={color} strokeWidth="1" opacity={0.15}
          strokeDasharray="4 8"/>
      ))}
      <line x1={cx - r} y1={cy} x2={cx + r} y2={cy} stroke={color} strokeWidth="1" opacity="0.1"/>
      <line x1={cx} y1={cy - r} x2={cx} y2={cy + r} stroke={color} strokeWidth="1" opacity="0.1"/>
      <g transform={`rotate(${angle} ${cx} ${cy})`}>
        <line x1={cx} y1={cy} x2={cx + r} y2={cy} stroke={color} strokeWidth="2" opacity="0.8"/>
      </g>
    </svg>
  );
}

// Kinetic number
function KineticNumber({ x, y, to, start = 0, dur = 1.4, size = 240, color = C.accent, suffix = '', prefix = '', format = v => Math.round(v).toLocaleString() }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutQuart(clamp((localTime - start) / dur, 0, 1));
  const v = to * p;
  return (
    <div style={{
      position: 'absolute', left: x, top: y,
      fontFamily: F.display, fontSize: size, fontWeight: 400, color,
      letterSpacing: '-0.03em', lineHeight: 0.9,
      fontVariantNumeric: 'tabular-nums',
    }}>
      {prefix}{format(v)}{suffix}
    </div>
  );
}

// Chyron (lower third) — single-line, occupies the reserved bottom band at y≈1000
// RESERVED ZONE: y=980..1030, across the full width. Do not place other elements here.
function Chyron({ number, title, subtitle }) {
  const { localTime, duration } = useSprite();
  const p = Easing.easeOutCubic(clamp(localTime / 0.6, 0, 1));
  const o = 1 - Easing.easeInCubic(clamp((localTime - (duration - 0.6)) / 0.5, 0, 1));
  return (
    <div style={{
      position: 'absolute', left: 80, right: 80, bottom: 58,
      opacity: o, pointerEvents: 'none',
      display: 'flex', alignItems: 'center', gap: 22,
      height: 28,
    }}>
      <div style={{ width: p * 60, height: 2, background: C.accent, flexShrink: 0 }}/>
      <div style={{
        fontFamily: F.mono, fontSize: 11, letterSpacing: '0.35em',
        color: C.accent, textTransform: 'uppercase', opacity: p,
        flexShrink: 0,
      }}>{number}</div>
      <div style={{
        fontFamily: F.display, fontSize: 22, color: C.tx1,
        letterSpacing: '0.02em', lineHeight: 1, textTransform: 'uppercase',
        opacity: p, flexShrink: 0,
      }}>{title}</div>
      {subtitle && (
        <>
          <div style={{ width: 20, height: 1, background: C.border, opacity: p, flexShrink: 0 }}/>
          <div style={{
            fontFamily: F.mono, fontSize: 11, letterSpacing: '0.2em',
            color: C.tx2, textTransform: 'uppercase', opacity: p,
          }}>{subtitle}</div>
        </>
      )}
    </div>
  );
}

// Persistent HUD corners + timecode
function PersistentHud() {
  const t = useTime();
  return (
    <>
      <div style={{
        position: 'absolute', top: 40, left: 40,
        fontFamily: F.mono, fontSize: 10, letterSpacing: '0.3em',
        color: C.tx3, textTransform: 'uppercase',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          width: 8, height: 8, background: C.accent,
          opacity: Math.floor(t * 2) % 2 === 0 ? 1 : 0.3,
        }}/>
        <span>MACENA / CS2-COACH-AI</span>
        <span style={{ color: C.tx3 }}>·</span>
        <span style={{ color: C.accent }}>PROMO REEL</span>
      </div>
      <div style={{
        position: 'absolute', top: 40, right: 40,
        fontFamily: F.mono, fontSize: 10, letterSpacing: '0.3em',
        color: C.tx3, textTransform: 'uppercase', textAlign: 'right',
      }}>
        TC · <span style={{ color: C.tx1, fontVariantNumeric: 'tabular-nums' }}>
          {String(Math.floor(t / 60)).padStart(2,'0')}:
          {String(Math.floor(t % 60)).padStart(2,'0')}:
          {String(Math.floor((t * 100) % 100)).padStart(2,'0')}
        </span>
      </div>
      <div style={{
        position: 'absolute', left: 20, top: '50%',
        transform: 'translateY(-50%)',
        fontFamily: F.mono, fontSize: 10, letterSpacing: '0.4em',
        color: C.tx3, textTransform: 'uppercase',
        writingMode: 'vertical-rl',
      }}>16:9 · 1920 × 1080 · v2</div>
    </>
  );
}

Object.assign(window, {
  F, C,
  ParticleField, TelemetryScroller, Oscilloscope, LiveBars,
  Typewriter, RadarSweep, KineticNumber,
  Chyron, PersistentHud,
});
