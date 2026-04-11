import os
import sys

import pytest

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager
from Programma_CS2_RENAN.backend.storage.database import init_database


def run_training_cycle():
    manager = CoachTrainingManager()
    manager.run_full_cycle()


@pytest.mark.integration
def test_e2e_user_journey(isolated_settings):
    """
    End-to-End Test (E2E): Simulate full lifecycle using real DB data.
    1. Initialize System
    2. Configure User (writes to temp file via isolated_settings fixture)
    3. Verify sufficient real data exists (skip-gate)
    4. Run ML Training
    """
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
    from Programma_CS2_RENAN.core.config import save_user_setting

    # 1. Init
    init_database()

    # 2. Config — writes to temp file, never touches real user_settings.json
    save_user_setting("CS2_PLAYER_NAME", "E2E_Test_Player")

    # 3. Verify sufficient real data exists (skip-gate — no synthetic seeding)
    db = get_db_manager()
    with db.get_session() as session:
        real_stats = session.exec(select(PlayerMatchStats).limit(10)).all()
    if len(real_stats) < 5:
        pytest.skip(
            f"Not enough real data for E2E test (found {len(real_stats)}, need 5+). "
            "Run ingestion first to populate the database."
        )

    # 4. Run Training Cycle with real data
    try:
        run_training_cycle()
    except Exception as e:
        pytest.fail(f"E2E Lifecycle Failed during Training: {e}")

    # 5. Verify training produced observable effects
    from Programma_CS2_RENAN.backend.storage.db_models import CoachState
    from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

    sm = get_state_manager()
    state = sm.get_coach_state()
    # Coach state must exist and reflect a completed or active training
    assert state is not None, "CoachState missing after training cycle"
    assert state.status is not None, "CoachState.status is None after training"

    # At least one epoch must have run (current_epoch >= 1 or total_loss set)
    if hasattr(state, "current_epoch") and state.current_epoch is not None:
        assert state.current_epoch >= 1, f"Expected at least 1 epoch, got {state.current_epoch}"
