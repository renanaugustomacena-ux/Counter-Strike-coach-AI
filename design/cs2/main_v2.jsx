// main_v2.jsx — v2 timeline with cinematic density
// ──────────────────────────────────────────────────

const TIMELINE_V2 = [
  // ACT I · Hook
  [V2_S1_ColdOpen,     8],   //  0 →  8
  [V2_S2_Problem,      8],   //  8 → 16
  [V2_S3_Thesis,       8],   // 16 → 24

  // ACT II · Product reel
  [V2_S4_ProductReel, 35],   // 24 → 59

  // ACT III · Architecture
  [V2_S5_Pipeline,    12],   // 59 → 71
  [V2_S6_JEPA,         9],   // 71 → 80
  [V2_S7_Invariants,   9],   // 80 → 89

  // ACT IV · RAP loop
  [V2_S8_RAP,         12],   // 89 → 101

  // ACT V · Design + close
  [V2_S9_DesignSystem, 8],   // 101 → 109
  [V2_S10_Closing,    10],   // 109 → 119
];

let _c = 0;
const TIMED_V2 = TIMELINE_V2.map(([fn, d]) => {
  const s = _c; _c += d;
  return { fn, start: s, dur: d };
});
const TOTAL_V2 = _c;

function VideoV2() {
  return (
    <Stage
      width={1920}
      height={1080}
      duration={TOTAL_V2}
      background="#0a0a14"
      loop={true}
      autoplay={true}
      persistKey="macena-video-v2"
    >
      {TIMED_V2.map(({ fn: Fn, start, dur }, i) => (
        <Fn key={i} start={start} dur={dur} />
      ))}
      <ProgressBar total={TIMELINE_V2.length} duration={TOTAL_V2} />
    </Stage>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<VideoV2 />);
