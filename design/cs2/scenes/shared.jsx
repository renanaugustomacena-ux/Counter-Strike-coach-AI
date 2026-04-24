// shared.jsx — base tokens + minimal primitives
// ──────────────────────────────────────────────

const T = {
  base:    '#14141e',
  raised:  '#1a1a2e',
  sunken:  '#0f0f2e',
  accent:  '#d96600',
  accentHi:'#e67a1a',
  accentLo:'#b85500',
  tx1: '#dcdcdc',
  tx2: '#a0a0b0',
  tx3: '#6b6b7a',
  ok:  '#4caf50',
  warn:'#ffaa00',
  err: '#ff4444',
  info:'#4a9eff',
  cyan:'#00ccff',
  border: '#3a3a5a',
};

function Scanlines({ opacity = 0.04 }) {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      backgroundImage: 'repeating-linear-gradient(0deg, rgba(255,255,255,0.5) 0 1px, transparent 1px 3px)',
      opacity, pointerEvents: 'none', mixBlendMode: 'overlay',
    }} />
  );
}

function Vignette({ strength = 0.6 }) {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      background: `radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,${strength}) 100%)`,
      pointerEvents: 'none',
    }} />
  );
}

// Bottom progress bar spanning whole timeline
function ProgressBar({ total, duration }) {
  const t = useTime();
  const p = Math.min(1, t / duration);
  return (
    <div style={{
      position: 'absolute', left: 80, right: 80, bottom: 32,
      height: 14, display: 'flex', alignItems: 'center', gap: 12,
      fontFamily: "'JetBrains Mono', monospace", color: T.tx3, fontSize: 10,
      letterSpacing: '0.2em', textTransform: 'uppercase',
      pointerEvents: 'none',
    }}>
      <span>00:00</span>
      <div style={{ flex: 1, position: 'relative', height: 2, background: 'rgba(255,255,255,0.08)' }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${p * 100}%`, background: T.accent,
        }}/>
        {Array.from({ length: total + 1 }).map((_, i) => (
          <div key={i} style={{
            position: 'absolute', top: -4, bottom: -4,
            left: `${(i / total) * 100}%`,
            width: 1, background: 'rgba(255,255,255,0.2)',
          }}/>
        ))}
      </div>
      <span>{String(Math.floor(duration/60)).padStart(2,'0')}:{String(Math.floor(duration%60)).padStart(2,'0')}</span>
    </div>
  );
}

Object.assign(window, { T, Scanlines, Vignette, ProgressBar });
