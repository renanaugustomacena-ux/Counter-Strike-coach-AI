/**
 * Player trails — last ~20 ticks per player as a fading SVG polyline.
 * Pure SVG (no D3/Three for trails — low overhead, <50 nodes).
 */
import { teamColor, type FramePayload, type PlayerState } from "../types";

export interface TrailsLayerProps {
  history: FramePayload[];
  side: number;
}

export function TrailsLayer({ history, side }: TrailsLayerProps): JSX.Element {
  if (history.length < 2) return <g />;
  // Build per-player point arrays from history (oldest → newest).
  const byPlayer = new Map<number, PlayerState[]>();
  for (const frame of history) {
    for (const p of frame.players) {
      if (!p.is_alive) continue;
      const bucket = byPlayer.get(p.id) ?? [];
      bucket.push(p);
      byPlayer.set(p.id, bucket);
    }
  }

  return (
    <g opacity={0.75}>
      {Array.from(byPlayer.entries()).map(([id, points]) => {
        if (points.length < 2) return null;
        const color = teamColor(points[0].team);
        const pts = points
          .map((p) => `${(p.nx * side).toFixed(1)},${(p.ny * side).toFixed(1)}`)
          .join(" ");
        return (
          <polyline
            key={id}
            points={pts}
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeOpacity={0.55}
          />
        );
      })}
    </g>
  );
}
