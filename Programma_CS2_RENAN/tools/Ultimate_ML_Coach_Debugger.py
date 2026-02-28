"""
Ultimate ML Coach Debugger
===========================
F8-28: Neural belief state and decision logic falsification tool.
Checks fidelity thresholds, stability probes, and insight traceability
against real database records.
"""

import sys

from _infra import path_stabilize

path_stabilize()

import torch
from sqlmodel import func, select

from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
from Programma_CS2_RENAN.backend.processing.state_reconstructor import RAPStateReconstructor
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import (
    CoachingInsight,
    PlayerMatchStats,
    PlayerTickState,
)

# F8-20: Variance threshold for neural belief stability. 0.5 is a heuristic upper bound
# based on expected normalized output magnitude. Adjust if model architecture changes.
_BELIEF_STABILITY_VARIANCE_THRESHOLD = 0.5


class UltimateMLDebugger:
    """
    Ultimate ML Coach Debugger (MCIV Clinical Module).
    Falsifies Neural Belief States and Decision Logic.
    """

    def __init__(self):
        self.db = get_db_manager()
        self.recon = RAPStateReconstructor()
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        self.model = ModelFactory.get_model("default", input_dim=METADATA_DIM, output_dim=4)
        self.report = []

    def run_diagnostic_cycle(self, player_name="MCIV_PROBE"):
        print("\n" + "█" * 60 + "\n MACENA ULTIMATE ML COACH DEBUGGER v1.0\n" + "█" * 60)
        self._audit_data_fidelity(player_name)
        self._audit_belief_stability(player_name)
        self._audit_decision_logic(player_name)
        return self._generate_clinical_summary()

    def _audit_data_fidelity(self, player_name):
        print("[1/3] Probing Knowledge Base Fidelity...")
        with self.db.get_session() as s:
            ticks = s.exec(
                select(func.count(PlayerTickState.id)).where(
                    PlayerTickState.player_name == player_name
                )
            ).one()
            matches = s.exec(
                select(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.player_name == player_name
                )
            ).one()

        self._check_fidelity_thresholds(ticks, matches)  # F8-09: proper instance method call

    def _audit_belief_stability(self, player_name):
        print("[2/3] Probing Neural Belief State Stability...")
        with self.db.get_session() as s:
            match_data = s.exec(
                select(PlayerTickState).where(PlayerTickState.player_name == player_name).limit(100)
            ).all()

        if not match_data:
            return self.report.append(("Belief_Stability", "FAIL", "No sequential data"))

        self._execute_stability_probe(match_data)  # F8-09: proper instance method call

    def _audit_decision_logic(self, player_name):
        print("[3/3] Probing Decision Quality Delta (DQD)...")
        with self.db.get_session() as s:
            insights = s.exec(
                select(CoachingInsight).where(CoachingInsight.player_name == player_name)
            ).all()

        self._verify_insight_traceability(insights)  # F8-09: proper instance method call

    def _generate_clinical_summary(self):
        print("\n" + "=" * 60 + "\nCLINICAL DIAGNOSTIC REPORT\n" + "=" * 60)
        for test, status, detail in self.report:
            color = "\033[92m" if status == "PASS" else "\033[91m"
            print(f" {test:<30}: {color}{status}\033[0m | {detail}")

        all_pass = all(r[1] in ("PASS", "WARN") for r in self.report)
        print("\n" + ("BRAIN STATE: HEALTHY" if all_pass else "BRAIN STATE: PATHOLOGICAL") + "\n")
        return 0 if all_pass else 1

    # F8-09: Converted from module-level functions to proper instance methods
    def _check_fidelity_thresholds(self, ticks, matches):
        status = "PASS" if ticks > 0 and matches > 0 else "FAIL"
        detail = f"Ticks: {ticks}, Matches: {matches}"
        self.report.append(("KB_Fidelity", status, detail))

    def _execute_stability_probe(self, data):
        try:
            tensors = self.recon.reconstruct_belief_tensors(data)
            out = self.model(tensors["metadata"])
            variance = torch.var(out).item()
            status = "PASS" if variance < _BELIEF_STABILITY_VARIANCE_THRESHOLD else "FAIL"
            self.report.append(("Neural_Stability", status, f"Var: {variance:.6f}"))
        except Exception as e:
            self.report.append(("Neural_Stability", "FAIL", str(e)))

    def _verify_insight_traceability(self, insights):
        if not insights:
            return self.report.append(("DQD_Traceability", "WARN", "No insights generated yet"))

        # Verify each insight has a traceable demo_name link
        traceable = 0
        for ins in insights:
            if hasattr(ins, "demo_name") and ins.demo_name:
                traceable += 1

        ratio = traceable / len(insights) if insights else 0
        status = "PASS" if ratio >= 0.8 else "FAIL"
        self.report.append(
            (
                "DQD_Traceability",
                status,
                f"Audited {len(insights)} insights, {traceable} traceable ({ratio:.0%})",
            )
        )


if __name__ == "__main__":
    exit_code = UltimateMLDebugger().run_diagnostic_cycle()
    sys.exit(exit_code)
