// main.jsx — assembles all scenes into the Stage
// ────────────────────────────────────────────────

// Scene timing table — total duration computed below.
// Each block is [sceneFn, durationInSeconds]
const TIMELINE = [
  // ── ACT I · Hook ─────────────────────────────
  [Scene1_ColdOpen,     7],   //  0 →  7   cold open
  [Scene2_Problem,      8],   //  7 → 15   problem
  [Scene3_Claim,        7],   // 15 → 22   claim

  // ── ACT II · Product Tour ────────────────────
  [Scene4_ProductTour, 30],   // 22 → 52   product screens

  // ── ACT III · Under the hood ─────────────────
  [Scene5_Architecture, 8],   // 52 → 60   7 layers
  [Scene5b_JEPA,        6],   // 60 → 66   jepa
  [Scene5c_Guardrails,  8],   // 66 → 74   invariants

  // ── ACT IV · RAP deep-dive ───────────────────
  [Scene6a_RAPIntro,    6],   // 74 → 80
  [Scene6b_Loop,        8],   // 80 → 88   self-correction loop
  [Scene6c_Chronovisor, 6],   // 88 → 94
  [Scene6d_Memory,      6],   // 94 → 100

  // ── ACT V · Design system + close ────────────
  [Scene7_DesignSystem, 6],   // 100 → 106
  [Scene8_Closing,      9],   // 106 → 115
];

// Compute start offsets
let _cursor = 0;
const TIMED = TIMELINE.map(([fn, d]) => {
  const s = _cursor;
  _cursor += d;
  return { fn, start: s, dur: d };
});
const TOTAL = _cursor;

function Video() {
  return (
    <Stage
      width={1920}
      height={1080}
      duration={TOTAL}
      background="#14141e"
      loop={true}
      autoplay={true}
      persistKey="macena-video"
    >
      {TIMED.map(({ fn: Fn, start, dur }, i) => (
        <Fn key={i} start={start} dur={dur} />
      ))}

      {/* Always-on top-layer progress bar across whole video */}
      <ProgressBar total={TIMELINE.length} duration={TOTAL} />
    </Stage>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<Video />);
