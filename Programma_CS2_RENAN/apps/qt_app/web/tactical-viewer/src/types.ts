/** Shared types — kept in lockstep with apps/qt_app/core/web_bridge.py. */

export type Team = "CT" | "T" | string;

export interface PlayerState {
  id: number;
  name: string;
  team: Team;
  nx: number; // normalized [0..1] via SpatialEngine.world_to_normalized
  ny: number;
  yaw: number;
  is_alive: boolean;
  hp: number;
  weapon: string;
}

export interface NadeState {
  kind: string;
  nx: number;
  ny: number;
  active: boolean;
}

export interface FramePayload {
  tick: number;
  players: PlayerState[];
  nades: NadeState[];
}

export interface EventMarker {
  tick: number;
  kind: string;
  attacker?: number;
  victim?: number;
}

export interface GhostState {
  id: number;
  name: string;
  team: Team;
  nx: number;
  ny: number;
}

/** Team-color lookup matched to the CS2 radar convention. */
export function teamColor(team: Team): string {
  if (team === "CT") return "#4d80ff";
  if (team === "T") return "#FF8533";
  return "#8B94A5";
}
