"""CLI wrapper — the exporter lives in the package (WP4b).

The implementation moved to ``Programma_CS2_RENAN/backend/storage/episode_export.py``
so the in-app Train action can call it (the frozen build ships no ``tools/``).
This file keeps the historical command line::

    PYTHONPATH=. .venv/bin/python tools/export_episodes.py \\
        --out DIR [--profile full|medium|sample] [--db PATH] [--seed 0] \\
        [--demos N] [--workers K] [--full]
"""

from __future__ import annotations

from Programma_CS2_RENAN.backend.storage.episode_export import (  # noqa: F401
    CHRONOLOGICAL_SOURCES,
    EXPORT_VERSION,
    GAP_TOLERANCE,
    MIN_EPISODE_TICKS,
    PTS_COLS,
    ROUNDSTATS_LABEL_COLS,
    ExportSummary,
    _apply_profile,
    _bridge_episode,
    _build_episode_labels,
    _compute_actions,
    _cut_at_death,
    _dedupe,
    _determine_split,
    _drop_warmup,
    _git_sha,
    _normalize_demo_name,
    _normalize_player_name,
    _process_demo,
    _split_episodes,
    _wrap_delta_yaw,
    _write_manifest,
    _write_shard,
    export_episodes,
    main,
    open_ro,
    run_export,
)

if __name__ == "__main__":
    main()
