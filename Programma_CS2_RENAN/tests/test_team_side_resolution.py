"""F-0025 — RAP training resolves the REAL side, in every vocabulary.

PlayerTickState has no `team` column, so `getattr(item, "team", "CT")` was a
constant "CT": every T-side sample got CT-perspective advantage labels and
the T-side tactical roles were unreachable. Shards carry 'CT'/'TERRORIST';
knowledge.own_team holds the shard value.
"""

from types import SimpleNamespace

from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
from Programma_CS2_RENAN.core.team_codes import normalize_team


class TestNormalizeTeam:
    def test_vocabularies(self):
        assert normalize_team("CT") == "CT"
        assert normalize_team("TERRORIST") == "T"
        assert normalize_team("counter-terrorist") == "CT"
        assert normalize_team(2) == "T"
        assert normalize_team(3) == "CT"
        assert normalize_team("t") == "T"
        assert normalize_team("spectator") is None
        assert normalize_team(None) is None


def _player(team, health=100, equip=4000, alive=True):
    return SimpleNamespace(team=team, health=health, equipment_value=equip, is_alive=alive)


class TestSideResolution:
    def test_item_team_normalized(self):
        item = SimpleNamespace(team="TERRORIST")
        assert TrainingOrchestrator._resolve_item_side(item, None) == "T"

    def test_knowledge_own_team_fallback(self):
        item = SimpleNamespace()  # PlayerTickState-shaped: no team attribute
        knowledge = SimpleNamespace(own_team="TERRORIST")
        assert TrainingOrchestrator._resolve_item_side(item, knowledge) == "T"

    def test_documented_ct_last_resort(self):
        assert TrainingOrchestrator._resolve_item_side(SimpleNamespace(), None) == "CT"


class TestAdvantageWithShardVocabulary:
    def test_terrorist_sample_dominated_by_cts_is_disadvantaged(self):
        # 4 healthy CTs vs 1 TERRORIST — the T-side player must read < 0.5.
        players = [_player("CT") for _ in range(4)] + [_player("TERRORIST", health=40)]
        adv = TrainingOrchestrator._compute_advantage(players, "T", bomb_planted=False)
        assert adv < 0.5

    def test_ct_sample_same_state_is_advantaged(self):
        players = [_player("CT") for _ in range(4)] + [_player("TERRORIST", health=40)]
        adv = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=False)
        assert adv > 0.5


class TestTacticalRoleSides:
    def test_terrorist_entry_reaches_site_take(self):
        orch = TrainingOrchestrator.__new__(TrainingOrchestrator)
        item = SimpleNamespace(team="TERRORIST", equipment_value=5000, is_crouching=False)
        role = orch._classify_tactical_role(item, None, [])
        assert role == TrainingOrchestrator.ROLE_SITE_TAKE

    def test_ct_default_passive_hold(self):
        orch = TrainingOrchestrator.__new__(TrainingOrchestrator)
        item = SimpleNamespace(team="CT", equipment_value=5000, is_crouching=False)
        role = orch._classify_tactical_role(item, None, [])
        assert role == TrainingOrchestrator.ROLE_PASSIVE_HOLD
