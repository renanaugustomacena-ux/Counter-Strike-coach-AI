import { useState } from "react";
import { CS2_TOKENS } from "@shared/tokens";
import { useCoachChatBridge } from "./bridge";

export function App(): JSX.Element {
  const { bridge, messages, isLoading, isAvailable, sessionActive, error } =
    useCoachChatBridge();
  const [draft, setDraft] = useState("");

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

  const handleSend = () => {
    const text = draft.trim();
    if (!text || !bridge || isLoading) return;
    bridge.send_message(text);
    setDraft("");
  };

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
        gap: 16,
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
        Coach Chat{" "}
        <span style={{ color: accent }}>/ WebEngine preview</span>
      </header>

      <section
        style={{
          background: raised,
          border: `1px solid ${CS2_TOKENS.border_subtle}`,
          borderRadius: 16,
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 8,
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
        </div>
        <div style={{ color: textSecondary, fontSize: 13 }}>
          Available:{" "}
          <span style={{ color: isAvailable ? CS2_TOKENS.success : CS2_TOKENS.error }}>
            {isAvailable ? "yes" : "no"}
          </span>
          {" · Session: "}
          <span style={{ color: sessionActive ? CS2_TOKENS.success : textSecondary }}>
            {sessionActive ? "active" : "inactive"}
          </span>
        </div>
      </section>

      <section
        style={{
          flex: 1,
          background: raised,
          border: `1px solid ${CS2_TOKENS.border_subtle}`,
          borderRadius: 16,
          padding: 16,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {messages.length === 0 && (
          <div style={{ color: textSecondary, fontSize: 13 }}>
            No messages yet. Start a session to chat with the coach.
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              background: msg.role === "user" ? accent : CS2_TOKENS.surface_overlay,
              color: textPrimary,
              borderRadius: 12,
              padding: "8px 14px",
              maxWidth: "75%",
              fontSize: 14,
              whiteSpace: "pre-wrap",
            }}
          >
            {msg.content}
          </div>
        ))}
        {isLoading && (
          <div style={{ color: cyan, fontSize: 13 }}>thinking…</div>
        )}
      </section>

      <section style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={!bridge || !sessionActive}
          placeholder={sessionActive ? "Ask the coach…" : "Start a session first"}
          style={{
            flex: 1,
            background: raised,
            color: textPrimary,
            border: `1px solid ${CS2_TOKENS.border_subtle}`,
            borderRadius: 8,
            padding: "10px 14px",
            fontSize: 14,
            fontFamily: "'Inter', sans-serif",
            outline: "none",
          }}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={!bridge || !sessionActive || isLoading || !draft.trim()}
          style={buttonStyle(accent, textPrimary)}
        >
          send
        </button>
        <button
          type="button"
          onClick={() => bridge?.start_session("player", "")}
          disabled={!bridge || !isAvailable || sessionActive}
          style={buttonStyle(cyan, textPrimary)}
        >
          start
        </button>
        <button
          type="button"
          onClick={() => bridge?.clear_session()}
          disabled={!bridge || !sessionActive}
          style={buttonStyle(CS2_TOKENS.error, textPrimary)}
        >
          clear
        </button>
      </section>

      <footer
        style={{
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
    whiteSpace: "nowrap",
  };
}
