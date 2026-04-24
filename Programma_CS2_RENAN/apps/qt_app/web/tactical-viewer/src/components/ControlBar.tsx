/** Top control bar — status dot + toggle buttons. */
import { CS2_TOKENS } from "@shared/tokens";

export interface ControlBarProps {
  connected: boolean;
  error: string | null;
  mapName: string;
  currentTick: number;
  playerCount: number;
  showHeatmap: boolean;
  showGhosts: boolean;
  onToggleHeatmap: () => void;
  onToggleGhosts: () => void;
  onRequestGhost: () => void;
  onSeekHome: () => void;
}

export function ControlBar(props: ControlBarProps): JSX.Element {
  const statusColor = props.error
    ? CS2_TOKENS.error
    : props.connected
      ? CS2_TOKENS.success
      : CS2_TOKENS.chart_line_primary;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "12px 16px",
        borderBottom: `1px solid ${CS2_TOKENS.border_subtle}`,
        background: CS2_TOKENS.surface_raised,
        flexShrink: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: 5,
            background: statusColor,
            boxShadow: `0 0 8px ${statusColor}`,
          }}
        />
        <span
          style={{
            color: CS2_TOKENS.text_primary,
            fontFamily: "'Space Grotesk', 'Inter', sans-serif",
            fontSize: 16,
            fontWeight: 700,
            letterSpacing: -0.3,
          }}
        >
          Tactical Viewer
        </span>
        {props.mapName && (
          <span
            style={{
              color: CS2_TOKENS.accent_primary,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: 1,
              textTransform: "uppercase",
              padding: "2px 8px",
              background: CS2_TOKENS.accent_muted_15,
              borderRadius: 4,
            }}
          >
            {props.mapName}
          </span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          color: CS2_TOKENS.text_secondary,
          fontSize: 12,
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        <span>
          tick{" "}
          <span style={{ color: CS2_TOKENS.chart_line_primary }}>
            {props.currentTick.toLocaleString()}
          </span>
        </span>
        <span>
          players{" "}
          <span style={{ color: CS2_TOKENS.accent_primary }}>
            {props.playerCount}
          </span>
        </span>
      </div>

      <div style={{ flex: 1 }} />

      <TgButton
        active={props.showGhosts}
        onClick={props.onToggleGhosts}
        label="ghosts"
        title="Show Ghost AI overlay"
      />
      <TgButton
        active={false}
        onClick={props.onRequestGhost}
        label="refresh"
        title="Re-request Ghost AI for this tick"
      />
      <TgButton
        active={props.showHeatmap}
        onClick={props.onToggleHeatmap}
        label="heatmap"
        title="Accumulated-position density"
      />
      <TgButton
        active={false}
        onClick={props.onSeekHome}
        label="seek 0"
        title="Seek to start"
      />

      {props.error && (
        <span
          style={{
            color: CS2_TOKENS.error,
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            maxWidth: 300,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={props.error}
        >
          {props.error}
        </span>
      )}
    </div>
  );
}

interface TgButtonProps {
  active: boolean;
  onClick: () => void;
  label: string;
  title: string;
}

function TgButton({ active, onClick, label, title }: TgButtonProps): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        background: active ? CS2_TOKENS.accent_primary : "transparent",
        color: active ? CS2_TOKENS.text_inverse : CS2_TOKENS.text_primary,
        border: `1px solid ${active ? CS2_TOKENS.accent_primary : CS2_TOKENS.border_default}`,
        borderRadius: 6,
        padding: "6px 12px",
        fontSize: 12,
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: 0.5,
        textTransform: "uppercase",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}
