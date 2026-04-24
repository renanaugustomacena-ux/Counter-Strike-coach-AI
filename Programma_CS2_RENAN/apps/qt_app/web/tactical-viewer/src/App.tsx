import { CS2_TOKENS } from "@shared/tokens";
import { useMarqueeBridge } from "./bridge";

/**
 * MVP-min web app: renders a centered status panel that proves the
 * bridge is connected and the tokens are propagating. Subsequent
 * iterations replace this with the MapCanvas + PlayerTrails + Heatmap
 * components per the P4.0 plan.
 */
export function App(): JSX.Element {
  const { bridge, currentTick, frame, error } = useMarqueeBridge();

  const bg = CS2_TOKENS.surface_base;
  const raised = CS2_TOKENS.surface_raised;
  const accent = CS2_TOKENS.accent_primary;
  const cyan = CS2_TOKENS.chart_line_primary;
  const textPrimary = CS2_TOKENS.text_primary;
  const textSecondary = CS2_TOKENS.text_secondary;

  const status = error
    ? { label: "Bridge error", color: CS2_TOKENS.error }
    : bridge
      ? { label: "Bridge connected", color: CS2_TOKENS.success }
      : { label: "Awaiting Qt handshake…", color: cyan };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: bg,
        color: textPrimary,
        padding: 32,
        boxSizing: "border-box",
        gap: 24,
      }}
    >
      <header
        style={{
          fontFamily: "'Space Grotesk', 'Inter', sans-serif",
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: -1,
        }}
      >
        Tactical Viewer{" "}
        <span style={{ color: accent }}>/ WebEngine preview</span>
      </header>

      <section
        style={{
          background: raised,
          border: `1px solid ${CS2_TOKENS.border_subtle}`,
          borderRadius: 16,
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: 5,
              background: status.color,
              boxShadow: `0 0 8px ${status.color}`,
            }}
          />
          <span style={{ color: textSecondary }}>{status.label}</span>
        </div>
        <div style={{ color: textSecondary, fontSize: 13 }}>
          Current tick:{" "}
          <span
            style={{
              color: cyan,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {currentTick.toLocaleString()}
          </span>
        </div>
        <div style={{ color: textSecondary, fontSize: 13 }}>
          Frame players:{" "}
          <span
            style={{
              color: accent,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {frame?.players?.length ?? 0}
          </span>
        </div>
        {error && (
          <div
            style={{
              marginTop: 8,
              color: CS2_TOKENS.error,
              fontSize: 13,
              whiteSpace: "pre-wrap",
            }}
          >
            {error}
          </div>
        )}
      </section>

      <section
        style={{
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <button
          type="button"
          onClick={() => bridge?.seek_to_tick(0)}
          disabled={!bridge}
          style={buttonStyle(accent, textPrimary)}
        >
          seek 0
        </button>
        <button
          type="button"
          onClick={() => bridge?.seek_to_tick(currentTick + 1000)}
          disabled={!bridge}
          style={buttonStyle(accent, textPrimary)}
        >
          +1000 ticks
        </button>
        <button
          type="button"
          onClick={() => bridge?.request_ghost(currentTick)}
          disabled={!bridge}
          style={buttonStyle(cyan, textPrimary)}
        >
          request ghost
        </button>
      </section>

      <footer
        style={{
          marginTop: "auto",
          color: textSecondary,
          fontSize: 11,
          fontFamily: "'JetBrains Mono', monospace",
          opacity: 0.6,
        }}
      >
        macena · neo-tactical noir · MVP-min (P4.0)
      </footer>
    </div>
  );
}

function buttonStyle(
  accent: string,
  textPrimary: string,
): React.CSSProperties {
  return {
    background: "transparent",
    color: textPrimary,
    border: `1px solid ${accent}`,
    borderRadius: 8,
    padding: "8px 16px",
    fontSize: 13,
    fontFamily: "'Inter', sans-serif",
    cursor: "pointer",
  };
}
