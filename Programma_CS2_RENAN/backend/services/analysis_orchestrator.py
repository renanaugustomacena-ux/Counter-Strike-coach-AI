"""
Analysis Orchestrator — Phase 6 Integration Layer

Coordinates all Phase 6 game-theory analysis modules and produces
structured coaching insights for storage in the database.

This is the bridge between the analysis engines (backend/analysis/)
and the coaching pipeline (CoachingService).
"""

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from Programma_CS2_RENAN.backend.storage.db_models import CoachingInsight
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.analysis_orchestrator")


@dataclass
class RoundAnalysis:
    """Analysis results for a single round."""

    round_number: int
    insights: List[CoachingInsight] = field(default_factory=list)


@dataclass
class MatchAnalysis:
    """Aggregated analysis results for an entire match."""

    player_name: str
    demo_name: str
    round_analyses: List[RoundAnalysis] = field(default_factory=list)
    match_insights: List[CoachingInsight] = field(default_factory=list)

    @property
    def all_insights(self) -> List[CoachingInsight]:
        result = list(self.match_insights)
        for ra in self.round_analyses:
            result.extend(ra.insights)
        return result


class AnalysisOrchestrator:
    """
    Coordinates Phase 6 analysis modules for a match/round.

    Consumes parsed demo data and produces CoachingInsight objects
    that can be stored directly in the database.
    """

    def __init__(self):
        from Programma_CS2_RENAN.backend.analysis import (
            get_blind_spot_detector,
            get_death_estimator,
            get_deception_analyzer,
            get_economy_optimizer,
            get_engagement_range_analyzer,
            get_entropy_analyzer,
            get_game_tree_search,
            get_momentum_tracker,
            get_role_classifier,
            get_utility_analyzer,
            get_win_predictor,
        )

        self.belief_estimator = get_death_estimator()
        self.deception_analyzer = get_deception_analyzer()
        self.momentum_tracker = get_momentum_tracker()
        self.entropy_analyzer = get_entropy_analyzer()
        self.game_tree = get_game_tree_search()
        self.blind_spot_detector = get_blind_spot_detector()
        self.engagement_analyzer = get_engagement_range_analyzer()
        self.win_predictor = get_win_predictor()
        self.role_classifier = get_role_classifier()
        self.utility_analyzer = get_utility_analyzer()
        self.economy_optimizer = get_economy_optimizer()

        # F5-14: per-module failure counter for observability of persistent silent failures.
        self._module_failure_counts: Dict[str, int] = {}

    # Log suppression threshold: log first N failures, then every Mth.
    _LOG_SUPPRESSION_INITIAL = 3
    _LOG_SUPPRESSION_INTERVAL = 10

    def _record_module_failure(self, module: str, error: Exception) -> None:
        """Record and log module failure with suppression for repeated errors."""
        n = self._module_failure_counts.get(module, 0) + 1
        self._module_failure_counts[module] = n
        if n <= self._LOG_SUPPRESSION_INITIAL or n % self._LOG_SUPPRESSION_INTERVAL == 0:
            logger.error("%s analysis failed (consecutive=%s): %s", module, n, error)
        # Notify user when failures are persistent (>3 consecutive)
        if n == self._LOG_SUPPRESSION_INITIAL:
            try:
                from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

                get_state_manager().add_notification(
                    "analysis",
                    "WARNING",
                    f"{module} analysis failing repeatedly ({n} times).",
                )
            except Exception:
                pass

    def analyze_match(
        self,
        player_name: str,
        demo_name: str,
        round_outcomes: List[Dict],
        tick_data: Optional[pd.DataFrame] = None,
        game_states: Optional[List[Dict]] = None,
        player_stats: Optional[Dict[str, float]] = None,
    ) -> MatchAnalysis:
        """
        Run full Phase 6 analysis suite on match data.

        Args:
            player_name: Player identifier.
            demo_name: Demo file name.
            round_outcomes: List of dicts with 'round_number' and 'round_won' keys.
            tick_data: Optional DataFrame with tick-level data for deception/entropy.
            game_states: Optional list of game state dicts for game tree / blind spots.

        Returns:
            MatchAnalysis with all generated insights.
        """
        analysis = MatchAnalysis(player_name=player_name, demo_name=demo_name)

        # O-01: Reset per-module failure counters at the start of each match
        # so persistent failures from one match don't suppress logging in the next.
        self._module_failure_counts.clear()

        # 1. Momentum analysis (always available from round outcomes)
        momentum_insights = self._analyze_momentum(player_name, demo_name, round_outcomes)
        analysis.match_insights.extend(momentum_insights)

        # 2. Deception analysis (requires tick data)
        if tick_data is not None and not tick_data.empty:
            deception_insights = self._analyze_deception(player_name, demo_name, tick_data)
            analysis.match_insights.extend(deception_insights)

        # 3. Entropy analysis (requires tick data with utility events)
        if tick_data is not None and not tick_data.empty:
            entropy_insights = self._analyze_utility_entropy(player_name, demo_name, tick_data)
            analysis.match_insights.extend(entropy_insights)

        # 4. Game tree + blind spots (requires game states)
        if game_states:
            strategy_insights = self._analyze_strategy(player_name, demo_name, game_states)
            analysis.match_insights.extend(strategy_insights)

        # 5. Engagement range analysis (requires tick data with kill positions)
        if tick_data is not None and not tick_data.empty:
            range_insights = self._analyze_engagement_range(
                player_name,
                demo_name,
                tick_data,
            )
            analysis.match_insights.extend(range_insights)

        # 6. Win probability (requires game_states)
        if game_states:
            wp_insights = self._analyze_win_probability(player_name, demo_name, game_states)
            analysis.match_insights.extend(wp_insights)

        # 7. Role classification (requires player_stats)
        if player_stats:
            role_insights = self._analyze_role(player_name, demo_name, player_stats)
            analysis.match_insights.extend(role_insights)

        # 8. Utility usage analysis (requires player_stats with utility fields)
        if player_stats:
            util_insights = self._analyze_utility(player_name, demo_name, player_stats)
            analysis.match_insights.extend(util_insights)

        # 9. Economy optimization (requires game_states with economy data)
        if game_states:
            econ_insights = self._analyze_economy(player_name, demo_name, game_states)
            analysis.match_insights.extend(econ_insights)

        # 10. Bayesian death probability (requires tick data with HP/armor/visibility)
        if tick_data is not None and not tick_data.empty:
            death_insights = self._analyze_death_probability(
                player_name, demo_name, tick_data
            )
            analysis.match_insights.extend(death_insights)

        logger.info(
            "Analysis complete for %s on %s: %d insights generated",
            player_name,
            demo_name,
            len(analysis.all_insights),
        )
        return analysis

    def _analyze_momentum(
        self,
        player_name: str,
        demo_name: str,
        round_outcomes: List[Dict],
    ) -> List[CoachingInsight]:
        """Track momentum through round outcomes, flag tilt/hot states."""
        insights: List[CoachingInsight] = []

        if not round_outcomes:
            return insights

        try:
            from Programma_CS2_RENAN.backend.analysis.momentum import (
                get_momentum_tracker,
                predict_performance_adjustment,
            )

            tracker = get_momentum_tracker()
            tilt_rounds = []
            hot_rounds = []

            for rd in round_outcomes:
                rnum = rd.get("round_number", 0)
                won = rd.get("round_won", False)
                state = tracker.update(round_won=won, round_number=rnum)

                if state.is_tilted:
                    tilt_rounds.append(rnum)
                elif state.is_hot:
                    hot_rounds.append(rnum)

            if tilt_rounds:
                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Momentum: Tilt Risk Detected",
                        severity="High",
                        message=(
                            f"Your momentum dropped into the tilt zone (below 0.85) "
                            f"during rounds {', '.join(str(r) for r in tilt_rounds[:5])}. "
                            f"Consider calling a timeout or changing your approach after "
                            f"consecutive losses to reset your mental state."
                        ),
                        focus_area="momentum",
                    )
                )

            if hot_rounds:
                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Momentum: Hot Streak",
                        severity="Info",
                        message=(
                            f"You entered a hot streak (multiplier > 1.2) during "
                            f"rounds {', '.join(str(r) for r in hot_rounds[:5])}. "
                            f"Great momentum management — capitalize on these phases "
                            f"with confident plays."
                        ),
                        focus_area="momentum",
                    )
                )

        except Exception as e:
            self._record_module_failure("momentum", e)

        return insights

    def _analyze_deception(
        self,
        player_name: str,
        demo_name: str,
        tick_data: pd.DataFrame,
    ) -> List[CoachingInsight]:
        """Analyze deception sophistication from tick data."""
        insights: List[CoachingInsight] = []

        try:
            metrics = self.deception_analyzer.analyze_round(tick_data)

            if metrics.composite_index > 0.6:
                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Deception: Advanced Tactics",
                        severity="Info",
                        message=(
                            f"Your deception index is {metrics.composite_index:.2f} — "
                            f"strong use of fakes and misdirection. "
                            f"Flash bait rate: {metrics.fake_flash_rate:.0%}, "
                            f"Rotation feints: {metrics.rotation_feint_rate:.0%}."
                        ),
                        focus_area="deception",
                    )
                )
            elif metrics.composite_index < 0.2 and metrics.composite_index > 0:
                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Deception: Predictable Play",
                        severity="Medium",
                        message=(
                            f"Your deception index is {metrics.composite_index:.2f} — "
                            f"your play may be predictable. Consider adding fake executes, "
                            f"utility baits, or rotation feints to keep opponents guessing."
                        ),
                        focus_area="deception",
                    )
                )

        except Exception as e:
            self._record_module_failure("deception", e)

        return insights

    def _analyze_utility_entropy(
        self,
        player_name: str,
        demo_name: str,
        tick_data: pd.DataFrame,
    ) -> List[CoachingInsight]:
        """Analyze utility usage effectiveness via entropy reduction."""
        insights: List[CoachingInsight] = []

        try:
            if "event_type" not in tick_data.columns:
                return insights

            utility_events = tick_data[
                tick_data["event_type"].isin(
                    [
                        "smokegrenade_throw",
                        "flashbang_throw",
                        "molotov_throw",
                        "hegrenade_throw",
                    ]
                )
            ]

            if utility_events.empty:
                return insights

            if "team" not in tick_data.columns:
                return insights

            # Compute enemy position entropy before/after each utility
            utility_type_map = {
                "smokegrenade_throw": "smoke",
                "flashbang_throw": "flash",
                "molotov_throw": "molotov",
                "hegrenade_throw": "he_grenade",
            }

            impacts = []
            for _, event in utility_events.iterrows():
                tick = event["tick"]
                utype = utility_type_map.get(event["event_type"], "smoke")

                # Pre: enemy positions at this tick
                event_team = event.get("team", "")
                pre_mask = (tick_data["tick"] == tick) & (tick_data["team"] != event_team)
                post_mask = (tick_data["tick"] == tick + 128) & (tick_data["team"] != event_team)

                if "pos_x" in tick_data.columns and "pos_y" in tick_data.columns:
                    pre_pos = list(
                        zip(
                            tick_data.loc[pre_mask, "pos_x"],
                            tick_data.loc[pre_mask, "pos_y"],
                        )
                    )
                    post_pos = list(
                        zip(
                            tick_data.loc[post_mask, "pos_x"],
                            tick_data.loc[post_mask, "pos_y"],
                        )
                    )

                    if pre_pos:
                        impact = self.entropy_analyzer.analyze_utility_throw(
                            pre_pos,
                            post_pos if post_pos else pre_pos,
                            utype,
                        )
                        impacts.append(impact)

            if impacts:
                ranked = self.entropy_analyzer.rank_utility_usage(impacts)
                best = ranked[0]
                avg_eff = sum(i.effectiveness_rating for i in impacts) / len(impacts)

                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Utility: Entropy Impact Analysis",
                        severity="Info",
                        message=(
                            f"Analyzed {len(impacts)} utility throws. "
                            f"Average effectiveness: {avg_eff:.0%}. "
                            f"Best throw ({best.utility_type}): reduced uncertainty "
                            f"by {best.entropy_delta:.2f} bits ({best.effectiveness_rating:.0%} effective)."
                        ),
                        focus_area="utility_entropy",
                    )
                )

        except Exception as e:
            self._record_module_failure("utility_entropy", e)

        return insights

    def _analyze_strategy(
        self,
        player_name: str,
        demo_name: str,
        game_states: List[Dict],
    ) -> List[CoachingInsight]:
        """Run game tree + blind spot analysis on decision points."""
        insights: List[CoachingInsight] = []

        try:
            # Run blind spot detection
            spots = self.blind_spot_detector.detect(game_states)

            if spots:
                # Generate training plan from top blind spots
                plan = self.blind_spot_detector.generate_training_plan(spots, top_n=3)
                top_spot = spots[0]

                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title=f"Blind Spot: {top_spot.situation_type.title()}",
                        severity="High" if top_spot.impact_rating > 0.15 else "Medium",
                        message=(
                            f"Detected {len(spots)} strategic blind spot(s). "
                            f"Most impactful: In '{top_spot.situation_type}' situations, "
                            f"you tend to '{top_spot.actual_action}' when the optimal play "
                            f"is '{top_spot.optimal_action}' "
                            f"(seen {top_spot.frequency}x, impact: {top_spot.impact_rating:.0%}).\n\n"
                            f"{plan}"
                        ),
                        focus_area="blind_spots",
                    )
                )

            # Also generate a strategy recommendation from the latest state
            if game_states:
                latest = game_states[-1].get("game_state", game_states[-1])
                strategy = self.game_tree.suggest_strategy(latest)
                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Strategy: Game Tree Recommendation",
                        severity="Info",
                        message=strategy,
                        focus_area="game_theory",
                    )
                )

        except Exception as e:
            self._record_module_failure("strategy", e)

        return insights

    def _analyze_engagement_range(
        self,
        player_name: str,
        demo_name: str,
        tick_data: pd.DataFrame,
    ) -> List[CoachingInsight]:
        """Analyze kill distances and provide spatial coaching insights."""
        insights: List[CoachingInsight] = []

        try:
            # Need kill events with position data
            required_cols = {"event_type", "pos_x", "pos_y"}
            if not required_cols.issubset(tick_data.columns):
                return insights

            kill_rows = tick_data[tick_data["event_type"] == "player_death"]
            if kill_rows.empty or len(kill_rows) < 3:
                return insights

            # Build kill event dicts from available columns
            kill_events = []
            for _, row in kill_rows.iterrows():
                ev = {
                    "killer_x": row.get("attacker_pos_x", row.get("pos_x", 0)),
                    "killer_y": row.get("attacker_pos_y", row.get("pos_y", 0)),
                    "killer_z": row.get("attacker_pos_z", row.get("pos_z", 0)),
                    "victim_x": row.get("pos_x", 0),
                    "victim_y": row.get("pos_y", 0),
                    "victim_z": row.get("pos_z", 0),
                }
                kill_events.append(ev)

            if not kill_events:
                return insights

            # Determine map name from tick_data if available
            map_name = "unknown"
            if "map_name" in tick_data.columns:
                map_vals = tick_data["map_name"].dropna().unique()
                if len(map_vals) > 0:
                    map_name = str(map_vals[0])

            # Get player role if available
            player_role = "flex"
            if "role" in tick_data.columns:
                role_vals = tick_data["role"].dropna().unique()
                if len(role_vals) > 0:
                    player_role = str(role_vals[0])

            result = self.engagement_analyzer.analyze_match_engagements(
                kill_events,
                map_name,
                player_role,
            )

            profile = result["profile"]
            observations = result["observations"]

            # Build summary message
            parts = [
                f"Engagement range analysis across {profile.total_kills} kills:",
                f"  Close (<500u): {profile.close_pct:.0%}",
                f"  Medium (500-1500u): {profile.medium_pct:.0%}",
                f"  Long (1500-3000u): {profile.long_pct:.0%}",
                f"  Extreme (>3000u): {profile.extreme_pct:.0%}",
                f"  Average distance: {profile.avg_distance:.0f} units",
            ]

            if observations:
                parts.append("")
                for obs in observations:
                    parts.append(f"  - {obs}")

            # Annotate top kill positions
            annotated = result.get("annotated_kills", [])
            if annotated and map_name != "unknown":
                position_counts: Dict[str, int] = {}
                for ak in annotated:
                    pos = ak.get("killer_position", "Unknown Position")
                    if pos != "Unknown Position":
                        position_counts[pos] = position_counts.get(pos, 0) + 1
                if position_counts:
                    top_positions = sorted(
                        position_counts.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3]
                    parts.append("")
                    parts.append("Most frequent kill positions:")
                    for pos_name, count in top_positions:
                        parts.append(f"  - {pos_name}: {count} kills")

            severity = "Medium" if observations else "Info"
            insights.append(
                CoachingInsight(
                    player_name=player_name,
                    demo_name=demo_name,
                    title="Engagement Range Profile",
                    severity=severity,
                    message="\n".join(parts),
                    focus_area="positioning",
                )
            )

        except Exception as e:
            self._record_module_failure("engagement_range", e)

        return insights

    def _analyze_win_probability(
        self,
        player_name: str,
        demo_name: str,
        game_states: List[Dict],
    ) -> List[CoachingInsight]:
        """Analyze win probability across key moments in the match."""
        insights: List[CoachingInsight] = []

        try:
            if not game_states:
                return insights

            from Programma_CS2_RENAN.backend.analysis.win_probability import GameState

            critical_moments = []
            prev_prob = 0.5

            for state_dict in game_states:
                gs = state_dict.get("game_state", state_dict)
                prob, explanation = self.win_predictor.predict_from_dict(gs)
                swing = abs(prob - prev_prob)

                if swing > 0.2:
                    round_num = gs.get("round_number", 0)
                    critical_moments.append(
                        {
                            "round": round_num,
                            "prob": prob,
                            "swing": swing,
                            "explanation": explanation,
                        }
                    )
                prev_prob = prob

            if not critical_moments:
                return insights

            critical_moments.sort(key=lambda m: m["swing"], reverse=True)
            top_moments = critical_moments[:3]

            parts = ["Significant win probability swings detected:"]
            for m in top_moments:
                direction = "jumped" if m["prob"] > 0.5 else "dropped"
                parts.append(
                    f"  Round {m['round']}: Win chance {direction} by "
                    f"{m['swing']:.0%} ({m['explanation']})"
                )

            heuristic_note = ""
            if not self.win_predictor._checkpoint_loaded:
                heuristic_note = (
                    "\n\n(Note: Predictions are heuristic-based. "
                    "Accuracy will improve once the win probability model is trained.)"
                )

            insights.append(
                CoachingInsight(
                    player_name=player_name,
                    demo_name=demo_name,
                    title="Win Probability: Critical Moments",
                    severity="Medium" if any(m["swing"] > 0.3 for m in top_moments) else "Info",
                    message="\n".join(parts) + heuristic_note,
                    focus_area="win_probability",
                )
            )

        except Exception as e:
            self._record_module_failure("win_probability", e)

        return insights

    def _analyze_role(
        self,
        player_name: str,
        demo_name: str,
        player_stats: Dict[str, float],
    ) -> List[CoachingInsight]:
        """Classify player role and provide role-specific coaching."""
        insights: List[CoachingInsight] = []

        try:
            role, confidence, profile = self.role_classifier.classify(player_stats)

            # Cold start guard: confidence 0.0 means no learned thresholds
            if confidence == 0.0:
                logger.debug(
                    "Role classification in cold start for %s — skipping insight",
                    player_name,
                )
                return insights

            if confidence < 0.3:
                return insights

            map_name = player_stats.get("map_name")
            tips = self.role_classifier.get_role_coaching(role, map_name)

            parts = [
                f"Your playstyle most closely matches the {role.value.upper()} role "
                f"({confidence:.0%} confidence).",
                f"Role description: {profile.description}.",
            ]

            if tips:
                parts.append("\nRole-specific coaching:")
                for tip in tips[:3]:
                    parts.append(f"  - {tip}")

            insights.append(
                CoachingInsight(
                    player_name=player_name,
                    demo_name=demo_name,
                    title=f"Role: {role.value.title()} Detected",
                    severity="Info",
                    message="\n".join(parts),
                    focus_area="role",
                )
            )

        except Exception as e:
            self._record_module_failure("role_classifier", e)

        return insights

    def _analyze_utility(
        self,
        player_name: str,
        demo_name: str,
        player_stats: Dict[str, float],
    ) -> List[CoachingInsight]:
        """Analyze utility usage effectiveness."""
        insights: List[CoachingInsight] = []

        try:
            utility_keys = [
                "smoke_thrown",
                "flash_thrown",
                "molotov_thrown",
                "he_grenade_thrown",
            ]
            has_utility_data = any(player_stats.get(k, 0) > 0 for k in utility_keys)

            if not has_utility_data:
                return insights

            report = self.utility_analyzer.analyze(player_stats)

            parts = [f"Overall utility effectiveness: {report.overall_score:.0%}"]

            for util_type, stats in report.utility_stats.items():
                if stats.total_thrown > 0:
                    parts.append(
                        f"  {util_type.value.title()}: {stats.total_thrown} thrown, "
                        f"effectiveness {stats.effectiveness_score:.0%}"
                    )

            if report.recommendations:
                parts.append("\nRecommendations:")
                for rec in report.recommendations:
                    parts.append(f"  - {rec}")

            parts.append(f"\nEstimated economy value of your utility: ${report.economy_impact:.0f}")

            severity = (
                "High"
                if report.overall_score < 0.3
                else ("Medium" if report.overall_score < 0.6 else "Info")
            )

            insights.append(
                CoachingInsight(
                    player_name=player_name,
                    demo_name=demo_name,
                    title="Utility: Usage Effectiveness",
                    severity=severity,
                    message="\n".join(parts),
                    focus_area="utility",
                )
            )

        except Exception as e:
            self._record_module_failure("utility_analysis", e)

        return insights

    def _analyze_economy(
        self,
        player_name: str,
        demo_name: str,
        game_states: List[Dict],
    ) -> List[CoachingInsight]:
        """Analyze economy decisions and provide buy recommendations."""
        insights: List[CoachingInsight] = []

        try:
            if not game_states:
                return insights

            suboptimal_buys = []

            for state_dict in game_states:
                gs = state_dict.get("game_state", state_dict)

                money = gs.get("team_economy") or gs.get("current_money")
                if money is None:
                    continue

                round_num = gs.get("round_number", 0)
                is_ct = gs.get("is_ct", True)
                score_diff = gs.get("score_diff", 0)
                loss_bonus = gs.get("loss_bonus", 1900)
                actual_buy = gs.get("buy_type", "")

                decision = self.economy_optimizer.recommend(
                    current_money=money,
                    round_number=round_num,
                    is_ct=is_ct,
                    score_diff=score_diff,
                    loss_bonus=loss_bonus,
                )

                if actual_buy and actual_buy != decision.action and decision.confidence > 0.7:
                    suboptimal_buys.append(
                        {
                            "round": round_num,
                            "actual": actual_buy,
                            "recommended": decision.action,
                            "reasoning": decision.reasoning,
                            "confidence": decision.confidence,
                        }
                    )

            if not suboptimal_buys:
                return insights

            parts = [f"Detected {len(suboptimal_buys)} potentially suboptimal buy decision(s):"]
            for buy in suboptimal_buys[:3]:
                parts.append(
                    f"  Round {buy['round']}: You chose '{buy['actual']}' "
                    f"but '{buy['recommended']}' was recommended "
                    f"({buy['reasoning']}, {buy['confidence']:.0%} confidence)"
                )

            insights.append(
                CoachingInsight(
                    player_name=player_name,
                    demo_name=demo_name,
                    title="Economy: Buy Decision Review",
                    severity="Medium" if len(suboptimal_buys) > 2 else "Info",
                    message="\n".join(parts),
                    focus_area="economy",
                )
            )

        except Exception as e:
            self._record_module_failure("economy", e)

        return insights

    def _analyze_death_probability(
        self,
        player_name: str,
        demo_name: str,
        tick_data: pd.DataFrame,
    ) -> List[CoachingInsight]:
        """SVC-04: Bayesian death probability analysis from tick-level state."""
        insights: List[CoachingInsight] = []

        try:
            from Programma_CS2_RENAN.backend.analysis.belief_model import BeliefState

            required = {"health", "armor", "enemies_visible"}
            if not required.issubset(tick_data.columns):
                return insights

            # Sample high-risk moments: low HP with enemies visible
            risk_ticks = tick_data[
                (tick_data["health"] > 0)
                & (tick_data["health"] <= 50)
                & (tick_data["enemies_visible"] >= 1)
            ]

            if risk_ticks.empty:
                return insights

            # Compute average death probability across high-risk ticks
            total_prob = 0.0
            count = 0
            for _, row in risk_ticks.head(200).iterrows():
                belief = BeliefState(
                    visible_enemies=int(row.get("enemies_visible", 0)),
                    positional_exposure=0.5,
                )
                has_armor = bool(row.get("armor", 0) > 0)
                weapon_class = str(row.get("weapon_class", "rifle"))
                prob = self.belief_estimator.estimate(
                    belief, int(row["health"]), has_armor, weapon_class
                )
                total_prob += prob
                count += 1

            if count == 0:
                return insights

            avg_death_prob = total_prob / count
            risk_count = len(risk_ticks)

            if avg_death_prob > 0.6:
                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Survival: High Death Probability in Key Moments",
                        severity="High",
                        message=(
                            f"Across {risk_count} high-risk ticks (HP ≤ 50 with enemies visible), "
                            f"your average survival probability was {1 - avg_death_prob:.0%}. "
                            f"Consider repositioning to cover before engaging at low HP — "
                            f"trading at low HP is rarely worth it unless the round depends on it."
                        ),
                        focus_area="survival",
                    )
                )
            elif avg_death_prob < 0.35 and risk_count > 20:
                insights.append(
                    CoachingInsight(
                        player_name=player_name,
                        demo_name=demo_name,
                        title="Survival: Good Risk Management",
                        severity="Info",
                        message=(
                            f"Even in {risk_count} high-risk situations, your estimated "
                            f"survival probability remained at {1 - avg_death_prob:.0%}. "
                            f"Your positioning under pressure is strong."
                        ),
                        focus_area="survival",
                    )
                )

        except Exception as e:
            self._record_module_failure("death_probability", e)

        return insights


_orchestrator: AnalysisOrchestrator = None  # type: ignore[assignment]
_orchestrator_lock = threading.Lock()  # AC-21-01: thread-safe singleton


def get_analysis_orchestrator() -> AnalysisOrchestrator:
    """Singleton factory — avoids re-instantiating 11 analysis modules per call (F5-37)."""
    global _orchestrator
    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                _orchestrator = AnalysisOrchestrator()
    return _orchestrator
