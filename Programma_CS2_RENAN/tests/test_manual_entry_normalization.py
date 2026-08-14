"""F-0042 regression: manual-entry normalizes percent-scale KAST/HS to the
ratio convention before writing is_pro=True rows (pro_baseline consumes
them unfiltered — a raw 71.0 poisons the baseline at ~100x)."""

import builtins
import sys
from contextlib import contextmanager
from pathlib import Path

# ptools use bare sibling imports (from _infra import ...) — mirror the
# script execution context.
_PTOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_PTOOLS) not in sys.path:
    sys.path.insert(0, str(_PTOOLS))
from unittest.mock import MagicMock, patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


def test_percent_inputs_are_normalized_to_ratio():
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
    from Programma_CS2_RENAN.tools import user_tools

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine, tables=[PlayerMatchStats.__table__])

    class _DB:
        @contextmanager
        def get_session(self, engine_key="default"):
            with Session(engine, expire_on_commit=False) as s:
                yield s

    answers = iter(["ZywOo", "1.27", "82.0", "78", "42", "1.3", "0.9", "0.31", "1.1", "q"])
    with patch.object(builtins, "input", side_effect=lambda *_: next(answers)):
        with patch(
            "Programma_CS2_RENAN.backend.storage.database.get_db_manager",
            return_value=_DB(),
        ):
            user_tools.cmd_manual_entry(MagicMock())

    with Session(engine) as s:
        row = s.exec(select(PlayerMatchStats)).first()
    assert row is not None
    assert row.avg_kast == 0.78, f"KAST stored {row.avg_kast}, expected ratio 0.78"
    assert row.avg_hs == 0.42, f"HS stored {row.avg_hs}, expected ratio 0.42"
    assert row.is_pro is True
