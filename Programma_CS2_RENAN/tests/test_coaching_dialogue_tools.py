"""
Tests for DP-03 — LLM tool-calling DB access in CoachingDialogueEngine.

Covers:
  _validate_rounds / _canonical_demo — zero-trust argument validation
  _tool_list_matches — filtered inventory listing
  _execute_tool — dispatch + unknown-tool/unknown-demo handling
  _resolve_demo_candidates / _disambiguation_block — multi-match handling
  _get_match_inventory — system-prompt inventory block
  _respond_via_tools — agentic loop against a scripted fake LLM
"""

import threading

from Programma_CS2_RENAN.backend.services.coaching_dialogue import (
    CoachingDialogueEngine,
)

KNOWN = {
    "faze-vs-spirit-m2-mirage": 24,
    "spirit-vs-faze-m1-mirage": 21,
    "spirit-vs-faze-m2-nuke": 19,
    "spirit-vs-faze-m3-vertigo": 30,
    "navi-vs-vitality-m1-inferno": 0,
}


def make_engine(llm=None):
    """Engine shell without __init__ (no DB, no warmup thread, no Ollama)."""
    eng = CoachingDialogueEngine.__new__(CoachingDialogueEngine)
    eng._llm = llm
    eng._player_lookup = None
    eng._player_context = {}
    eng._system_prompt = ""
    eng._history = []
    eng._session_active = False
    eng._state_lock = threading.Lock()
    eng._warmed_up = False
    eng._stream_cancel = threading.Event()
    eng._session_ml_cache = ""
    eng._known_demos = {k.lower(): k for k in KNOWN}
    eng._demo_rounds = {k: v for k, v in KNOWN.items() if v}
    eng._match_inventory_cache = None
    return eng


class FakeToolLLM:
    """Scripted chat_tools responses; records every call payload."""

    def __init__(self, script, tools_supported=True):
        self.script = list(script)
        self.calls = []
        self._tools_supported = tools_supported

    @property
    def tools_supported(self):
        return self._tools_supported

    def chat_tools(self, messages, system_prompt=None, tools=None, read_timeout=None):
        self.calls.append({"messages": list(messages), "system": system_prompt})
        if self.script:
            return self.script.pop(0)
        return {"content": "exhausted", "tool_calls": []}


class TestArgumentValidation:
    def test_validate_rounds_filters_and_caps(self):
        eng = make_engine()
        raw = [5, "7", 0, 51, "junk", None, 7, 3, 12, 15, 20]
        assert eng._validate_rounds(raw) == [3, 5, 7, 12, 15]

    def test_validate_rounds_rejects_non_list(self):
        eng = make_engine()
        assert eng._validate_rounds("5") == []
        assert eng._validate_rounds(None) == []

    def test_canonical_demo_case_insensitive(self):
        eng = make_engine()
        assert eng._canonical_demo("  SPIRIT-vs-FAZE-m2-nuke ") == "spirit-vs-faze-m2-nuke"

    def test_canonical_demo_rejects_unknown_and_non_str(self):
        eng = make_engine()
        assert eng._canonical_demo("evil'; DROP TABLE--") is None
        assert eng._canonical_demo(42) is None
        assert eng._canonical_demo(None) is None


class TestListMatches:
    def test_team_filter(self):
        eng = make_engine()
        out = eng._tool_list_matches("faze", "")
        assert "4 matches found" in out
        assert "navi" not in out

    def test_map_filter_whitelisted(self):
        eng = make_engine()
        out = eng._tool_list_matches("faze", "nuke")
        assert "spirit-vs-faze-m2-nuke" in out
        assert "mirage" not in out

    def test_bogus_map_ignored(self):
        eng = make_engine()
        out = eng._tool_list_matches("", "not_a_map'; --")
        assert "5 matches found" in out

    def test_no_results(self):
        eng = make_engine()
        assert "No matches found" in eng._tool_list_matches("astralis", "")


class TestExecuteTool:
    def test_unknown_tool(self):
        eng = make_engine()
        assert eng._execute_tool("drop_tables", {}).startswith("ERROR")

    def test_round_details_unknown_demo(self):
        eng = make_engine()
        out = eng._execute_tool("get_round_details", {"demo_name": "nope", "rounds": [1]})
        assert out.startswith("ERROR")
        assert "list_matches" in out

    def test_round_details_invalid_rounds(self):
        eng = make_engine()
        out = eng._execute_tool(
            "get_round_details",
            {"demo_name": "spirit-vs-faze-m2-nuke", "rounds": [99, "x"]},
        )
        assert out.startswith("ERROR")

    def test_lookup_player_requires_name(self):
        eng = make_engine()
        assert eng._execute_tool("lookup_player", {"name": ""}).startswith("ERROR")


class TestDemoCandidates:
    def test_multiple_candidates_sorted(self):
        eng = make_engine()
        got = eng._resolve_demo_candidates("what happened in faze vs spirit?")
        assert got == sorted(d for d in KNOWN if "faze" in d and "spirit" in d)

    def test_map_mention_narrows(self):
        eng = make_engine()
        got = eng._resolve_demo_candidates("faze vs spirit on nuke")
        assert got == ["spirit-vs-faze-m2-nuke"]

    def test_session_demo_fallback(self):
        eng = make_engine()
        eng._player_context = {"demo_name": "navi-vs-vitality-m1-inferno"}
        assert eng._resolve_demo_candidates("hello") == ["navi-vs-vitality-m1-inferno"]

    def test_resolve_demo_name_ambiguous_is_none(self):
        eng = make_engine()
        assert eng._resolve_demo_name("faze vs spirit") is None

    def test_disambiguation_block_lists_and_instructs(self):
        eng = make_engine()
        block = eng._disambiguation_block(["spirit-vs-faze-m1-mirage", "spirit-vs-faze-m2-nuke"])
        assert "spirit-vs-faze-m1-mirage" in block
        assert "spirit-vs-faze-m2-nuke" in block
        assert "Ask the user" in block


class TestMatchInventory:
    def test_inventory_block(self):
        eng = make_engine()
        inv = eng._get_match_inventory()
        assert "5 matches" in inv
        assert "4 with full round data" in inv
        assert "faze-vs-spirit-m2-mirage (24 rounds)" in inv
        assert "navi-vs-vitality-m1-inferno (stats only)" in inv

    def test_inventory_cached(self):
        eng = make_engine()
        first = eng._get_match_inventory()
        eng._known_demos = {}  # would change output if not cached
        assert eng._get_match_inventory() is first


class TestRespondViaTools:
    def test_tool_round_then_answer(self):
        llm = FakeToolLLM(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "list_matches",
                                "arguments": {"team": "faze"},
                            },
                        }
                    ],
                },
                {"content": "Here is the analysis.", "tool_calls": []},
            ]
        )
        eng = make_engine(llm)
        out = eng._respond_via_tools([{"role": "user", "content": "pick a match"}], "SYS")
        assert out == "Here is the analysis."
        # Second call must carry the executed tool result
        second_msgs = llm.calls[1]["messages"]
        tool_msgs = [m for m in second_msgs if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["tool_name"] == "list_matches"
        assert tool_msgs[0]["tool_call_id"] == "call_1"
        assert "matches found" in tool_msgs[0]["content"]

    def test_string_arguments_parsed_as_json(self):
        llm = FakeToolLLM(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "list_matches",
                                "arguments": '{"team": "spirit"}',
                            }
                        }
                    ],
                },
                {"content": "done", "tool_calls": []},
            ]
        )
        eng = make_engine(llm)
        assert eng._respond_via_tools([{"role": "user", "content": "q"}], "S") == "done"
        tool_msgs = [m for m in llm.calls[1]["messages"] if m.get("role") == "tool"]
        assert "4 matches found" in tool_msgs[0]["content"]

    def test_unsupported_model_short_circuits(self):
        llm = FakeToolLLM([], tools_supported=False)
        eng = make_engine(llm)
        assert eng._respond_via_tools([{"role": "user", "content": "q"}], "S") is None
        assert llm.calls == []

    def test_llm_error_marker_returns_none(self):
        llm = FakeToolLLM([{"content": "[LLM Connection Error] x", "tool_calls": []}])
        eng = make_engine(llm)
        assert eng._respond_via_tools([{"role": "user", "content": "q"}], "S") is None

    def test_direct_answer_no_tools(self):
        llm = FakeToolLLM([{"content": "Direct.", "tool_calls": []}])
        eng = make_engine(llm)
        assert eng._respond_via_tools([{"role": "user", "content": "q"}], "S") == "Direct."

    def test_cancellation_between_rounds(self):
        llm = FakeToolLLM([])
        eng = make_engine(llm)
        eng._stream_cancel.set()
        assert eng._respond_via_tools([{"role": "user", "content": "q"}], "S") == ""
        assert llm.calls == []
