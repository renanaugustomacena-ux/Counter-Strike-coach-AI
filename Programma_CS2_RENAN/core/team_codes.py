"""Single authority for CS2 team-side normalization (F-0025 / F-0016 class).

Parsers and shards carry team sides in several vocabularies depending on
parser version and event type: full names ('TERRORIST', 'COUNTER-TERRORIST'),
short codes ('T', 'CT'), and demoparser2 int team_nums (2=T, 3=CT). Every
comparison site that tests ``== "CT"`` against a raw value silently
misclassifies the other vocabularies — round_won was always-False for
int-emitting demos (F-0016), and RAP training labeled every 'TERRORIST'
sample as CT (F-0025).

Use ``normalize_team()`` at every boundary; compare only its output.
"""

from typing import Optional

import pandas as pd

_CT_TOKENS = frozenset({"CT", "COUNTER-TERRORIST", "COUNTER_TERRORIST", "COUNTERTERRORIST", "3"})
_T_TOKENS = frozenset({"T", "TERRORIST", "TERRORISTS", "2"})


def normalize_team(raw) -> Optional[str]:
    """Normalize any known team-side shape to 'CT' / 'T'; unknown -> None."""
    if raw is None or (not isinstance(raw, str) and pd.isna(raw)):
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return {2: "T", 3: "CT"}.get(int(raw))
    token = str(raw).strip().upper()
    if token in _CT_TOKENS:
        return "CT"
    if token in _T_TOKENS:
        return "T"
    return None
