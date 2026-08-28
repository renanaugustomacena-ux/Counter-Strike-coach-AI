"""
Coaching Dialogue Engine

Multi-turn coaching dialogue with RAG, Experience Bank, and baseline-deviation
augmentation.  Evolves the single-shot OllamaCoachWriter into an interactive
session where players can ask follow-up questions about their performance.

D-02 (F-0028 caller drift): this module used to claim "Neural Network
augmentation" — no neural model ever runs here. Since F-0028, neural output
enters coaching only via JEPAInsightAdapter (26-HYB-01); this engine augments
chat with pro-baseline Z-score analysis and retrieval.

Integration Points:
    - llm_service.py: LLMService.chat() for multi-turn Ollama conversations
    - rag_knowledge.py: KnowledgeRetriever for tactical knowledge retrieval
    - experience_bank.py: ExperienceBank for COPER experience retrieval
    - coaching_service.py: Existing push-coaching (unchanged, parallel capability)
    - hybrid_engine.py: On-demand baseline Z-deviation analysis for mentioned players
    - PlayerMatchStats / RoundStats: Match & round-level statistical context
"""

import json
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
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

# WR-06 / CHAT-01 (AUDIT §8.1): Timeout budget for interactive LLM calls.
# Realistic Gemma 4 E2B latency on this class of hardware (5.1B Q4_K_M,
# ROCm, full coaching prompt with system + 2-3 KB retrieved context) is
# 30-40 s warm, up to ~50 s cold. Previous 45 s response budget
# triggered fallback for most real queries → user saw raw-data dumps.
# New budget is generous enough to cover cold starts; UI already shows
# a loading spinner via `is_loading_changed`, so long waits are visible.
# Override via env for faster GPUs: `CS2_DIALOGUE_TIMEOUT=60`.
_DIALOGUE_TIMEOUT = int(os.getenv("CS2_DIALOGUE_TIMEOUT", "180"))
_OPENING_TIMEOUT = int(os.getenv("CS2_OPENING_TIMEOUT", "90"))
_FALLBACK_RETRY_TIMEOUT = int(os.getenv("CS2_FALLBACK_TIMEOUT", "90"))
# F2 (TASKS#33): per-chunk stall budget for streaming responses. With
# streaming, first-token latency replaces whole-response latency as the
# felt wait, so the per-chunk gap budget can be much tighter than
# _DIALOGUE_TIMEOUT — no chunk for this many seconds aborts the stream.
_STREAM_STALL_TIMEOUT = float(os.getenv("CS2_CHAT_STREAM_STALL", "30"))


class _StreamCancelledError(Exception):
    """F2.3: raised inside the chunk callback to abort a cancelled stream."""


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
    "round_query": [
        "round ",
        "rounds ",
        "what happened in round",
        "show me round",
        "analyze round",
        "break down round",
        "round by round",
    ],
    "match_query": [
        "match",
        "demo",
        "game against",
        "versus",
        " vs ",
        "map on",
        "that game",
        "this match",
    ],
}

# DP-03: LLM-driven DB access. The tool phase lets the model query the
# match database itself instead of relying on regex extraction from the
# user's phrasing. Every argument the model supplies is UNTRUSTED — the
# executors validate against DB-known values before touching a query
# (zero-trust at the LLM boundary, same posture as BE-03).
_MAX_TOOL_ROUNDS = 4
_INVENTORY_LIMIT = 60
_DISAMBIGUATION_LIMIT = 12

COACH_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_matches",
            "description": (
                "List matches (parsed demo files) in the database. Optional "
                "filters: a team/player name fragment and/or a CS2 map name. "
                "Returns demo names with their round counts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team or player name fragment, e.g. 'faze'",
                    },
                    "map_name": {
                        "type": "string",
                        "description": "CS2 map name, e.g. 'mirage'",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_match_overview",
            "description": (
                "Full scoreboard for one match: every player's rating, K/D, "
                "ADR, HS%, KAST plus the highest-impact rounds. Requires the "
                "exact demo_name as returned by list_matches."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "demo_name": {
                        "type": "string",
                        "description": "Exact demo name from list_matches",
                    },
                },
                "required": ["demo_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_round_details",
            "description": (
                "Per-player breakdown of specific rounds in one match: kills, "
                "deaths, damage, headshots, opening kills, trades, utility and "
                "economy, plus a tick-level timeline when available. Max 5 "
                "rounds per call."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "demo_name": {
                        "type": "string",
                        "description": "Exact demo name from list_matches",
                    },
                    "rounds": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Round numbers (1-50), max 5",
                    },
                },
                "required": ["demo_name", "rounds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_player",
            "description": (
                "Verified profile and statistics for a player by name "
                "(pro or parsed-demo player)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Player name or nickname",
                    },
                },
                "required": ["name"],
            },
        },
    },
]

TOOLS_GUIDANCE = """\

DATABASE TOOLS:
You can query the real match database directly with the provided tools \
(list_matches, get_match_overview, get_round_details, lookup_player).
- When the user asks about matches, rounds, or players, CALL THE TOOLS to \
fetch real data — never claim you lack access to match data without first \
calling list_matches.
- When the user says "pick a match" or "choose a round", call list_matches, \
pick one, then drill down with get_round_details.
- If several matches fit the user's description (teams meet more than once), \
list the candidates and ask which one they mean — do NOT silently pick one.
- Tool output is real parsed-demo data: ground every claim in it, and say so \
when a detail is not present in the data."""

# DP-02: Regex patterns for extracting round numbers from user messages
_ROUND_PATTERN = re.compile(
    r"""
    \b(?:rounds?|r)\s*(\d{1,2})   # "round 5", "rounds 3", "R5", "round 12"
                                  # R4 MED: \b prevents the trailing 'r' of any
                                  # word ("...tips foR 5 players") matching and
                                  # misrouting the intent to round_query
    (?:\s*(?:-|–|\s+to\s+)\s*(\d{1,2}))?   # optional range: "5-10", "5 to 10"
    """,
    re.IGNORECASE | re.VERBOSE,
)

# DP-02: Pattern for extracting demo/match references from user messages
_DEMO_PATTERN = re.compile(
    r"(\w+)[\s-]+(?:vs|versus)[\s-]+(\w+)",  # "faze vs spirit", "navi-vs-furia"
    re.IGNORECASE,
)

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

# CHAT-02 (AUDIT §8.2): 2nd → 3rd person regex transforms. CoachingInsight
# messages are authored in 2nd person at NN-generation time (describing the
# analyzed player's weaknesses). When the user has no personal demos and we
# inject pro-player insights as reference material, the raw text reads as if
# the critique is aimed at the user. Transforms below re-attribute it to the
# pro. Order matters — longest/most-specific patterns first so, e.g.,
# "You were" matches before "You".
_SECOND_TO_THIRD_PERSON: Tuple[Tuple[re.Pattern, str], ...] = (
    # Full phrases first — capital-You variants keep capital "They" to
    # preserve sentence-start capitalization in sentences that begin with You.
    (re.compile(r"\bYou are\b"), "They are"),
    (re.compile(r"\byou are\b"), "they are"),
    (re.compile(r"\bYou were\b"), "They were"),
    (re.compile(r"\byou were\b"), "they were"),
    (re.compile(r"\bYou have\b"), "They have"),
    (re.compile(r"\byou have\b"), "they have"),
    (re.compile(r"\bYou will\b"), "They will"),
    (re.compile(r"\byou will\b"), "they will"),
    (re.compile(r"\bYou should\b"), "They should"),
    (re.compile(r"\byou should\b"), "they should"),
    (re.compile(r"\bYou can\b"), "They can"),
    (re.compile(r"\byou can\b"), "they can"),
    # Possessives — "Your X" / "your X" → "Their X" / "their X"
    (re.compile(r"\bYour\b"), "Their"),
    (re.compile(r"\byour\b"), "their"),
    (re.compile(r"\bYours\b"), "Theirs"),
    (re.compile(r"\byours\b"), "theirs"),
    # Bare pronouns last
    (re.compile(r"\bYou\b"), "They"),
    (re.compile(r"\byou\b"), "they"),
)


# BE-03 (AUDIT §9.1): CoachingInsight.message, pro nicknames, and HLTV bios
# are attacker-influenceable. Strip ASCII control chars (except newline / tab)
# to neutralise terminal-escape injection and hidden prompt-instruction bytes
# before the text lands in an LLM prompt. Matches Unicode categories Cc
# (control) minus \t (0x09) and \n (0x0A).
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _sanitize_llm_context(text: str, max_len: int = 300) -> str:
    """Sanitise free-form strings destined for an LLM prompt context block.

    Removes ASCII control chars and caps length. Does NOT attempt semantic
    prompt-injection defence — that is enforced via SYSTEM_PROMPT_TEMPLATE
    rules and the `{` / `}` escape at `_build_system_prompt`.
    """
    if not text:
        return ""
    cleaned = _CONTROL_CHARS_RE.sub("", text)
    return cleaned[:max_len]


def _to_third_person(text: str, pro_name: str, attribute: bool = True) -> str:
    """Re-narrate 2nd-person coaching text as 3rd-person about `pro_name`.

    Deterministic regex-based transform — no LLM call. Swaps you/your/yours
    pronouns to they/their/theirs. Optionally prepends an attribution prefix.

    Args:
        text: Original insight message (may contain "you"/"your").
        pro_name: Pro player the insight actually describes.
        attribute: When True, prepend `[pro_name] ` unless already present.
            Set False when the caller's surrounding format already names the
            pro (avoids double attribution).

    Returns:
        Rewritten text.
    """
    rewritten = text
    for pattern, replacement in _SECOND_TO_THIRD_PERSON:
        rewritten = pattern.sub(replacement, rewritten)
    if attribute:
        prefix = f"[{pro_name}] "
        if not rewritten.startswith(prefix):
            rewritten = prefix + rewritten
    return rewritten


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
- When match data, round data, or coaching insights are provided in the context, use them \
extensively — cite specific rounds, specific stats. \
Build your analysis around real data, not generic advice.
- Do NOT repeat raw numbers — interpret and explain them.
- Only claim neural-network/AI-model analysis when a context block explicitly says a \
model produced it; otherwise describe the insights as statistical analysis of parsed \
demos. Never invent neural provenance.

CRITICAL RULES FOR FACTUAL ACCURACY:
- When player data is provided in a "VERIFIED PLAYER DATA" block, use ONLY that data.
- When MATCH STATISTICS, BEST WINNING ROUNDS, or COACHING INSIGHTS \
blocks are present, treat them as real analyzed data from parsed demo files.
- NEVER guess or fabricate a player's team, nationality, real name, or statistics.
- If no verified data is available for a player, say: \
"I don't have verified data for that player in my database."
- Do NOT confuse different players — each player profile is distinct.
- When comparing players, only use data explicitly provided — do not invent statistics.
- If the user asks about a player and no VERIFIED PLAYER DATA block is present, \
say you don't have information on that player rather than guessing.

CRITICAL RULES FOR DATA PROVENANCE:
- If the player context says "pro reference data" or "no personal match data yet", \
treat the entire session as TUTOR MODE: the user has no personal demos, so every \
insight, statistic, round, and prediction in the retrieved context describes a \
PROFESSIONAL player — NEVER the user. In tutor mode you MUST:
  - Refer to the pro by name in 3rd person ("donk did X", "zywoo's KAST is Y").
  - NEVER use "you", "your", or "yours" when describing the retrieved data. \
Phrases like "your KAST", "you are 36% slower", "improve your opening duels" are \
FORBIDDEN and constitute fabricated personal critique.
  - Frame every lesson as: "[pro_name] shows X → what you (the user) can take away: Y".
  - If the retrieved text already contains "[{{pro_name}}]" attribution prefix, keep \
the attribution visible when echoing the stat.
- WR-79: Address the user as "you" or "player" in YOUR OWN advice only — NEVER use \
their configured username (shown in Player context above) in coaching advice.
- When retrieved coaching experiences mention specific player names, those are \
pro players from parsed demos — clearly attribute them (e.g., "in s1mple's \
data we see..."), do NOT conflate pro player names with the user.
- Only use possessive framing ("your", "you") when the context explicitly confirms \
the data comes from the user's personal matches (i.e., NOT in tutor mode).

CRITICAL RULES FOR DATA HONESTY (WR-78):
- Only describe events that appear in the data provided below. If the data shows \
kills, deaths, and damage but no positioning or timing detail, do NOT invent \
tactical narratives ("he pushed A long", "well-placed flash") — state what the \
numbers show and note that positioning detail is not available.
- Mark inferences explicitly. Use phrasing like "Based on the damage numbers, it \
appears..." or "The kill timing suggests..." — never present an inference as a \
stated fact from the data.
- When asked for detail the data does not contain, say "The available data doesn't \
include this level of detail" — never fill gaps with plausible-sounding CS2 text.
- Do NOT copy near-identical descriptions across multiple rounds with only the \
numbers changed. Each round has a unique tactical story — if you cannot distinguish \
them from the data, say so.
- When a ROUND TIMELINE block is provided, narrate those events faithfully — the \
timeline contains real tick-level data (positions as callouts, weapon changes, \
health deltas, engagement timing). Build your analysis around these grounded facts.
- When only MATCH STATISTICS or BEST WINNING ROUNDS blocks are available (aggregate \
stats without tick detail), limit your analysis to what those statistics show. \
Do NOT extrapolate positioning, movement, or tactical decisions from aggregate \
kill/death/damage numbers alone.\
"""


class CoachingDialogueEngine:
    """Multi-turn coaching dialogue with RAG-augmented responses."""

    MAX_CONTEXT_TURNS = 6
    RETRIEVAL_TOP_K = 3

    # DP-03: class-level defaults so test shells built via __new__ (the
    # established idiom in this suite) inherit a sane empty state. Every
    # write below rebinds an instance attribute — the class values are
    # never mutated.
    _known_demos: Optional[Dict[str, str]] = None
    _demo_rounds: Dict[str, int] = {}
    _match_inventory_cache: Optional[str] = None

    def __init__(self):
        self._llm = get_llm_service()
        self._player_lookup = None  # Lazy init to avoid import cost at startup
        self._player_context: Dict = {}
        self._system_prompt: str = ""
        self._history: List[Dict[str, str]] = []
        self._session_active: bool = False
        # C-06: Protect mutable session state from concurrent UI thread access
        self._state_lock = threading.Lock()
        self._warmed_up: bool = False
        # F2.3: lock-free cancellation flag for in-flight streaming responses
        # (checked per chunk; set by cancel_stream() from any thread).
        self._stream_cancel = threading.Event()
        # F3/TASKS#37: session-scoped cache for the NN context block so the
        # hybrid engine + baseline load at most once per session (latency
        # budget F3.3). None = not computed yet; "" = computed, nothing usable.
        self._session_ml_cache: Optional[str] = None
        # DP-03: session-scoped caches for DB-grounded match awareness.
        # _known_demos maps lowercase demo_name -> canonical demo_name and is
        # the validation whitelist for every LLM-supplied demo argument.
        self._known_demos: Optional[Dict[str, str]] = None
        self._demo_rounds: Dict[str, int] = {}
        self._match_inventory_cache: Optional[str] = None

        # Ensure hand-curated tactical knowledge is in the DB for RAG retrieval
        try:
            from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import (
                ensure_seed_knowledge_loaded,
            )

            ensure_seed_knowledge_loaded()
        except Exception as exc:
            logger.debug("Seed knowledge check skipped: %s", exc)

        # CHAT-01: Warm Gemma in a daemon thread so the first real chat
        # request does not pay the ~10 s model-load tax. No-op when LLM
        # is unavailable — is_available() caches the result anyway.
        threading.Thread(
            target=self._warmup_llm,
            name="gemma-warmup",
            daemon=True,
        ).start()

    def _warmup_llm(self) -> None:
        """Fire a tiny chat request so Gemma is hot before the user asks.

        Runs at engine construction on a daemon thread. Silent on failure;
        `is_available()` retries on next call.
        """
        try:
            if not self._llm.is_available():
                return
            # Minimal prompt — just forces Ollama to load the model into VRAM.
            self._llm.chat(
                [{"role": "user", "content": "ready?"}],
                system_prompt="Reply with a single word.",
            )
            self._warmed_up = True
            logger.info("Gemma warmup complete — chat engine hot.")
        except Exception as exc:
            logger.debug("Gemma warmup skipped: %s", exc)

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
        """Process a user question and return a coaching response.

        R4 LOW (concurrency): the state lock is held only to SNAPSHOT
        session state and to APPEND history afterwards — the LLM call (up
        to 180 s) runs outside it, so get_history()/clear_session() no
        longer block for a whole generation.
        """
        with self._state_lock:
            # F2.3 follow-up: a cancel flag left set by a previous stream
            # must not silently disable the DP-03 tool phase for
            # non-streaming turns (only respond_stream cleared it).
            self._stream_cancel.clear()
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

            # Build message array for Ollama (sliding window — history NOT
            # yet mutated); snapshot the prompt for use outside the lock.
            messages = self._build_chat_messages(augmented_user)
            system_prompt = self._system_prompt

        # F5-06: append user message only after we have a valid response so
        # that an LLM exception cannot leave the history in an inconsistent
        # state. WR-06: timeout protection prevents UI hangs. Runs UNLOCKED.
        # DP-03: tool phase first — the model queries the DB itself; the
        # legacy retrieval-stuffed path is the fallback for models without
        # tool support (or any tool-phase failure).
        response = None
        try:
            response = self._respond_via_tools(messages, system_prompt)
        except Exception as exc:
            logger.warning("Tool phase raised — falling back to plain chat: %s", exc)
        if not response:
            try:
                response = self._chat_with_timeout(messages, system_prompt)
            except TimeoutError:
                logger.warning("Dialogue response timed out for user query")
                response = self._fallback_response(user_message, intent)
            except Exception as exc:
                logger.error("LLM chat raised an exception: %s", exc)
                response = self._fallback_response(user_message, intent)

        # Check for LLM error markers → fall back
        if response.startswith("[LLM"):
            logger.warning("LLM error in dialogue: %s", response)
            response = self._fallback_response(user_message, intent)

        # Re-acquire to append now that we have a usable response. If the
        # session was cleared while generating, drop the exchange instead
        # of resurrecting a dead session's history.
        with self._state_lock:
            if self._session_active:
                self._history.append({"role": "user", "content": user_message})
                self._history.append({"role": "assistant", "content": response})
        return response

    def cancel_stream(self) -> None:
        """F2.3: abort any in-flight streaming response (lock-free; safe from
        any thread). The stream loop observes the flag on its next chunk."""
        self._stream_cancel.set()

    def respond_stream(self, user_message: str, progress_callback=None) -> str:
        """F2 (TASKS#33): streaming variant of respond().

        ``progress_callback`` receives the ACCUMULATED assistant text per
        chunk (DR-14: whole-message re-render, never fragments). Mirrors
        respond() exactly — same intent/retrieval/prompt build, same F5-06
        history discipline (history mutates only once a usable final
        response exists), same fallback ladder. Cancellation (cancel_stream)
        aborts without mutating history and returns "".
        """
        with self._state_lock:
            if not self._session_active:
                if self._llm.is_available():
                    self._session_active = True
                    self._system_prompt = self._system_prompt or self._build_system_prompt()
                else:
                    return self._fallback_response(
                        user_message, self._classify_intent(user_message)
                    )

            intent = self._classify_intent(user_message)
            retrieval_context = self._retrieve_context(user_message, intent)

            augmented_user = user_message
            if retrieval_context:
                augmented_user = (
                    f"{user_message}\n\n"
                    f"[Retrieved coaching knowledge for reference — "
                    f"use if relevant, ignore if not]\n{retrieval_context}"
                )

            messages = self._build_chat_messages(augmented_user)
            system_prompt = self._system_prompt

            self._stream_cancel.clear()

        # R4 LOW (concurrency): the streaming loop runs UNLOCKED — same
        # snapshot/re-acquire discipline as respond(), so cancel_stream(),
        # get_history() and clear_session() stay responsive mid-generation.
        def _on_chunk(accumulated: str) -> None:
            if self._stream_cancel.is_set():
                raise _StreamCancelledError()
            if progress_callback is not None:
                progress_callback(accumulated)

        # DP-03: tool phase first. Tool rounds are non-streaming (function
        # calls have no useful token stream); the UI gets whole-message
        # progress pushes ("checking the database...") per DR-14, then one
        # final push with the complete answer. Legacy streamed path remains
        # the fallback for models without tool support.
        response = None
        try:

            def _tool_notify(tool_name: str) -> None:
                if progress_callback is not None:
                    progress_callback(f"_Checking the match database ({tool_name})..._")

            response = self._respond_via_tools(messages, system_prompt, notify=_tool_notify)
            if response == "" and self._stream_cancel.is_set():
                logger.info("F2.3: tool-phase response cancelled — history unchanged")
                return ""
            if response and progress_callback is not None:
                progress_callback(response)
        except Exception as exc:
            logger.warning("Tool phase raised — falling back to streaming: %s", exc)
            response = None

        if not response:
            try:
                response = self._llm.chat_stream(
                    messages,
                    system_prompt=system_prompt,
                    on_chunk=_on_chunk,
                    stall_timeout=_STREAM_STALL_TIMEOUT,
                )
            except _StreamCancelledError:
                logger.info("F2.3: streaming response cancelled — history unchanged")
                return ""
            except Exception as exc:
                # Stall (requests.Timeout), connection loss, malformed chunk —
                # same fallback ladder as respond(); the UI replaces any
                # partial render with the fallback text (logged loudly).
                logger.warning(
                    "F2.5: stream failed (%s: %s) — falling back to offline response",
                    type(exc).__name__,
                    exc,
                )
                response = self._fallback_response(user_message, intent)

        if not response or response.startswith("[LLM"):
            logger.warning("LLM error in streamed dialogue: %s", response or "(empty)")
            response = self._fallback_response(user_message, intent)

        # F5-06: history mutates only now, with a usable final response —
        # re-acquired; a session cleared mid-stream drops the exchange.
        with self._state_lock:
            if self._session_active:
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
            self._session_ml_cache = None  # F3: NN context is per-session
            # DP-03: match awareness is refreshed per session so newly
            # ingested demos become visible without a restart.
            self._known_demos = None
            self._demo_rounds = {}
            self._match_inventory_cache = None
            logger.info("Dialogue session cleared")

    # ── DP-03: DB-grounded match awareness ───────────────────────────────

    def _get_known_demos(self) -> Dict[str, str]:
        """Cached map of lowercase demo_name -> canonical demo_name.

        Doubles as the zero-trust whitelist for LLM-supplied demo names —
        a demo argument that does not resolve through this map is rejected
        before it reaches any query.
        """
        if self._known_demos is not None:
            return self._known_demos
        known: Dict[str, str] = {}
        rounds: Dict[str, int] = {}
        try:
            db = get_db_manager()
            with db.get_session() as session:
                names = session.exec(select(PlayerMatchStats.demo_name).distinct()).all()
                for n in names:
                    if n:
                        known[n.lower()] = n
                round_rows = session.exec(
                    select(
                        RoundStats.demo_name,
                        func.max(RoundStats.round_number),
                    ).group_by(RoundStats.demo_name)
                ).all()
                for demo, max_round in round_rows:
                    if demo:
                        rounds[demo] = int(max_round or 0)
        except Exception as exc:
            logger.warning("Failed to load demo inventory: %s", exc)
        self._known_demos = known
        self._demo_rounds = rounds
        return known

    def _format_demo_line(self, demo: str) -> str:
        rounds = self._demo_rounds.get(demo)
        return f"{demo} ({rounds} rounds)" if rounds else f"{demo} (stats only)"

    def _get_match_inventory(self) -> str:
        """Compact match-inventory block for the system prompt.

        Without this the LLM has no idea which matches exist and answers
        "I have no access to match data" — the coach must be able to see
        the menu before it can pick from it.
        """
        if self._match_inventory_cache is not None:
            return self._match_inventory_cache
        known = self._get_known_demos()
        if not known:
            self._match_inventory_cache = ""
            return ""
        demos = sorted(known.values())
        # Demos with parsed rounds first — they support real drill-down.
        with_rounds = [d for d in demos if self._demo_rounds.get(d)]
        stats_only = [d for d in demos if not self._demo_rounds.get(d)]
        ordered = with_rounds + stats_only
        shown = ordered[:_INVENTORY_LIMIT]
        lines = [
            f"MATCH DATABASE INVENTORY ({len(demos)} matches; "
            f"{len(with_rounds)} with full round data):"
        ]
        lines.extend(f"  - {self._format_demo_line(d)}" for d in shown)
        remaining = len(ordered) - len(shown)
        if remaining > 0:
            lines.append(f"  ...and {remaining} more (filter with the list_matches tool).")
        self._match_inventory_cache = "\n".join(lines)
        return self._match_inventory_cache

    # ── F3/TASKS#37: baseline-deviation input beyond player_query ────────

    _NN_COACHING_INTENTS = ("positioning", "aim", "utility", "economy", "general")

    def _should_inject_session_ml(self, intent: str) -> bool:
        """F3.2 (revised with D-02): inject the baseline-deviation block for
        coaching intents whenever the session player has match stats.

        The old ``using_pro_reference`` gate selected exactly the sessions
        where the player has NO data (tutor mode = zero personal insight
        rows), then analyzed that player's own PlayerMatchStats — so the
        block was structurally near-inert even before the D-02 breakage.
        _get_ml_analysis_for_players already returns "" when no stats
        exist, and the "" is session-cached, so this stays cheap.
        """
        return intent in self._NN_COACHING_INTENTS

    def _get_session_ml_context(self) -> str:
        """F3.3: cached, session-scoped baseline-deviation analysis for the
        active player (D-02: statistical Z-scores, no neural model).

        The hybrid engine + pro baseline load exactly once per session; a
        session without a player (or with no usable output) caches ""
        so later turns pay nothing.
        """
        if self._session_ml_cache is not None:
            return self._session_ml_cache
        player = self._player_context.get("player_name")
        if not player or player == "Unknown":
            self._session_ml_cache = ""
            return ""
        try:
            self._session_ml_cache = self._get_ml_analysis_for_players([player]) or ""
        except Exception as exc:
            logger.warning("F3: session NN context failed: %s", exc, exc_info=True)
            self._session_ml_cache = ""
        return self._session_ml_cache

    @property
    def is_available(self) -> bool:
        """True when Ollama is reachable."""
        return self._llm.is_available()

    def _chat_with_timeout(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        timeout: int = _DIALOGUE_TIMEOUT,
    ) -> str:
        """Run LLM chat with timeout protection (WR-06).

        Prevents UI hangs when Ollama stalls or network I/O blocks.
        Returns the LLM response or raises TimeoutError.
        """
        result: List[Optional[str]] = [None]
        exc_holder: List[Optional[Exception]] = [None]

        def target():
            try:
                result[0] = self._llm.chat(messages, system_prompt=system_prompt)
            except Exception as e:
                exc_holder[0] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            logger.warning(
                "LLM dialogue timed out after %ds (%d messages in context)",
                timeout,
                len(messages),
            )
            raise TimeoutError(f"LLM chat timed out after {timeout}s")
        if exc_holder[0]:
            raise exc_holder[0]
        return result[0] or ""

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
                    f"{len(insights)} insights available — these describe PRO "
                    f"players' gameplay, NOT the user's):"
                )
                for ins in insights[:10]:
                    pro = ins.get("player_name", "Pro")
                    # CHAT-02: transform 2nd-person text to 3rd-person.
                    # Outer format already names the pro, so suppress the
                    # attribution prefix to avoid "donk — title: [donk] they…".
                    # BE-03: sanitise message before LLM exposure.
                    clean_msg = _sanitize_llm_context(ins["message"], max_len=300)
                    retold = _to_third_person(clean_msg, pro, attribute=False)
                    parts.append(f"  - [{ins['severity']}] {pro} — {ins['title']}: {retold}")
            else:
                parts.append(f"Recent coaching insights ({len(insights)} available):")
                for ins in insights[:10]:
                    clean_msg = _sanitize_llm_context(ins["message"], max_len=300)
                    parts.append(f"  - [{ins['severity']}] {ins['title']}: {clean_msg}")

        # BE-03 (AUDIT §9.1): every value in `player_context_str` is sourced
        # from `CoachingInsight.message`, pro nicknames, and HLTV-scraped
        # bios — all attacker-influenceable through poisoned demos or HLTV
        # rows. Two attack surfaces:
        #   1. Literal `{` / `}` braces would be interpreted by `str.format`
        #      below → `KeyError` (DoS) or unintended substitution.
        #   2. Adversarial instructions embedded in nicknames / messages
        #      could attempt prompt injection downstream. The brace escape
        #      neutralises the `format()` exploit; further LLM-side
        #      hardening is in SYSTEM_PROMPT_TEMPLATE rules.
        # DP-03: make the match inventory part of the coach's world — the
        # LLM cannot "choose a match" it has never been shown.
        inventory = self._get_match_inventory()
        if inventory:
            parts.append("")
            parts.append(inventory)

        player_context_str = "\n".join(parts)
        safe_context = player_context_str.replace("{", "{{").replace("}", "}}")
        return SYSTEM_PROMPT_TEMPLATE.format(player_context=safe_context)

    def _get_player_lookup(self):
        """Lazy-init PlayerLookupService to avoid import cost at startup."""
        if self._player_lookup is None:
            from Programma_CS2_RENAN.backend.services.player_lookup import PlayerLookupService

            self._player_lookup = PlayerLookupService()
        return self._player_lookup

    def _classify_intent(self, message: str) -> str:
        """Keyword-based intent classification with player entity detection.

        DP-02: round_query and match_query take priority when explicit round
        numbers or match references are detected, since the user is asking
        for specific data drill-down rather than general coaching advice.
        """
        message_lower = message.lower()

        # DP-02: Check for round numbers first — strongest signal
        round_numbers = self._parse_round_numbers(message)
        if round_numbers:
            return "round_query"

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

    @staticmethod
    def _parse_round_numbers(text: str) -> List[int]:
        """DP-02: Extract round numbers from user message.

        Handles: "round 5", "R5", "rounds 5-10", "round 5 to 10",
        "rounds 3, 7, and 12" (via multiple matches).
        Returns sorted, deduplicated list of round numbers.
        """
        rounds: set = set()
        for match in _ROUND_PATTERN.finditer(text):
            start = int(match.group(1))
            end_str = match.group(2)
            if end_str:
                end = int(end_str)
                rounds.update(range(start, min(end, 50) + 1))
            else:
                rounds.add(start)
        return sorted(rounds)

    def _resolve_demo_candidates(self, text: str) -> List[str]:
        """DP-03: Resolve ALL demos matching the user's message.

        Predecessor `_resolve_demo_name` returned the FIRST demo containing
        both team fragments — with 4 FaZe–Spirit demos in the DB the coach
        silently narrated an arbitrary one every time. Now every candidate
        is returned; the caller disambiguates (1 → use it, >1 → ask the
        user, 0 → fall back to the session demo).
        """
        demo_match = _DEMO_PATTERN.search(text)
        if demo_match:
            team_a = demo_match.group(1).lower()
            team_b = demo_match.group(2).lower()
            candidates = [
                canonical
                for lower, canonical in self._get_known_demos().items()
                if team_a in lower and team_b in lower
            ]
            # A map mention narrows the candidate set ("faze vs spirit on nuke").
            map_name = self._detect_map_mention(text)
            if map_name and len(candidates) > 1:
                narrowed = [c for c in candidates if map_name in c.lower()]
                if narrowed:
                    candidates = narrowed
            if candidates:
                return sorted(candidates)

        session_demo = self._player_context.get("demo_name")
        return [session_demo] if session_demo else []

    def _resolve_demo_name(self, text: str) -> Optional[str]:
        """Single-demo resolution: unambiguous candidate or None."""
        candidates = self._resolve_demo_candidates(text)
        return candidates[0] if len(candidates) == 1 else None

    def _disambiguation_block(self, candidates: List[str]) -> str:
        """Context block instructing the coach to ask which match is meant."""
        shown = candidates[:_DISAMBIGUATION_LIMIT]
        lines = [f"MULTIPLE MATCHES FOUND ({len(candidates)} candidates in the database):"]
        lines.extend(f"  - {self._format_demo_line(d)}" for d in shown)
        if len(candidates) > len(shown):
            lines.append(f"  ...and {len(candidates) - len(shown)} more.")
        lines.append(
            "Ask the user which specific match they mean before analyzing — "
            "do NOT silently pick one."
        )
        return "\n".join(lines)

    # ── DP-03: agentic tool phase ────────────────────────────────────────

    _TOOL_ARG_MAX_LEN = 40
    _TOOL_LIST_LIMIT = 40
    _TOOL_MAX_ROUNDS_PER_CALL = 5
    _TOOL_RESULT_MAX_LEN = 8000
    _TEAM_FRAGMENT_RE = re.compile(r"[^a-z0-9 _-]")
    _CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    def _sanitize_tool_result(self, text: str) -> str:
        """BE-03 posture for the tool channel: DB-sourced text (player
        nicknames, demo names, insight prose) flows back into the prompt as
        tool results — strip control characters and cap length before the
        LLM sees it."""
        clean = self._CONTROL_CHARS_RE.sub("", text)
        if len(clean) > self._TOOL_RESULT_MAX_LEN:
            clean = clean[: self._TOOL_RESULT_MAX_LEN] + "\n[...truncated]"
        return clean

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Execute one LLM-requested tool. Every argument is UNTRUSTED:
        demo names must resolve through the `_get_known_demos` whitelist,
        strings are length-capped and character-filtered, round numbers are
        bounded ints. Errors return short 'ERROR: ...' strings the model can
        recover from — never exception details."""
        return self._sanitize_tool_result(self._execute_tool_inner(name, args))

    def _execute_tool_inner(self, name: str, args: Dict[str, Any]) -> str:
        try:
            if name == "list_matches":
                return self._tool_list_matches(
                    str(args.get("team", "") or ""), str(args.get("map_name", "") or "")
                )
            if name == "get_match_overview":
                canonical = self._canonical_demo(args.get("demo_name"))
                if not canonical:
                    return "ERROR: unknown demo_name. Call list_matches for exact names."
                return self._retrieve_match_overview(canonical) or "ERROR: no data for this match."
            if name == "get_round_details":
                canonical = self._canonical_demo(args.get("demo_name"))
                if not canonical:
                    return "ERROR: unknown demo_name. Call list_matches for exact names."
                rounds = self._validate_rounds(args.get("rounds"))
                if not rounds:
                    return "ERROR: 'rounds' must be integers between 1 and 50 (max 5)."
                return (
                    self._retrieve_round_drill_down(canonical, rounds, "")
                    or "ERROR: no round data for those rounds in this match."
                )
            if name == "lookup_player":
                player = str(args.get("name", "") or "").strip()[: self._TOOL_ARG_MAX_LEN]
                if not player:
                    return "ERROR: 'name' is required."
                lookup = self._get_player_lookup()
                profile = lookup.lookup_player(player)
                if not profile:
                    return f"ERROR: no verified data for player '{player}' in the database."
                return lookup.format_player_context(profile)
            return f"ERROR: unknown tool '{name[:32]}'."
        except Exception as exc:
            logger.warning("Tool '%s' execution failed: %s", name, exc, exc_info=True)
            return "ERROR: tool execution failed."

    def _canonical_demo(self, raw: Any) -> Optional[str]:
        """Whitelist-resolve an LLM-supplied demo name (case-insensitive)."""
        if not isinstance(raw, str):
            return None
        return self._get_known_demos().get(raw.strip().lower())

    def _validate_rounds(self, raw: Any) -> List[int]:
        if not isinstance(raw, (list, tuple)):
            return []
        rounds: List[int] = []
        for item in raw:
            try:
                n = int(item)
            except (TypeError, ValueError):
                continue
            if 1 <= n <= 50:
                rounds.append(n)
        return sorted(set(rounds))[: self._TOOL_MAX_ROUNDS_PER_CALL]

    def _tool_list_matches(self, team: str, map_name: str) -> str:
        team_frag = self._TEAM_FRAGMENT_RE.sub("", team.strip().lower())[: self._TOOL_ARG_MAX_LEN]
        map_frag = map_name.strip().lower()
        if map_frag and map_frag not in _CS2_MAP_NAMES:
            map_frag = ""
        demos = sorted(self._get_known_demos().values())
        if team_frag:
            demos = [d for d in demos if team_frag in d.lower()]
        if map_frag:
            demos = [d for d in demos if map_frag in d.lower()]
        if not demos:
            return "No matches found for those filters."
        shown = demos[: self._TOOL_LIST_LIMIT]
        lines = [f"{len(demos)} matches found:"]
        lines.extend(f"  - {self._format_demo_line(d)}" for d in shown)
        if len(demos) > len(shown):
            lines.append(f"  ...and {len(demos) - len(shown)} more (narrow the filter).")
        return "\n".join(lines)

    def _respond_via_tools(self, messages, system_prompt, notify=None) -> Optional[str]:
        """DP-03: agentic exchange — the LLM queries the DB via tools.

        Runs up to _MAX_TOOL_ROUNDS tool rounds, then one forced-answer
        round. Returns the final answer text, or None when the model/path
        cannot do tools (caller falls back to the legacy retrieval path).
        ``notify(tool_name)`` fires before each tool execution so streaming
        callers can render progress. Cancellation via _stream_cancel aborts
        between rounds with "" (same contract as respond_stream).
        """
        if self._llm.tools_supported is False:
            return None
        sys_p = system_prompt + TOOLS_GUIDANCE
        work: List[Dict[str, Any]] = [dict(m) for m in messages]

        for round_no in range(_MAX_TOOL_ROUNDS + 1):
            if self._stream_cancel.is_set():
                return ""
            resp = self._llm.chat_tools(
                work,
                system_prompt=sys_p,
                tools=COACH_TOOLS,
                read_timeout=float(_DIALOGUE_TIMEOUT),
            )
            content = resp.get("content", "")
            calls = resp.get("tool_calls", [])
            if content.startswith("[LLM"):
                logger.warning("Tool phase aborted: %s", content)
                return None
            if calls and round_no < _MAX_TOOL_ROUNDS:
                work.append({"role": "assistant", "content": content, "tool_calls": calls})
                for call in calls[:4]:
                    fn = call.get("function") or {}
                    tool_name = str(fn.get("name", ""))
                    raw_args = fn.get("arguments") or {}
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except (ValueError, TypeError):
                            raw_args = {}
                    if not isinstance(raw_args, dict):
                        raw_args = {}
                    if notify is not None:
                        notify(tool_name)
                    result = self._execute_tool(tool_name, raw_args)
                    tool_msg: Dict[str, Any] = {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": result,
                    }
                    if call.get("id"):
                        tool_msg["tool_call_id"] = call["id"]
                    work.append(tool_msg)
                continue
            # No tool calls (or budget exhausted): the content is the answer.
            if content.strip():
                return content
            return None
        return None

    def _retrieve_context(self, user_message: str, intent: str) -> str:
        """Retrieve RAG knowledge and experiences relevant to the question."""
        blocks: List[str] = []

        # F3/TASKS#37: baseline-deviation analysis for coaching intents
        # (cached per session). Player-mention questions keep their own
        # richer per-player path. (D-02: no neural model runs here.)
        if self._should_inject_session_ml(intent):
            ml_block = self._get_session_ml_context()
            if ml_block:
                blocks.append(ml_block)

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

        # DP-02/DP-03: Round-specific drill-down when the user asks about
        # specific rounds or a specific match. Ambiguous team pairings
        # (teams that met more than once) surface ALL candidates and
        # instruct the coach to ask instead of silently picking one.
        round_numbers = self._parse_round_numbers(user_message)
        candidates = self._resolve_demo_candidates(user_message)
        demo_name = candidates[0] if len(candidates) == 1 else None

        if len(candidates) > 1 and (round_numbers or intent == "match_query"):
            blocks.append(self._disambiguation_block(candidates))
        elif round_numbers and demo_name:
            try:
                round_ctx = self._retrieve_round_drill_down(demo_name, round_numbers, user_message)
                if round_ctx:
                    blocks.append(round_ctx)
            except Exception as exc:
                logger.warning("Round drill-down retrieval failed: %s", exc)
        elif intent == "match_query" and demo_name:
            try:
                match_ctx = self._retrieve_match_overview(demo_name)
                if match_ctx:
                    blocks.append(match_ctx)
            except Exception as exc:
                logger.warning("Match overview retrieval failed: %s", exc)

        # Analytical context: match stats, round data, and stored coaching
        # insights for any player mentioned in the query (when no specific
        # round/match drill-down was triggered above).
        if not round_numbers and intent != "match_query":
            try:
                analytical = self._retrieve_analytical_context(user_message, intent)
                if analytical:
                    blocks.append(analytical)
            except Exception as exc:
                logger.warning("Analytical context retrieval failed: %s", exc)

        return "\n\n".join(blocks)

    # ------------------------------------------------------------------
    # Analytical context — match stats, round data, stored insights
    # ------------------------------------------------------------------

    def _retrieve_analytical_context(self, user_message: str, intent: str) -> str:
        """Query match/round statistics and stored coaching insights
        for players mentioned in the user message.

        This bridges the gap between the post-match analysis pipeline
        (which stores insights during processing) and the interactive
        dialogue — so the LLM can reference real analyzed data when
        answering questions about specific players. (D-02: labels claim
        neural provenance only where a model actually produced the row.)
        """
        # Detect player names in the message
        mentioned: List[str] = []
        try:
            lookup = self._get_player_lookup()
            mentioned = lookup.detect_player_mentions(user_message)
        except Exception:
            logger.debug("player-mention detection failed", exc_info=True)

        if not mentioned:
            return ""

        blocks: List[str] = []

        db = get_db_manager()
        with db.get_session() as session:
            for name in mentioned[:5]:  # Cap to avoid oversized prompts
                player_block = self._format_player_analytics(session, name)
                if player_block:
                    blocks.append(player_block)

        # On-demand baseline Z-deviation analysis for mentioned players
        # (if the hybrid engine loads and player stats exist in the DB).
        ml_block = self._get_ml_analysis_for_players(mentioned[:3])
        if ml_block:
            blocks.append(ml_block)

        return "\n\n".join(blocks)

    def _retrieve_round_drill_down(
        self, demo_name: str, round_numbers: List[int], user_message: str
    ) -> str:
        """DP-02: Retrieve detailed data for specific rounds in a specific demo.

        Queries RoundStats for requested rounds, reconstructs tick-level
        timelines via RoundReconstructor, and formats for LLM context.
        """
        blocks: List[str] = []
        db = get_db_manager()

        with db.get_session() as session:
            # Get all players in this demo's requested rounds
            round_stmt = (
                select(RoundStats)
                .where(RoundStats.demo_name == demo_name)
                .where(RoundStats.round_number.in_(round_numbers))  # type: ignore[union-attr]
                .order_by(RoundStats.round_number, desc(RoundStats.kills))
            )
            round_rows = session.exec(round_stmt).all()

            if not round_rows:
                # Try partial match on demo_name (user may abbreviate)
                all_demos = session.exec(select(PlayerMatchStats.demo_name).distinct()).all()
                for d in all_demos:
                    if d and demo_name.lower() in d.lower():
                        demo_name = d
                        round_rows = session.exec(
                            select(RoundStats)
                            .where(RoundStats.demo_name == demo_name)
                            .where(RoundStats.round_number.in_(round_numbers))  # type: ignore[union-attr]
                            .order_by(RoundStats.round_number, desc(RoundStats.kills))
                        ).all()
                        break

            if not round_rows:
                return ""

            # Group by round number
            rounds_by_num: Dict[int, List] = {}
            for r in round_rows:
                rounds_by_num.setdefault(r.round_number, []).append(r)

            # Format round-level statistics
            lines = [
                f"ROUND DRILL-DOWN for {demo_name} "
                f"(rounds {', '.join(str(n) for n in sorted(rounds_by_num))})"
                f" — data from parsed demo file:"
            ]

            for rnum in sorted(rounds_by_num):
                players = rounds_by_num[rnum]
                won = any(p.round_won for p in players)
                result = "WON" if won else "LOST"
                lines.append(f"\n  --- Round {rnum} ({result}) ---")
                for p in players:
                    opener = " OPENER" if p.opening_kill else ""
                    traded = " TRADED" if p.was_traded else ""
                    hs = f" {p.headshot_kills}HS" if p.headshot_kills else ""
                    util = []
                    if p.flashes_thrown:
                        util.append(f"{p.flashes_thrown}flash")
                    if p.smokes_thrown:
                        util.append(f"{p.smokes_thrown}smoke")
                    if p.he_damage or p.molotov_damage:
                        util.append(f"{(p.he_damage or 0) + (p.molotov_damage or 0):.0f}utildmg")
                    util_str = f" [{', '.join(util)}]" if util else ""
                    lines.append(
                        f"    {p.player_name} ({p.side}): "
                        f"{p.kills}K/{p.deaths}D {p.damage_dealt}dmg{hs}{opener}{traded}"
                        f" ${p.equipment_value}{util_str}"
                    )
            blocks.append("\n".join(lines))

        # Tick-level round reconstruction for detailed timelines
        # Detect which player the user is asking about (from message or session)
        player_name = None
        try:
            lookup = self._get_player_lookup()
            mentions = lookup.detect_player_mentions(user_message)
            if mentions:
                player_name = mentions[0]
        except Exception:
            logger.debug("player-mention detection failed", exc_info=True)
        if not player_name:
            player_name = self._player_context.get("player_name")

        if player_name and round_numbers:
            try:
                from Programma_CS2_RENAN.backend.processing.round_reconstructor import (
                    get_round_reconstructor,
                )

                reconstructor = get_round_reconstructor()
                # Cap at 5 rounds to avoid oversized context
                timelines = reconstructor.reconstruct_rounds(
                    demo_name, player_name, round_numbers[:5]
                )
                for tl in timelines:
                    if tl and tl.events:
                        blocks.append(tl.format_for_llm())
            except Exception:
                logger.debug(
                    "Round reconstruction unavailable for %s rounds %s",
                    player_name,
                    round_numbers,
                    exc_info=True,
                )

        return "\n\n".join(blocks)

    def _retrieve_match_overview(self, demo_name: str) -> str:
        """DP-02: Retrieve a full match overview for a specific demo.

        Returns all player stats and key rounds for the match.
        """
        db = get_db_manager()
        parts: List[str] = []

        with db.get_session() as session:
            # Match-level stats for all players
            match_stmt = (
                select(PlayerMatchStats)
                .where(PlayerMatchStats.demo_name == demo_name)
                .order_by(desc(PlayerMatchStats.rating))
            )
            matches = session.exec(match_stmt).all()

            if not matches:
                # Partial match
                all_demos = session.exec(select(PlayerMatchStats.demo_name).distinct()).all()
                for d in all_demos:
                    if d and demo_name.lower() in d.lower():
                        demo_name = d
                        matches = session.exec(
                            select(PlayerMatchStats)
                            .where(PlayerMatchStats.demo_name == demo_name)
                            .order_by(desc(PlayerMatchStats.rating))
                        ).all()
                        break

            if not matches:
                return ""

            lines = [f"MATCH OVERVIEW for {demo_name} ({len(matches)} players):"]
            for m in matches:
                lines.append(
                    f"  {m.player_name}: Rating={m.rating:.2f} "
                    f"K/D={m.kd_ratio:.2f} ADR={m.avg_adr:.1f} "
                    f"HS%={m.avg_hs:.0%} KAST={m.avg_kast:.0%}"
                )
            parts.append("\n".join(lines))

            # Key rounds: highest-impact rounds across all players
            key_stmt = (
                select(RoundStats)
                .where(RoundStats.demo_name == demo_name)
                .where(RoundStats.kills >= 2)  # type: ignore[union-attr]
                .order_by(desc(RoundStats.kills), desc(RoundStats.damage_dealt))
                .limit(20)
            )
            key_rounds = session.exec(key_stmt).all()

            if key_rounds:
                lines = ["KEY ROUNDS (multi-kill rounds, sorted by impact):"]
                for r in key_rounds:
                    opener = " OPENER" if r.opening_kill else ""
                    lines.append(
                        f"  R{r.round_number} {r.player_name} ({r.side}): "
                        f"{r.kills}K/{r.deaths}D {r.damage_dealt}dmg{opener}"
                    )
                parts.append("\n".join(lines))

        return "\n\n".join(parts)

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
            # D-02 relabel: these rows are parsed-demo statistics, not model
            # output — the old "analyzed by ML pipeline" overclaimed.
            lines = [
                f"MATCH STATISTICS for {player_name} "
                f"({len(matches)} recent matches from parsed demo files):"
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
                    # R4 MED: None-guard both addends — if exactly one is None
                    # the guard passes but the addition raised TypeError,
                    # discarding the whole analytical context block (the
                    # parallel site at the player loop already guards).
                    util.append(f"{(r.he_damage or 0) + (r.molotov_damage or 0):.0f}utildmg")
                util_str = f" [{', '.join(util)}]" if util else ""

                lines.append(
                    f"  R{r.round_number} ({r.side}) on {r.demo_name}: "
                    f"{r.kills}K/{r.deaths}D {r.damage_dealt}dmg{hs}{opener}{trades}"
                    f" ${r.equipment_value}{util_str}"
                )
            parts.append("\n".join(lines))

        # --- Round timelines (WR-76: tick-level reconstruction) ---
        if rounds:
            try:
                from Programma_CS2_RENAN.backend.processing.round_reconstructor import (
                    get_round_reconstructor,
                )

                reconstructor = get_round_reconstructor()
                # Reconstruct top 3 rounds for detailed timelines
                top_rounds = rounds[:3]
                for r in top_rounds:
                    timeline = reconstructor.reconstruct_round(
                        r.demo_name, r.round_number, player_name
                    )
                    if timeline and timeline.events:
                        parts.append(timeline.format_for_llm())
            except Exception:
                logger.debug("Round reconstruction unavailable for %s", player_name, exc_info=True)

        # --- Coaching insights already generated by the analysis pipeline ---
        # D-02 relabel: CoachingInsight rows come from the correction engine,
        # longitudinal trends, Phase-6 engines, COPER and hybrid baseline-Z
        # synthesis; only RAP-written (and future armed-JEPA) rows are
        # genuinely NN-derived, and per-row provenance is not stored — so
        # the block claims neither "neural" nor "not neural" (Law I).
        insight_stmt = (
            select(CoachingInsight)
            .where(CoachingInsight.player_name == player_name)
            .order_by(desc(CoachingInsight.created_at))
            .limit(10)
        )
        insights = session.exec(insight_stmt).all()

        if insights:
            lines = [
                f"COACHING INSIGHTS for {player_name} "
                f"({len(insights)} insights from the analysis pipeline — "
                f"describing {player_name}'s gameplay, rendered in 3rd person):"
            ]
            for ins in insights:
                # CHAT-02: re-attribute to the pro so LLM cannot echo as "your".
                # Header already names the player — suppress inline prefix.
                # BE-03: sanitise message before LLM exposure.
                clean_msg = _sanitize_llm_context(ins.message, max_len=300)
                retold = _to_third_person(clean_msg, player_name, attribute=False)
                lines.append(f"  [{ins.severity}] {ins.title} ({ins.focus_area}): {retold}")
            parts.append("\n".join(lines))

        if not parts:
            return ""

        return "\n".join(parts)

    @staticmethod
    def _get_ml_analysis_for_players(player_names: List[str]) -> str:
        """Baseline Z-deviation analysis for mentioned players.

        Aggregates each player's match stats and synthesizes pro-baseline
        Z-score insights via the hybrid engine. NO neural model runs here
        (F-0028 removed that seam; neural output enters coaching only via
        JEPAInsightAdapter, 26-HYB-01 — armed-JEPA output reaches chat as
        persisted 'World-model read:' CoachingInsight rows instead).

        IMPORTANT: does NOT touch the RAG retriever, to avoid
        double-loading SBERT, which causes CUDA OOM on GPUs with
        < 4 GiB VRAM.
        """
        try:
            from Programma_CS2_RENAN.backend.coaching.hybrid_engine import HybridCoachingEngine

            db = get_db_manager()
            blocks: List[str] = []

            # Create engine ONCE outside the loop (loads the pro baseline).
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

                # D-02 (F-0028 caller drift): the old chain called the deleted
                # _get_ml_predictions and the pre-F-0028 5-arg
                # _synthesize_insights — it raised AttributeError on EVERY
                # call, swallowed by the except below, so this block NEVER
                # rendered. Repaired against the current API: baseline
                # Z-deviations + synthesis only. Empty knowledge list keeps
                # SBERT unloaded (CUDA OOM guard); no map context in chat.
                deviations = engine._calculate_deviations(player_stats)
                insights = engine._synthesize_insights(
                    deviations,  # deviations
                    [],  # knowledge: none (SBERT guard)
                    None,  # map_name: chat has no map context
                    engine.pro_baseline,  # active_baseline
                )
                # Sort by priority (same as generate_insights)
                insights.sort(
                    key=lambda x: (
                        -engine._priority_value(x.priority),
                        -x.confidence,
                    )
                )

                if insights:
                    # D-02 relabel: no neural model ran — claiming "LIVE
                    # NEURAL NETWORK ANALYSIS" here was fabricated
                    # provenance (Law I; F-0028 renamed this exact math
                    # from 'ML confidence' to baseline math).
                    lines = [
                        f"BASELINE DEVIATION ANALYSIS for {name} "
                        f"(statistical Z-scores vs the pro baseline — no "
                        f"neural model ran; describing {name}'s gameplay "
                        f"in 3rd person):"
                    ]
                    for ins in insights[:5]:
                        # Header already names the player — suppress prefix.
                        # BE-03: sanitise message before LLM exposure.
                        clean_msg = _sanitize_llm_context(ins.message, max_len=250)
                        retold = _to_third_person(clean_msg, name, attribute=False)
                        lines.append(
                            f"  [{ins.priority.value.upper()}] {ins.title} "
                            f"(confidence={ins.confidence:.0%}): {retold}"
                        )
                    blocks.append("\n".join(lines))

            return "\n\n".join(blocks)

        except Exception as exc:
            # D-02: before the repair, an AttributeError died here on EVERY
            # call — a broad except must never be the only witness to a
            # dead feature, so the log now names the block it silences.
            logger.warning("Baseline deviation analysis block failed: %s", exc)
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

        using_pro = self._player_context.get("using_pro_reference", False)
        if using_pro:
            prompt_parts = [
                "Greet the player briefly. Acknowledge that you have access to a \
wealth of PROFESSIONAL match analysis (HLTV pro stats, parsed pro demos, \
ML-extracted pro patterns). Invite them to ask about any pro player, tactical \
concept, or specific round in your database.",
            ]
        else:
            prompt_parts = ["Greet the player briefly and offer to help with their gameplay."]
        insights = self._player_context.get("recent_insights", [])
        if insights and not using_pro:
            focus = self._player_context.get("primary_focus", "gameplay")
            prompt_parts.append(
                f"Mention that you've noticed their recent coaching focused on \
'{focus}' and ask if they'd like to dig deeper into that."
            )

        messages = [{"role": "user", "content": " ".join(prompt_parts)}]
        try:
            response = self._chat_with_timeout(
                messages, self._system_prompt, timeout=_OPENING_TIMEOUT
            )
        except (TimeoutError, Exception) as exc:
            logger.warning("Opening generation failed: %s", exc)
            return self._offline_opening()

        if response.startswith("[LLM"):
            return self._offline_opening()
        return response

    def _offline_opening(self) -> str:
        """Opening message when Ollama is unavailable."""
        name = self._player_context.get("player_name", "player")
        using_pro = self._player_context.get("using_pro_reference", False)
        focus = self._player_context.get("primary_focus")
        if using_pro:
            msg = (
                f"[Offline Coach] Hey {name}! I'm ready to analyze professional "
                f"gameplay with you. My database is loaded with HLTV pro stats, "
                f"parsed pro demos, and ML-extracted tactical patterns. "
                f"Ask me about any pro player, tactic, map concept, or specific match."
            )
        else:
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
                response = self._chat_with_timeout(
                    messages, system, timeout=_FALLBACK_RETRY_TIMEOUT
                )
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
