export interface MatchStats {
  demo_name: string;
  map_name: string;
  date: string;
  duration_seconds: number;
  score_ct: number;
  score_t: number;
  total_rounds: number;
}

export interface RoundSummary {
  round_number: number;
  winner: "CT" | "T";
  end_reason: string;
  ct_alive: number;
  t_alive: number;
  duration_seconds: number;
}

export interface Insight {
  category: string;
  severity: "info" | "warning" | "critical";
  message: string;
  round_number?: number;
}

export interface HltvBreakdown {
  player_name: string;
  kills: number;
  deaths: number;
  assists: number;
  adr: number;
  rating: number;
}

export interface MatchDetailPayload {
  stats: MatchStats;
  rounds: RoundSummary[];
  insights: Insight[];
  hltv: HltvBreakdown[];
}
