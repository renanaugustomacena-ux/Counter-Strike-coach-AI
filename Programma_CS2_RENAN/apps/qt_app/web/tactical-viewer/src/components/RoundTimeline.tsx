/**
 * Horizontal round timeline — round boundaries + event markers.
 * Click anywhere along the strip to scrub via bridge.seek_to_tick.
 */
import { CS2_TOKENS } from "@shared/tokens";
import { useMemo, useRef } from "react";
import type { EventMarker } from "../types";

export interface RoundTimelineProps {
  segments: Record<string, number>;
  events: EventMarker[];
  currentTick: number;
  totalTicks: number;
  onScrub: (tick: number) => void;
}

const EVENT_COLOR: Record<string, string> = {
  KILL: CS2_TOKENS.error,
  BOMB_PLANTED: CS2_TOKENS.warning,
  BOMB_DEFUSED: CS2_TOKENS.success,
  ROUND_END: CS2_TOKENS.text_tertiary,
};

export function RoundTimeline({
  segments,
  events,
  currentTick,
  totalTicks,
  onScrub,
}: RoundTimelineProps): JSX.Element {
  const stripRef = useRef<HTMLDivElement>(null);

  const maxTick = useMemo(() => {
    let m = totalTicks;
    for (const t of Object.values(segments)) m = Math.max(m, t);
    for (const e of events) m = Math.max(m, e.tick);
    return Math.max(m, currentTick, 1);
  }, [segments, events, currentTick, totalTicks]);

  const progress = Math.min(1, currentTick / maxTick);
  const handleClick = (ev: React.MouseEvent<HTMLDivElement>) => {
    if (!stripRef.current) return;
    const rect = stripRef.current.getBoundingClientRect();
    const f = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
    onScrub(Math.round(f * maxTick));
  };

  const roundMarks = Object.entries(segments).sort((a, b) => a[1] - b[1]);

  return (
    <div
      ref={stripRef}
      onClick={handleClick}
      style={{
        position: "relative",
        height: 52,
        margin: "0 16px",
        background: CS2_TOKENS.surface_raised,
        border: `1px solid ${CS2_TOKENS.border_subtle}`,
        borderRadius: 8,
        cursor: "pointer",
        overflow: "hidden",
      }}
      title="Click to scrub"
    >
      {/* Round boundaries */}
      {roundMarks.map(([name, tick]) => {
        const left = `${(tick / maxTick) * 100}%`;
        return (
          <div
            key={name}
            style={{
              position: "absolute",
              left,
              top: 0,
              bottom: 0,
              width: 1,
              background: CS2_TOKENS.border_default,
              opacity: 0.6,
            }}
            title={name}
          />
        );
      })}
      {/* Event markers */}
      {events.map((e, idx) => {
        const left = `${(e.tick / maxTick) * 100}%`;
        const color = EVENT_COLOR[e.kind] ?? CS2_TOKENS.text_secondary;
        return (
          <div
            key={`${e.kind}-${e.tick}-${idx}`}
            style={{
              position: "absolute",
              left,
              top: "50%",
              transform: "translate(-50%, -50%)",
              width: 6,
              height: 6,
              background: color,
              borderRadius: "50%",
              boxShadow: `0 0 6px ${color}`,
            }}
            title={`${e.kind} @ ${e.tick}`}
          />
        );
      })}
      {/* Playhead */}
      <div
        style={{
          position: "absolute",
          left: `${progress * 100}%`,
          top: 0,
          bottom: 0,
          width: 2,
          background: CS2_TOKENS.accent_primary,
          boxShadow: `0 0 8px ${CS2_TOKENS.accent_primary}`,
          transform: "translateX(-1px)",
        }}
      />
      {/* Bottom tick readout */}
      <div
        style={{
          position: "absolute",
          left: 8,
          bottom: 4,
          color: CS2_TOKENS.text_secondary,
          fontSize: 10,
          fontFamily: "'JetBrains Mono', monospace",
          pointerEvents: "none",
        }}
      >
        tick {currentTick.toLocaleString()} / {maxTick.toLocaleString()}
      </div>
      <div
        style={{
          position: "absolute",
          right: 8,
          bottom: 4,
          color: CS2_TOKENS.text_secondary,
          fontSize: 10,
          fontFamily: "'JetBrains Mono', monospace",
          pointerEvents: "none",
        }}
      >
        {roundMarks.length} rounds · {events.length} events
      </div>
    </div>
  );
}
