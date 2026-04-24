/** Translucent pro-position ghosts — renders when the Ghost AI returns a payload. */
import { teamColor, type GhostState } from "../types";

export interface GhostLayerProps {
  ghosts: GhostState[];
  side: number;
}

export function GhostLayer({ ghosts, side }: GhostLayerProps): JSX.Element {
  return (
    <g>
      {ghosts.map((g) => {
        const cx = g.nx * side;
        const cy = g.ny * side;
        const color = teamColor(g.team);
        return (
          <g key={`ghost-${g.id}`}>
            <circle
              cx={cx}
              cy={cy}
              r={9}
              fill={color}
              opacity={0.18}
            />
            <circle
              cx={cx}
              cy={cy}
              r={5}
              fill="none"
              stroke={color}
              strokeWidth={1.2}
              strokeDasharray="2 2"
              opacity={0.7}
            />
          </g>
        );
      })}
    </g>
  );
}
