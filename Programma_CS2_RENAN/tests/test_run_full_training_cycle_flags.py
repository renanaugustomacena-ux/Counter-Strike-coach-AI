"""D-36: the full-cycle entry point must expose the jepa_v2 budget flags.

``run_full_training_cycle.py --model-type jepa_v2`` dispatches to
``jepa_v2.cli.run_jepa_v2(args)``, which reads ``steps`` / ``probe_every`` /
``data_dir`` / ``no_resume`` from the namespace with ``getattr`` defaults.
The parser never declared them, so ``--epochs`` (and ``EPOCHS=`` in
train.sh) were silently ignored for v2 and no budget override was possible
from the documented entry point.
"""

from __future__ import annotations

import pytest

import run_full_training_cycle as rftc


@pytest.mark.parametrize(
    "argv, attr, expected",
    [
        (["--model-type", "jepa_v2", "--steps", "5"], "steps", 5),
        (["--model-type", "jepa_v2", "--probe-every", "2"], "probe_every", 2),
        (["--model-type", "jepa_v2", "--data-dir", "X"], "data_dir", "X"),
        (["--model-type", "jepa_v2", "--no-resume"], "no_resume", True),
    ],
)
def test_parser_exposes_jepa_v2_budget_flags(argv, attr, expected):
    args = rftc._build_parser().parse_args(argv)
    assert getattr(args, attr) == expected


def test_jepa_v2_flags_default_to_none_or_false():
    args = rftc._build_parser().parse_args(["--model-type", "jepa_v2"])
    assert args.steps is None
    assert args.probe_every is None
    assert args.data_dir is None
    assert args.no_resume is False
