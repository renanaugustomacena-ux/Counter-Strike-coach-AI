/** Player dots + yaw cone + name label + HP ring. */
import { teamColor, type PlayerState } from "../types";

export interface PlayerLayerProps {
  players: PlayerState[];
  side: number;
  selectedPlayerId: number | null;
  onSelectPlayer: (id: number) => void;
}

const R = 6;

export function PlayerLayer({
  players,
  side,
  selectedPlayerId,
  onSelectPlayer,
}: PlayerLayerProps): JSX.Element {
  return (
    <g>
      {players.map((p) => {
        const cx = p.nx * side;
        const cy = p.ny * side;
        const color = p.is_alive ? teamColor(p.team) : "#808080";
        const selected = p.id === selectedPlayerId;
        const coneLen = 22;
        // Yaw 90° = up on radar; we flip to map world-space yaw to screen space.
        const yawRad = ((90 - p.yaw) * Math.PI) / 180;
        const tipX = cx;
        const tipY = cy;
        const leftX = cx + Math.cos(yawRad - 0.35) * coneLen;
        const leftY = cy + Math.sin(yawRad - 0.35) * coneLen;
        const rightX = cx + Math.cos(yawRad + 0.35) * coneLen;
        const rightY = cy + Math.sin(yawRad + 0.35) * coneLen;
        return (
          <g
            key={p.id}
            onClick={() => onSelectPlayer(p.id)}
            style={{ cursor: "pointer" }}
          >
            {p.is_alive && (
              <polygon
                points={`${tipX},${tipY} ${leftX},${leftY} ${rightX},${rightY}`}
                fill={color}
                opacity={0.28}
              />
            )}
            {selected && (
              <circle
                cx={cx}
                cy={cy}
                r={R + 4}
                fill="none"
                stroke="#ffffff"
                strokeOpacity={0.8}
                strokeWidth={1.2}
              />
            )}
            <circle
              cx={cx}
              cy={cy}
              r={R}
              fill={color}
              opacity={p.is_alive ? 1 : 0.5}
            />
            {p.is_alive && (
              <circle
                cx={cx}
                cy={cy}
                r={R + 2}
                fill="none"
                stroke={p.hp > 60 ? "#4caf50" : p.hp >= 30 ? "#ffaa00" : "#ff4444"}
                strokeWidth={1.5}
                strokeOpacity={0.85}
                strokeDasharray={`${(p.hp / 100) * (Math.PI * 2 * (R + 2))} ${
                  Math.PI * 2 * (R + 2)
                }`}
                transform={`rotate(-90 ${cx} ${cy})`}
              />
            )}
            <text
              x={cx}
              y={cy - R - 6}
              fontSize={9}
              textAnchor="middle"
              fill="#F5F7FA"
              style={{ userSelect: "none", pointerEvents: "none" }}
              fontFamily="'Inter', sans-serif"
            >
              {p.name}
            </text>
          </g>
        );
      })}
    </g>
  );
}
