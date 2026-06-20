import { CS2_TOKENS } from "@shared/tokens";
import { useMatchDetailBridge } from "./bridge";

export function App(): JSX.Element {
  const { bridge, data, isLoading, error } = useMatchDetailBridge();

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
        Match Detail{" "}
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
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
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
          {isLoading && (
            <span style={{ color: cyan, fontSize: 12, marginLeft: 8 }}>
              loading…
            </span>
          )}
        </div>

        {data && (
          <>
            <div style={{ color: textSecondary, fontSize: 13 }}>
              Map:{" "}
              <span style={{ color: accent, fontFamily: "'JetBrains Mono', monospace" }}>
                {data.stats.map_name}
              </span>
            </div>
            <div style={{ color: textSecondary, fontSize: 13 }}>
              Score:{" "}
              <span style={{ color: "#4d80ff", fontFamily: "'JetBrains Mono', monospace" }}>
                {data.stats.score_ct}
              </span>
              {" – "}
              <span style={{ color: "#FF8533", fontFamily: "'JetBrains Mono', monospace" }}>
                {data.stats.score_t}
              </span>
            </div>
            <div style={{ color: textSecondary, fontSize: 13 }}>
              Rounds:{" "}
              <span style={{ color: cyan, fontFamily: "'JetBrains Mono', monospace" }}>
                {data.rounds.length}
              </span>
              {" · Insights: "}
              <span style={{ color: cyan, fontFamily: "'JetBrains Mono', monospace" }}>
                {data.insights.length}
              </span>
              {" · Players: "}
              <span style={{ color: cyan, fontFamily: "'JetBrains Mono', monospace" }}>
                {data.hltv.length}
              </span>
            </div>
          </>
        )}

        {!data && !isLoading && !error && (
          <div style={{ color: textSecondary, fontSize: 13 }}>
            No match loaded. Call load_detail(demo_name) from host.
          </div>
        )}

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

      <section style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => bridge?.load_detail("latest")}
          disabled={!bridge || isLoading}
          style={buttonStyle(accent, textPrimary)}
        >
          load latest
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
        macena · neo-tactical noir · MVP-min (P4.1)
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
