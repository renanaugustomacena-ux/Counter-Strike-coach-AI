"""
Coaching Dialogue Engine

Multi-turn coaching dialogue with RAG, Experience Bank, and Neural Network
augmentation.  Evolves the single-shot OllamaCoachWriter into an interactive
session where players can ask follow-up questions about their performance.

Integration Points:
    - llm_service.py: LLMService.chat() for multi-turn Ollama conversations
    - rag_knowledge.py: KnowledgeRetriever for tactical knowledge retrieval
    - experience_bank.py: ExperienceBank for COPER experience retrieval
    - coaching_service.py: Existing push-coaching (unchanged, parallel capability)
    - hybrid_engine.py: On-demand ML model predictions for mentioned players
    - PlayerMatchStats / RoundStats: Match & round-level statistical context
"""

import threading
from typing import Dict, List, Optional

from sqlmodel import desc, select

from Programma_CS2_RENAN.backend.services.llm_service import get_llm_service
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import (
    CoachingInsight,
    PlayerMatchStats,
    RoundStats,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.coaching_dialogue")

# Intent classification keywords for retrieval routing
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "positioning": [
        "position",
        "angle",
        "spot",
        "hold",
        "peek",
        "stand",
        "rotate",
        "flank",
        "site",
        "where",
        "place",
    ],
    "utility": [
        "smoke",
        "flash",
        "molotov",
        "HE",
        "grenade",
        "utility",
        "nade",
        "lineup",
        "throw",
    ],
    "economy": [
        "eco",
        "buy",
        "save",
        "money",
        "force",
        "full buy",
        "pistol",
        "budget",
        "invest",
    ],
    "aim": [
        "aim",
        "spray",
        "crosshair",
        "headshot",
        "accuracy",
        "recoil",
        "flick",
        "tracking",
        "sens",
        "sensitivity",
    ],
    "player_query": [
        "tell me about",
        "who is",
        "stats for",
        "profile",
        "nationality",
        "country",
        "what team",
    ],
}

_CS2_MAP_NAMES = frozenset(
    {
        "mirage",
        "dust2",
        "inferno",
        "overpass",
        "nuke",
        "ancient",
        "anubis",
        "vertigo",
        "train",
    }
)

SYSTEM_PROMPT_TEMPLATE = """\
You are an expert CS2 tactical coach.  You have access to real match data, \
round-by-round statistics, and coaching insights generated from parsed demo files.

Player context:
{player_context}

Guidelines:
- Be specific, actionable, and encouraging.
- Reference actual stats and recent coaching insights when relevant.
- If the user asks about positioning, utility, economy, or aim, give concrete examples.
- Match the depth of your response to what the user asks for. If they ask a quick \
question, be brief. If they ask for a detailed analysis, deep explanation, or \
specific examples from matches, give them a thorough, in-depth response with no \
artificial length limit. The user runs this system locally with no token costs — \
never truncate or summarize when they ask for depth.
- When the user asks for a minimum word count or detailed analysis, ALWAYS honor \
that request. Write as much as needed. You have no output length restrictions.
- When match data, round data, or ML insights are provided in the context, use them \
extensively — cite specific rounds, specific stats. \
Build your analysis around real data, not generic advice.
- Do NOT repeat raw numbers — interpret and explain them.
- Only claim AI/ML analysis when ML-BACKED COACHING INSIGHTS are actually present \
in the context below. If no ML insights are provided, do not reference neural \
network analysis — instead focus on the statistical data and coaching knowledge.

CRITICAL RULES FOR FACTUAL ACCURACY:
- When player data is provided in a "VERIFIED PLAYER DATA" block, use ONLY that data.
- When MATCH STATISTICS, BEST WINNING ROUNDS, or ML-BACKED COACHING INSIGHTS \
blocks are present, treat them as real analyzed data from parsed demo files.
- NEVER guess or fabricate a player's team, nationality, real name, or statistics.
- If no verified data is available for a player, say: \
"I don't have verified data for that player in my database."
- Do NOT confuse different players — each player profile is distinct.
- When comparing players, only use data explicitly provided — do not invent statistics.
- If the user asks about a player and no VERIFIED PLAYER DATA block is present, \
say you don't have information on that player rather than guessing.

CRITICAL RULES FOR DATA PROVENANCE:
- If the player context says "pro reference data", these insights come from \
professional players, NOT from the user's personal matches.
- NEVER say "your stats show" or "your utility usage" when referencing pro data. \
Instead say "the pro data shows" or "based on pro match analysis".
- WR-79: Address the user as "you" or "player" — NEVER use their configured \
username (shown in Player context above) in coaching advice. The username is \
metadata for the system, not something to repeat back to the user.
- When retrieved coaching experiences mention specific player names, those are \
pro players from parsed demos — clearly attribute them (e.g., "in s1mple's \
data we see..."), do NOT conflate pro player names with the user.
- Only use possessive framing ("your", "you") when the context explicitly confirms \
the data comes from the user's personal matches.\
"""


class CoachingDialogueEngine:
    """Multi-turn coaching dialogue with RAG-augmented responses."""

    MAX_CONTEXT_TURNS = 6
    RETRIEVAL_TOP_K = 3

    def __init__(self):
        self._llm = get_llm_service()
        self._player_lookup = None  # Lazy init to avoid import cost at startup
        self._player_context: Dict = {}
        self._system_prompt: str = ""
        self._history: List[Dict[str, str]] = []
        self._session_active: bool = False
        # C-06: Protect mutable session state from concurrent UI thread access
        self._state_lock = threading.Lock()

        # Ensure hand-curated tactical knowledge is in the DB for RAG retrieval
        try:
            from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import (
                ensure_seed_knowledge_loaded,
            )

            ensure_seed_knowledge_loaded()
        except Exception as exc:
            logger.debug("Seed knowledge check skipped: %s", exc)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(
        self,
        player_name: str,
        demo_name: Optional[str] = None,
    ) -> str:
        """Load player context and return an opening coaching message."""
        with self._state_lock:
            self._player_context = self._build_player_context(player_name, demo_name)
            self._system_prompt = self._build_system_prompt()
            self._history = []
            self._session_active = True

            opening = self._generate_opening()
            self._history.append({"role": "assistant", "content": opening})
            logger.info("Dialogue session started for player=%s", player_name)
            return opening

    def respond(self, user_message: str) -> str:
        """Process a user question and return a coaching response."""
        with self._state_lock:
            if not self._session_active:
                # No formal session — still attempt a full LLM response if
                # Ollama is available, using a default system prompt.
                if self._llm.is_available():
                    self._session_active = True
                    self._system_prompt = self._system_prompt or self._build_system_prompt()
                else:
                    return self._fallback_response(
                        user_message, self._classify_intent(user_message)
                    )

            intent = self._classify_intent(user_message)
            retrieval_context = self._retrieve_context(user_message, intent)

            # Build the augmented user message with retrieval context
            augmented_user = user_message
            if retrieval_context:
                augmented_user = (
                    f"{user_message}\n\n"
                    f"[Retrieved coaching knowledge for reference — "
                    f"use if relevant, ignore if not]\n{retrieval_context}"
                )

            # Build message array for Ollama (sliding window — history NOT yet mutated)
            messages = self._build_chat_messages(augmented_user)

            # F5-06: append user message only after we have a valid response so that
            # an LLM exception cannot leave the history in an inconsistent state.
            try:
                response = self._llm.chat(messages, system_prompt=self._system_prompt)
            except Exception as exc:
                logger.error("LLM chat raised an exception: %s", exc)
                response = self._fallback_response(user_message, intent)

            # Check for LLM error markers → fall back
            if response.startswith("[LLM"):
                logger.warning("LLM error in dialogue: %s", response)
                response = self._fallback_response(user_message, intent)

            # Safe to append now that we have a usable response
            self._history.append({"role": "user", "content": user_message})
            self._history.append({"role": "assistant", "content": response})
            return response

    def get_history(self) -> List[Dict[str, str]]:
        """Return the full conversation history."""
        with self._state_lock:
            return list(self._history)

    def clear_session(self):
        """Reset the dialogue session."""
        with self._state_lock:
            self._history = []
            self._player_context = {}
            self._session_active = False
            logger.info("Dialogue session cleared")

    @property
    def is_available(self) -> bool:
        """True when Ollama is reachable."""
        return self._llm.is_available()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_player_context(self, player_name: str, demo_name: Optional[str]) -> Dict:
        """Fetch recent coaching insights and stats from DB."""
        context: Dict = {"player_name": player_name, "demo_name": demo_name}

        # Infer map_name from demo filename (e.g. "navi-vs-faze-m1-mirage.dem")
        if demo_name:
            detected_map = self._detect_map_mention(demo_name)
            if detected_map:
                context["map_name"] = detected_map

        try:
            db = get_db_manager()
            with db.get_session() as session:
                stmt = (
                    select(CoachingInsight)
                    .where(CoachingInsight.player_name == player_name)
                    .order_by(desc(CoachingInsight.created_at))
                    .limit(20)
                )
                recent_insights = session.exec(stmt).all()

                # Fall back to pro player insights as coaching reference
                if not recent_insights:
                    pro_stmt = (
                        select(CoachingInsight).order_by(desc(CoachingInsight.created_at)).limit(20)
                    )
                    recent_insights = session.exec(pro_stmt).all()
                    if recent_insights:
                        context["using_pro_reference"] = True

                if recent_insights:
                    context["recent_insights"] = [
                        {
                            "title": i.title,
                            "focus_area": i.focus_area,
                            "severity": i.severity,
                            "message": i.message[:500],
                            "player_name": i.player_name,
                        }
                        for i in recent_insights
                    ]
                    # Identify recurring focus areas
                    areas = [i.focus_area for i in recent_insights]
                    context["primary_focus"] = max(set(areas), key=areas.count)
        except Exception as exc:
            logger.warning("Failed to load player context: %s", exc)

        return context

    def _build_system_prompt(self) -> str:
        """Create system prompt with player context embedded."""
        player_name = self._player_context.get("player_name", "Unknown")
        using_pro = self._player_context.get("using_pro_reference", False)

        if using_pro:
            parts = [f"User: {player_name} (no personal match data yet — using pro reference data)"]
        else:
            parts = [f"Player: {player_name}"]

        if self._player_context.get("demo_name"):
            parts.append(f"Current demo: {self._player_context['demo_name']}")

        if self._player_context.get("primary_focus"):
            parts.append(f"Primary improvement area: {self._player_context['primary_focus']}")

        insights = self._player_context.get("recent_insights", [])
        if insights:
            if self._player_context.get("using_pro_reference"):
                parts.append(
                    f"Pro player analysis (use as coaching reference, "
                    f"{len(insights)} insights available):"
                )
                for ins in insights[:10]:
                    pro = ins.get("player_name", "Pro")
                    parts.append(
                        f"  - [{ins['severity']}] {pro} — {ins['title']}: "
                        f"{ins['message'][:300]}"
                    )
            else:
                parts.append(f"Recent coaching insights ({len(insights)} available):")
                for ins in insights[:10]:
                    parts.append(f"  - [{ins['severity']}] {ins['title']}: {ins['message'][:300]}")

        player_context_str = "\n".join(parts)
        return SYSTEM_PROMPT_TEMPLATE.format(player_context=player_context_str)

    def _get_player_lookup(self):
        """Lazy-init PlayerLookupService to avoid import cost at startup."""
        if self._player_lookup is None:
            from Programma_CS2_RENAN.backend.services.player_lookup import PlayerLookupService

            self._player_lookup = PlayerLookupService()
        return self._player_lookup

    def _classify_intent(self, message: str) -> str:
        """Keyword-based intent classification with player entity detection."""
        message_lower = message.lower()
        scores: Dict[str, int] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            scores[intent] = sum(1 for kw in keywords if kw in message_lower)
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        intent = best if scores[best] > 0 else "general"

        # Player entity detection: if the message mentions a known pro player,
        # override to player_query so we inject verified data instead of guessing.
        if intent in ("general", "player_query"):
            try:
                mentions = self._get_player_lookup().detect_player_mentions(message)
                if mentions:
                    return "player_query"
            except Exception as exc:
                logger.debug("Player detection failed: %s", exc)

        return intent

    @staticmethod
    def _detect_map_mention(text: str) -> Optional[str]:
        """Extract a CS2 map name from free text, if mentioned."""
        text_lower = text.lower()
        for map_name in _CS2_MAP_NAMES:
            if map_name in text_lower:
                return map_name
        # Handle common variants
        if "dust 2" in text_lower or "dust_2" in text_lower:
            return "dust2"
        return None

    def _retrieve_context(self, user_message: str, intent: str) -> str:
        """Retrieve RAG knowledge and experiences relevant to the question."""
        blocks: List[str] = []

        # Player-specific factual context (structured DB lookup, not RAG)
        if intent == "player_query":
            try:
                lookup = self._get_player_lookup()
                mentions = lookup.detect_player_mentions(user_message)
                for name in mentions:
                    profile = lookup.lookup_player(name)
                    if profile:
                        blocks.append(lookup.format_player_context(profile))
            except Exception as exc:
                logger.warning("Player lookup failed: %s", exc)

        # RAG tactical knowledge
        category = intent if intent not in ("general", "player_query") else None
        try:
            from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import KnowledgeRetriever

            retriever = KnowledgeRetriever()
            entries = retriever.retrieve(
                query=user_message,
                top_k=self.RETRIEVAL_TOP_K,
                category=category,
            )
            # Category mismatch fallback: DB categories (pro_baseline, pro_map_reference,
            # opening_duels) don't match intent categories (positioning, utility, etc.).
            # Retry without filter — semantic search handles relevance ranking.
            if not entries and category:
                entries = retriever.retrieve(
                    query=user_message,
                    top_k=self.RETRIEVAL_TOP_K,
                )
            if entries:
                rag_lines = ["Tactical knowledge:"]
                for e in entries:
                    rag_lines.append(f"- {e.title}: {e.description}")
                blocks.append("\n".join(rag_lines))
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)

        # Experience Bank — retrieve pro experiences for grounding
        try:
            from Programma_CS2_RENAN.backend.knowledge.experience_bank import (
                ExperienceContext,
                get_experience_bank,
            )

            bank = get_experience_bank()  # Singleton — avoids re-loading SBERT model (F5-04)
            # Try map from session context first, then detect from user message
            map_name = self._player_context.get("map_name") or self._detect_map_mention(
                user_message
            )
            side = self._player_context.get("side")
            round_phase = self._player_context.get("round_phase")

            if map_name:
                # Contextual retrieval — map known (side defaults to "T" if unknown)
                ctx = ExperienceContext(
                    map_name=map_name,
                    round_phase=round_phase or "unknown",
                    side=side or "T",
                )
                experiences = bank.retrieve_similar(ctx, top_k=self.RETRIEVAL_TOP_K)
            else:
                # Semantic-only retrieval — no map context, search all experiences
                experiences = bank.retrieve_by_text(user_message, top_k=self.RETRIEVAL_TOP_K)

            if experiences:
                exp_lines = ["Similar pro experiences:"]
                for exp in experiences:
                    source = f"(pro: {exp.pro_player_name})" if exp.pro_player_name else ""
                    exp_lines.append(
                        f"- {exp.action_taken} → {exp.outcome} " f"on {exp.map_name} {source}"
                    )
                blocks.append("\n".join(exp_lines))
        except Exception as exc:
            logger.warning("Experience Bank retrieval failed: %s", exc)

        # Analytical context: match stats, round data, and ML-backed insights
        # for any player mentioned in the query.
        try:
            analytical = self._retrieve_analytical_context(user_message, intent)
            if analytical:
                blocks.append(analytical)
        except Exception as exc:
            logger.warning("Analytical context retrieval failed: %s", exc)

        return "\n\n".join(blocks)

    # ------------------------------------------------------------------
    # Analytical context — match stats, round data, ML insights
    # ------------------------------------------------------------------

    def _retrieve_analytical_context(self, user_message: str, intent: str) -> str:
        """Query match/round statistics and ML-backed coaching insights
        for players mentioned in the user message.

        This bridges the gap between the neural network analysis pipeline
        (which stores insights during post-match processing) and the
        interactive dialogue — so the LLM can reference actual NN-backed
        data when answering questions about specific players.
        """
        # Detect player names in the message
        mentioned: List[str] = []
        try:
            lookup = self._get_player_lookup()
            mentioned = lookup.detect_player_mentions(user_message)
        except Exception:
            pass

        if not mentioned:
            return ""

        blocks: List[str] = []

        db = get_db_manager()
        with db.get_session() as session:
            for name in mentioned[:5]:  # Cap to avoid oversized prompts
                player_block = self._format_player_analytics(session, name)
                if player_block:
                    blocks.append(player_block)

        # On-demand ML predictions for mentioned players (if hybrid engine
        # is available and player stats exist in the DB).
        ml_block = self._get_ml_analysis_for_players(mentioned[:3])
        if ml_block:
            blocks.append(ml_block)

        return "\n\n".join(blocks)

    @staticmethod
    def _format_player_analytics(session, player_name: str) -> str:
        """Format match-level and round-level data for a single player."""
        parts: List[str] = []

        # --- Match-level stats ---
        match_stmt = (
            select(PlayerMatchStats)
            .where(PlayerMatchStats.player_name == player_name)
            .order_by(desc(PlayerMatchStats.match_date))
            .limit(10)
        )
        matches = session.exec(match_stmt).all()

        if matches:
            lines = [
                f"MATCH STATISTICS for {player_name} "
                f"({len(matches)} recent matches analyzed by ML pipeline):"
            ]
            for m in matches:
                lines.append(
                    f"  {m.demo_name}: Rating={m.rating:.2f} "
                    f"K/D={m.kd_ratio:.2f} ADR={m.avg_adr:.1f} "
                    f"HS%={m.avg_hs:.0%} KAST={m.avg_kast:.0%} "
                    f"Opening={m.opening_duel_win_pct:.0%} "
                    f"Clutch={m.clutch_win_pct:.0%} "
                    f"Trade={m.trade_kill_ratio:.0%}"
                )
            parts.append("\n".join(lines))

        # --- Best rounds (highest impact for coaching examples) ---
        round_stmt = (
            select(RoundStats)
            .where(RoundStats.player_name == player_name)
            .where(RoundStats.round_won.is_(True))  # type: ignore[union-attr]
            .order_by(desc(RoundStats.kills), desc(RoundStats.damage_dealt))
            .limit(15)
        )
        rounds = session.exec(round_stmt).all()

        if rounds:
            lines = [
                f"BEST WINNING ROUNDS for {player_name} "
                f"({len(rounds)} rounds, sorted by impact):"
            ]
            for r in rounds:
                opener = " OPENER" if r.opening_kill else ""
                trades = f" {r.trade_kills}trade" if r.trade_kills else ""
                hs = f" {r.headshot_kills}HS" if r.headshot_kills else ""
                util = []
                if r.flashes_thrown:
                    util.append(f"{r.flashes_thrown}flash")
                if r.smokes_thrown:
                    util.append(f"{r.smokes_thrown}smoke")
                if r.he_damage or r.molotov_damage:
                    util.append(f"{r.he_damage + r.molotov_damage:.0f}utildmg")
                util_str = f" [{', '.join(util)}]" if util else ""

                lines.append(
                    f"  R{r.round_number} ({r.side}) on {r.demo_name}: "
                    f"{r.kills}K/{r.deaths}D {r.damage_dealt}dmg{hs}{opener}{trades}"
                    f" ${r.equipment_value}{util_str}"
                )
            parts.append("\n".join(lines))

        # --- Coaching insights already generated by NN pipeline ---
        insight_stmt = (
            select(CoachingInsight)
            .where(CoachingInsight.player_name == player_name)
            .order_by(desc(CoachingInsight.created_at))
            .limit(10)
        )
        insights = session.exec(insight_stmt).all()

        if insights:
            lines = [
                f"ML-BACKED COACHING INSIGHTS for {player_name} "
                f"({len(insights)} insights from neural network analysis):"
            ]
            for ins in insights:
                lines.append(
                    f"  [{ins.severity}] {ins.title} ({ins.focus_area}): " f"{ins.message[:300]}"
                )
            parts.append("\n".join(lines))

        if not parts:
            return ""

        return "\n".join(parts)

    @staticmethod
    def _get_ml_analysis_for_players(player_names: List[str]) -> str:
        """Run NN model predictions for mentioned players.

        Aggregates each player's match stats and feeds them through the
        AdvancedCoachNN or JEPA model to get fresh NN-backed predictions.

        IMPORTANT: Only calls the NN model + pro baseline (deviations +
        ML predictions + synthesis).  Does NOT touch the RAG retriever
        to avoid double-loading SBERT, which causes CUDA OOM on GPUs
        with < 4 GiB VRAM.
        """
        try:
            from Programma_CS2_RENAN.backend.coaching.hybrid_engine import HybridCoachingEngine

            db = get_db_manager()
            blocks: List[str] = []

            # Create engine ONCE outside the loop (loads NN model + baseline).
            # The retriever (SBERT) is lazy-loaded — we never touch it here.
            engine = HybridCoachingEngine()

            for name in player_names:
                # Aggregate player stats across all their matches
                with db.get_session() as session:
                    stats_rows = session.exec(
                        select(PlayerMatchStats).where(PlayerMatchStats.player_name == name)
                    ).all()

                if not stats_rows:
                    continue

                # Build average stats dict for the hybrid engine
                stat_fields = [
                    "avg_kills",
                    "avg_deaths",
                    "avg_adr",
                    "avg_hs",
                    "avg_kast",
                    "kd_ratio",
                    "impact_rounds",
                    "accuracy",
                    "econ_rating",
                    "rating",
                    "opening_duel_win_pct",
                    "clutch_win_pct",
                    "trade_kill_ratio",
                    "flash_assists",
                    "positional_aggression_score",
                    "kpr",
                    "dpr",
                    "rating_impact",
                    "rating_survival",
                    "he_damage_per_round",
                    "smokes_per_round",
                    "unused_utility_per_round",
                    "thrusmoke_kill_pct",
                    "kill_std",
                    "adr_std",
                ]
                player_stats = {}
                for field in stat_fields:
                    vals = [getattr(r, field, 0.0) or 0.0 for r in stats_rows]
                    player_stats[field] = sum(vals) / len(vals) if vals else 0.0

                # Run ONLY the NN parts: deviations + ML predictions + synthesis.
                # Bypass _retrieve_contextual_knowledge (which loads SBERT) by
                # passing an empty knowledge list to _synthesize_insights.
                deviations = engine._calculate_deviations(player_stats)
                ml_preds = engine._get_ml_predictions(player_stats)
                insights = engine._synthesize_insights(
                    deviations, ml_preds, [], None, engine.pro_baseline
                )
                # Sort by priority (same as generate_insights)
                insights.sort(
                    key=lambda x: (
                        -engine._priority_value(x.priority),
                        -x.confidence,
                    )
                )

                if insights:
                    lines = [
                        f"LIVE NEURAL NETWORK ANALYSIS for {name} "
                        f"(AdvancedCoachNN/JEPA model predictions):"
                    ]
                    for ins in insights[:5]:
                        lines.append(
                            f"  [{ins.priority.value.upper()}] {ins.title} "
                            f"(confidence={ins.confidence:.0%}): {ins.message[:250]}"
                        )
                    blocks.append("\n".join(lines))

            return "\n\n".join(blocks)

        except Exception as exc:
            logger.warning("On-demand ML analysis failed: %s", exc)
            return ""

    def _build_chat_messages(self, augmented_user: str) -> List[Dict[str, str]]:
        """Build message array for Ollama with sliding context window."""
        # Take the last MAX_CONTEXT_TURNS * 2 messages from history.
        # F5-06: history is NOT yet mutated when this is called — no need to
        # skip the last element (the user message is appended after LLM reply).
        window_size = self.MAX_CONTEXT_TURNS * 2
        prior = self._history[-window_size:]

        messages: List[Dict[str, str]] = list(prior)
        messages.append({"role": "user", "content": augmented_user})
        return messages

    def _generate_opening(self) -> str:
        """Generate a session opening message."""
        if not self._llm.is_available():
            return self._offline_opening()

        prompt_parts = ["Greet the player briefly and offer to help with their gameplay."]
        insights = self._player_context.get("recent_insights", [])
        if insights:
            focus = self._player_context.get("primary_focus", "gameplay")
            prompt_parts.append(
                f"Mention that you've noticed their recent coaching focused on "
                f"'{focus}' and ask if they'd like to dig deeper into that."
            )

        messages = [{"role": "user", "content": " ".join(prompt_parts)}]
        response = self._llm.chat(messages, system_prompt=self._system_prompt)

        if response.startswith("[LLM"):
            return self._offline_opening()
        return response

    def _offline_opening(self) -> str:
        """Opening message when Ollama is unavailable."""
        name = self._player_context.get("player_name", "player")
        focus = self._player_context.get("primary_focus")
        msg = (
            f"[Offline Coach] Hey {name}! I can help with your CS2 gameplay. "
            f"I'm running in offline mode — my answers will be based on the "
            f"tactical knowledge base."
        )
        if focus:
            msg += f" Your recent coaching focused on {focus}."
        msg += " What would you like to work on?"
        return msg

    def _fallback_response(self, user_message: str, intent: str) -> str:
        """Best-effort response when the main chat path fails.

        Tries Ollama one more time with retrieved context.  Falls back to
        raw data dump only when the LLM is truly unreachable.
        """
        retrieval = self._retrieve_context(user_message, intent)

        # Last-chance LLM attempt: feed retrieved data to Ollama even
        # outside a formal session so the user gets natural prose.
        if retrieval and self._llm.is_available():
            try:
                system = self._system_prompt or SYSTEM_PROMPT_TEMPLATE.format(
                    player_context="(No session context — answer based on retrieved data below.)"
                )
                messages = [
                    {
                        "role": "user",
                        "content": (
                            f"{user_message}\n\n"
                            f"[Retrieved coaching knowledge — use this data]\n"
                            f"{retrieval}"
                        ),
                    }
                ]
                response = self._llm.chat(messages, system_prompt=system)
                if not response.startswith("[LLM"):
                    return response
            except Exception as exc:
                logger.debug("Fallback LLM attempt failed: %s", exc)

        # True offline: dump what we have
        if retrieval:
            return (
                f"[Offline Coach] Here's what I found in the knowledge base:\n\n"
                f"{retrieval}\n\n"
                f"Start Ollama for a more interactive coaching experience."
            )
        return (
            "[Offline Coach] I don't have specific knowledge on that topic yet. "
            "Try asking about positioning, utility, economy, or aim. "
            "Start Ollama for full interactive coaching."
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_engine: Optional[CoachingDialogueEngine] = None
_engine_lock = threading.Lock()


def get_dialogue_engine() -> CoachingDialogueEngine:
    """Get or create the global CoachingDialogueEngine singleton (thread-safe)."""
    global _engine
    if _engine is not None:
        return _engine
    with _engine_lock:
        if _engine is None:
            _engine = CoachingDialogueEngine()
    return _engine
