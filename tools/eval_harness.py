"""GAP-04 · Eval harness — offline measurement for the CS2 Coach pipeline.

Purpose
-------
Before every retrain we need an evidence-first baseline. This harness collects
what we can measure today and writes a deterministic, append-only JSON report
under `reports/`. Each run is timestamped; no overwrite, no silent mutation.

Metrics (graceful degradation — every section is independent)
------------------------------------------------------------
1. FEATURE DRIFT    — `TickFeatureDriftMonitor` fit on reference vectors drawn
                      from the chosen demo's first 20% of ticks, compared to
                      the remainder. Per-dimension z-score drift report.
2. RAG RECALL@K     — For K random coachingexperience rows with non-null
                      embeddings, nearest-neighbour search across the full
                      embedding matrix must return the query row in top-k.
                      Reports recall@{1,5,10} + vector index health signal.
3. KNN PURITY       — Same embeddings, report the share of neighbours that
                      share the query row's `outcome` label (k=5). This is
                      the embedding-quality signal the training loop lacks.
4. BRIER + CALIB    — Stub that runs when `--win-prob-head` points to a
                      trained checkpoint. Until then records NOT_AVAILABLE.
5. LLM BASELINE     — Stub: emits NOT_IMPLEMENTED. Plan GAP-15 (external
                      A/B) owns the full implementation.

CLI
---
    ./.venv/bin/python tools/eval_harness.py \\
        --demo astralis-vs-furia-m1-overpass \\
        --baseline

    --demo          Demo stem (no .dem). Used to scope the drift sample.
    --baseline      Mark this report as the pre-retrain baseline (metadata only).
    --k             Override default recall@k list (default 1,5,10).
    --report-dir    Override output directory (default: repo_root/reports/).
    --dry-run       Build the report dict, print to stdout, do NOT write file.

Exit codes
----------
    0  Report written (or dry-run OK).
    2  Unrecoverable failure BEFORE the report could be written (bad CLI,
       missing DB, etc). Partial/NOT_AVAILABLE sections are NOT a failure —
       the whole point is graceful degradation.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

# Repo root — script lives at tools/, project root is parent dir
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from Programma_CS2_RENAN.observability.logger_setup import get_logger  # noqa: E402

logger = get_logger("cs2analyzer.eval_harness")


# ---------------------------------------------------------------------------
# Section: Feature drift
# ---------------------------------------------------------------------------
def _feature_drift_from_demo(demo_stem: str) -> Dict[str, Any]:
    """Fit TickFeatureDriftMonitor on the first 20% of a demo's ticks and
    compare the remainder. Reports drifted feature dimensions or
    NOT_AVAILABLE if the demo hasn't been ingested into playertickstate yet.
    """
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
        FEATURE_NAMES,
        FeatureExtractor,
    )
    from Programma_CS2_RENAN.backend.processing.validation.drift import TickFeatureDriftMonitor
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerTickState

    db = get_db_manager()
    with db.get_session() as session:
        rows = list(
            session.exec(
                select(PlayerTickState)
                .where(PlayerTickState.demo_name == demo_stem)
                .order_by(PlayerTickState.tick)
                .limit(50_000)  # cap for responsiveness
            ).all()
        )

    if len(rows) < 500:
        return {
            "status": "NOT_AVAILABLE",
            "reason": f"demo '{demo_stem}' has {len(rows)} ticks in playertickstate — "
            "ingest first (need ≥500)",
            "ticks_found": len(rows),
        }

    extractor = FeatureExtractor()
    try:
        feats = np.vstack(
            [
                extractor.extract(_tick_row_to_dict(r), map_name=r.map_name or "de_unknown")
                for r in rows
            ]
        )
    except Exception as exc:
        return {"status": "ERROR", "reason": f"feature extraction failed: {exc}"}

    split = max(1, int(0.2 * len(feats)))
    ref = feats[:split]
    new = feats[split:]

    monitor = TickFeatureDriftMonitor(z_threshold=2.5)
    monitor.fit_reference(ref, feature_names=list(FEATURE_NAMES))
    report = monitor.check_drift(new)

    return {
        "status": "OK",
        "reference_ticks": int(len(ref)),
        "new_ticks": int(len(new)),
        "z_threshold": monitor.z_threshold,
        "is_drifted": bool(report.is_drifted),
        "drifted_features": list(report.drifted_features),
        "metadata_dim": int(feats.shape[1]),
    }


def _tick_row_to_dict(row) -> Dict[str, Any]:
    """Translate a PlayerTickState ORM row into the dict shape FeatureExtractor wants."""
    return {
        "health": row.health,
        "armor": row.armor,
        "has_helmet": row.has_helmet,
        "has_defuser": row.has_defuser,
        "equipment_value": row.equipment_value,
        "is_crouching": row.is_crouching,
        "is_scoped": row.is_scoped,
        "is_blinded": row.is_blinded,
        "enemies_visible": row.enemies_visible,
        "pos_x": row.pos_x,
        "pos_y": row.pos_y,
        "pos_z": row.pos_z,
        "view_x": row.view_x,
        "view_y": row.view_y,
        "time_in_round": row.time_in_round,
        "bomb_planted": row.bomb_planted,
        "teammates_alive": row.teammates_alive,
        "enemies_alive": row.enemies_alive,
        "team_economy": row.team_economy,
        "round_phase": "full_buy",  # not stored per-tick in schema — neutral default
    }


# ---------------------------------------------------------------------------
# Section: RAG recall@k + kNN purity
# ---------------------------------------------------------------------------
def _load_experience_embeddings(sample_size: int = 2000, seed: int = 42):
    """Sample up to N rows with non-null embeddings. Returns (ids, matrix, labels).

    Reuses ExperienceBank._deserialize_embedding so we handle BOTH the legacy
    JSON format AND the current base64(float32 bytes) format (AC-32-01).
    """
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceBank
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import CoachingExperience

    db = get_db_manager()
    ids: List[int] = []
    vecs: List[np.ndarray] = []
    labels: List[str] = []

    with db.get_session() as session:
        # GAP-09 compatibility: SELECT only the three columns we need so the
        # query stays compatible with DBs that haven't yet run the
        # strategy_label migration (or any future additive migration).
        stmt = select(
            CoachingExperience.id,
            CoachingExperience.embedding,
            CoachingExperience.outcome,
        ).where(CoachingExperience.embedding.is_not(None))
        rows = [
            type("Row", (), {"id": r[0], "embedding": r[1], "outcome": r[2]})()
            for r in session.exec(stmt).all()
        ]

    if not rows:
        return np.empty((0,), dtype=np.int64), np.empty((0, 0)), np.empty((0,), dtype=object)

    rng = random.Random(seed)
    rng.shuffle(rows)
    rows = rows[:sample_size]

    for r in rows:
        if not r.embedding:
            continue
        try:
            v = ExperienceBank._deserialize_embedding(r.embedding)
        except Exception:
            continue
        if v.ndim != 1 or v.size == 0:
            continue
        ids.append(r.id)
        vecs.append(v)
        labels.append(str(r.outcome or ""))

    if not vecs:
        return np.empty((0,), dtype=np.int64), np.empty((0, 0)), np.empty((0,), dtype=object)

    # All vectors must share the same dim — drop any that don't match the mode
    dim = max(set(v.size for v in vecs), key=[v.size for v in vecs].count)
    keep = [i for i, v in enumerate(vecs) if v.size == dim]
    if len(keep) < len(vecs):
        logger.warning(
            "Dropped %d embedding rows with dim != mode (%d)",
            len(vecs) - len(keep),
            dim,
        )

    matrix = np.vstack([vecs[i] for i in keep])
    return (
        np.asarray([ids[i] for i in keep], dtype=np.int64),
        matrix,
        np.asarray([labels[i] for i in keep], dtype=object),
    )


def _rag_and_purity(k_list: Sequence[int], sample_size: int = 2000) -> Dict[str, Any]:
    ids, matrix, labels = _load_experience_embeddings(sample_size)
    if matrix.size == 0:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "no coachingexperience rows with embeddings",
            "sample_size": 0,
        }

    # L2-normalize for cosine via dot product
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat_n = matrix / norms
    sims = mat_n @ mat_n.T  # [N, N]

    # Self-retrieval recall@k — query row should appear in its own top-k.
    # np.argsort descending → index [:, :k] is top-k including self at position 0.
    top_sorted = np.argsort(-sims, axis=1)
    n = matrix.shape[0]
    recall_by_k: Dict[int, float] = {}
    for k in k_list:
        k_capped = min(k, n)
        top_k = top_sorted[:, :k_capped]
        hits = sum(1 for i in range(n) if i in top_k[i])
        recall_by_k[int(k)] = hits / n

    # kNN purity — share of k-NN (excluding self) sharing query's outcome label
    purity_k = 5
    if n >= purity_k + 1:
        neighbours = top_sorted[:, 1 : purity_k + 1]  # drop self at index 0
        same_label = np.asarray([np.sum(labels[neighbours[i]] == labels[i]) for i in range(n)])
        purity = float(same_label.mean() / purity_k)
    else:
        purity = None

    return {
        "status": "OK",
        "sample_size": int(n),
        "embedding_dim": int(matrix.shape[1]),
        "recall_at_k": recall_by_k,
        "knn_purity_k5": purity,
        "distinct_outcome_labels": int(len(np.unique(labels))),
    }


# ---------------------------------------------------------------------------
# Section: Brier score stub (activated once a win-prob checkpoint ships)
# ---------------------------------------------------------------------------
def brier_score(y_true: np.ndarray, p_hat: np.ndarray) -> float:
    """Mean squared error between binary outcomes and predicted probabilities.

    Kept as a public helper so the eval harness + future trainer callbacks
    share a single source of truth. y_true ∈ {0, 1}; p_hat ∈ [0, 1].
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    p_hat = np.asarray(p_hat, dtype=np.float64)
    if y_true.shape != p_hat.shape:
        raise ValueError(f"shape mismatch: y_true={y_true.shape} p_hat={p_hat.shape}")
    return float(np.mean((p_hat - y_true) ** 2))


def expected_calibration_error(
    y_true: np.ndarray, p_hat: np.ndarray, n_bins: int = 10
) -> Dict[str, Any]:
    """Phase 7A: ECE with per-bin breakdown.

    Bins predictions into equal-width intervals and compares average predicted
    probability vs. actual positive rate per bin (Naeini et al. 2015).
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    p_hat = np.asarray(p_hat, dtype=np.float64).clip(0, 1)
    n = len(y_true)
    if n == 0:
        return {"ece": 0.0, "bins": [], "n_samples": 0}

    bin_edges = np.linspace(0, 1, n_bins + 1)
    bins_detail = []
    ece = 0.0
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (p_hat >= lo) & (p_hat < hi) if hi < 1.0 else (p_hat >= lo) & (p_hat <= hi)
        count = int(mask.sum())
        if count == 0:
            continue
        avg_pred = float(p_hat[mask].mean())
        avg_true = float(y_true[mask].mean())
        gap = abs(avg_pred - avg_true)
        ece += gap * count / n
        bins_detail.append(
            {
                "range": f"[{lo:.1f}, {hi:.1f})",
                "count": count,
                "avg_predicted": round(avg_pred, 4),
                "avg_actual": round(avg_true, 4),
                "gap": round(gap, 4),
            }
        )

    return {"ece": round(ece, 5), "bins": bins_detail, "n_samples": n}


def _win_prob_calibration(ckpt_version: Optional[str]) -> Dict[str, Any]:
    """Phase 7A: Win-prob calibration via ECE on RoundStats outcomes."""
    if not ckpt_version:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "no --win-prob-ckpt supplied; train + point at checkpoint to enable",
        }

    try:
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.analysis.win_probability import (
            GameState,
            WinProbabilityPredictor,
        )
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import RoundStats

        predictor = WinProbabilityPredictor(model_path=ckpt_version)
        if not predictor._checkpoint_loaded:
            return {"status": "ERROR", "reason": f"checkpoint {ckpt_version} failed to load"}

        db = get_db_manager()
        with db.get_session() as session:
            rounds = list(session.exec(select(RoundStats).limit(5000)).all())

        if len(rounds) < 50:
            return {
                "status": "NOT_AVAILABLE",
                "reason": f"only {len(rounds)} rounds in RoundStats (need ≥50)",
            }

        y_true, p_hat = [], []
        for r in rounds:
            gs = GameState(
                team_economy=r.team_economy or 0,
                enemy_economy=r.enemy_economy or 0,
                alive_players=r.teammates_alive or 5,
                enemy_alive=r.enemies_alive or 5,
                is_ct=(r.team_side == "CT") if hasattr(r, "team_side") else True,
            )
            prob, _ = predictor.predict(gs)
            p_hat.append(prob)
            y_true.append(1.0 if r.round_won else 0.0)

        ece_result = expected_calibration_error(np.array(y_true), np.array(p_hat))
        bs = brier_score(np.array(y_true), np.array(p_hat))
        return {
            "status": "OK",
            "ckpt_version": ckpt_version,
            "brier_score": round(bs, 5),
            **ece_result,
        }
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}


# ---------------------------------------------------------------------------
# Section: LLM A/B baseline (tracked in GAP-15, deferred)
# ---------------------------------------------------------------------------
def _llm_baseline_stub() -> Dict[str, Any]:
    return {
        "status": "NOT_IMPLEMENTED",
        "reason": "GAP-15: Gemma-4 / external LLM A/B scoring deferred",
    }


# ---------------------------------------------------------------------------
# Section: Embedding quality — silhouette score (Phase 7D)
# ---------------------------------------------------------------------------
def _embedding_quality(sample_size: int = 2000) -> Dict[str, Any]:
    """Phase 7D: Silhouette score + per-dim variance on coaching embeddings.

    Silhouette score ∈ [-1, 1]: measures cluster separation by outcome label.
    Per-dim std > 0.1 signals no embedding collapse (VICReg target).
    """
    ids, matrix, labels = _load_experience_embeddings(sample_size)
    if matrix.size == 0 or matrix.shape[0] < 10:
        return {
            "status": "NOT_AVAILABLE",
            "reason": f"need ≥10 embedding rows, got {matrix.shape[0] if matrix.size else 0}",
        }

    unique_labels = np.unique(labels)
    if len(unique_labels) < 2:
        return {
            "status": "NOT_AVAILABLE",
            "reason": f"need ≥2 distinct outcome labels, got {len(unique_labels)}",
        }

    per_dim_std = np.std(matrix, axis=0)
    collapsed_dims = int(np.sum(per_dim_std < 0.1))

    try:
        from sklearn.metrics import silhouette_score as sk_silhouette

        sil = float(sk_silhouette(matrix, labels, sample_size=min(500, matrix.shape[0])))
    except ImportError:
        n = matrix.shape[0]
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        mat_n = matrix / norms
        sims = mat_n @ mat_n.T
        a_scores = np.zeros(n)
        b_scores = np.full(n, np.inf)
        for lab in unique_labels:
            mask = labels == lab
            count = int(mask.sum())
            if count < 2:
                continue
            for i in np.where(mask)[0]:
                same = sims[i][mask]
                a_scores[i] = 1.0 - float(same.sum() - 1.0) / max(count - 1, 1)
                for other_lab in unique_labels:
                    if other_lab == lab:
                        continue
                    other_mask = labels == other_lab
                    if not other_mask.any():
                        continue
                    dist = 1.0 - float(sims[i][other_mask].mean())
                    b_scores[i] = min(b_scores[i], dist)
        valid = b_scores < np.inf
        if valid.sum() < 2:
            sil = 0.0
        else:
            s = (b_scores[valid] - a_scores[valid]) / np.maximum(a_scores[valid], b_scores[valid])
            sil = float(s.mean())

    return {
        "status": "OK",
        "sample_size": int(matrix.shape[0]),
        "embedding_dim": int(matrix.shape[1]),
        "silhouette_score": round(sil, 4),
        "per_dim_std_mean": round(float(per_dim_std.mean()), 4),
        "per_dim_std_min": round(float(per_dim_std.min()), 4),
        "collapsed_dims_count": collapsed_dims,
        "collapse_detected": collapsed_dims > matrix.shape[1] * 0.5,
        "distinct_labels": int(len(unique_labels)),
    }


# ---------------------------------------------------------------------------
# Section: Strategy relevance scoring (Phase 7B)
# ---------------------------------------------------------------------------
def _strategy_relevance() -> Dict[str, Any]:
    """Phase 7B: Measure strategy label coverage across maps and sides."""
    try:
        from sqlmodel import func, select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import CoachingExperience

        db = get_db_manager()
        with db.get_session() as session:
            total = session.exec(select(func.count()).select_from(CoachingExperience)).one()
            distinct_labels = session.exec(
                select(func.count(func.distinct(CoachingExperience.strategy_label))).where(
                    CoachingExperience.strategy_label.is_not(None)
                )
            ).one()
            distinct_maps = session.exec(
                select(func.count(func.distinct(CoachingExperience.map_name))).where(
                    CoachingExperience.map_name.is_not(None)
                )
            ).one()

            family_counts = {}
            rows = session.exec(
                select(CoachingExperience.strategy_label).where(
                    CoachingExperience.strategy_label.is_not(None)
                )
            ).all()
            for label in rows:
                family = label.split(".")[0] if "." in label else label
                family_counts[family] = family_counts.get(family, 0) + 1

        return {
            "status": "OK",
            "total_experiences": int(total),
            "distinct_strategy_labels": int(distinct_labels),
            "distinct_maps": int(distinct_maps),
            "label_target_200": int(distinct_labels) >= 200,
            "family_distribution": {
                k: v for k, v in sorted(family_counts.items(), key=lambda x: -x[1])[:10]
            },
        }
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}


# ---------------------------------------------------------------------------
# Section: MoE expert utilization (Phase 7C)
# ---------------------------------------------------------------------------
def _expert_utilization() -> Dict[str, Any]:
    """Phase 7C: Load JEPA model and measure MoE routing distribution on sample data."""
    try:
        import torch

        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
        from Programma_CS2_RENAN.backend.nn.persistence import load_nn

        model = ModelFactory.get_model("jepa")
        try:
            load_nn("jepa_brain", model)
        except Exception:
            return {
                "status": "NOT_AVAILABLE",
                "reason": "no jepa_brain checkpoint — train first",
            }

        model.eval()
        if not hasattr(model, "_expert_counts"):
            return {
                "status": "NOT_AVAILABLE",
                "reason": "model lacks _expert_counts (pre-Phase 3A)",
            }

        model._expert_counts.zero_()
        with torch.no_grad():
            for _ in range(20):
                dummy = torch.randn(8, 10, model.encoder[0].in_features)
                model(dummy)

        counts = model._expert_counts.cpu().numpy()
        total = float(counts.sum()) if counts.sum() > 0 else 1.0
        fracs = (counts / total).tolist()
        max_frac = max(fracs) if fracs else 0
        min_frac = min(fracs) if fracs else 0
        balanced = max_frac < 0.6 and min_frac > 0.1

        return {
            "status": "OK",
            "expert_fractions": [round(f, 4) for f in fracs],
            "balanced": balanced,
            "max_fraction": round(max_frac, 4),
            "min_fraction": round(min_frac, 4),
            "imbalance_ratio": round(max_frac / max(min_frac, 1e-6), 2),
        }
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ReportMeta:
    timestamp_utc: str
    demo: Optional[str]
    baseline: bool
    harness_version: str
    git_sha: Optional[str]


def _git_sha() -> Optional[str]:
    try:
        import subprocess

        out = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def run(
    demo: Optional[str],
    baseline: bool,
    k_list: Sequence[int],
    win_prob_ckpt: Optional[str],
    report_dir: Path,
    dry_run: bool,
) -> Path | None:
    meta = ReportMeta(
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        demo=demo,
        baseline=baseline,
        harness_version="2.0",
        git_sha=_git_sha(),
    )

    report: Dict[str, Any] = {
        "meta": {
            "timestamp_utc": meta.timestamp_utc,
            "demo": meta.demo,
            "baseline": meta.baseline,
            "harness_version": meta.harness_version,
            "git_sha": meta.git_sha,
        },
        "sections": {},
    }

    # --- Feature drift (demo-scoped) ---
    if demo:
        try:
            report["sections"]["feature_drift"] = _feature_drift_from_demo(demo)
        except Exception as exc:
            logger.exception("feature_drift section failed")
            report["sections"]["feature_drift"] = {"status": "ERROR", "reason": str(exc)}
    else:
        report["sections"]["feature_drift"] = {
            "status": "SKIPPED",
            "reason": "--demo not supplied",
        }

    # --- RAG + kNN purity ---
    try:
        report["sections"]["rag_and_purity"] = _rag_and_purity(k_list)
    except Exception as exc:
        logger.exception("rag_and_purity section failed")
        report["sections"]["rag_and_purity"] = {"status": "ERROR", "reason": str(exc)}

    # --- Brier calibration ---
    report["sections"]["win_prob_calibration"] = _win_prob_calibration(win_prob_ckpt)

    # --- LLM baseline ---
    report["sections"]["llm_baseline"] = _llm_baseline_stub()

    # --- Phase 7D: Embedding quality ---
    try:
        report["sections"]["embedding_quality"] = _embedding_quality()
    except Exception as exc:
        logger.exception("embedding_quality section failed")
        report["sections"]["embedding_quality"] = {"status": "ERROR", "reason": str(exc)}

    # --- Phase 7B: Strategy relevance ---
    try:
        report["sections"]["strategy_relevance"] = _strategy_relevance()
    except Exception as exc:
        logger.exception("strategy_relevance section failed")
        report["sections"]["strategy_relevance"] = {"status": "ERROR", "reason": str(exc)}

    # --- Phase 7C: Expert utilization ---
    try:
        report["sections"]["expert_utilization"] = _expert_utilization()
    except Exception as exc:
        logger.exception("expert_utilization section failed")
        report["sections"]["expert_utilization"] = {"status": "ERROR", "reason": str(exc)}

    if dry_run:
        print(json.dumps(report, indent=2, default=str))
        return None

    report_dir.mkdir(parents=True, exist_ok=True)
    fname = f"eval_{meta.timestamp_utc.replace(':', '').replace('-', '')}.json"
    out_path = report_dir / fname
    out_path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("Eval report written: %s", out_path)
    return out_path


def _parse_k_list(s: str) -> List[int]:
    return sorted({int(x.strip()) for x in s.split(",") if x.strip()})


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="GAP-04 eval harness")
    p.add_argument("--demo", type=str, default=None, help="demo stem (no .dem)")
    p.add_argument("--baseline", action="store_true", help="mark as pre-retrain baseline")
    p.add_argument("--k", type=_parse_k_list, default=[1, 5, 10], help="recall@k list, e.g. 1,5,10")
    p.add_argument(
        "--win-prob-ckpt", type=str, default=None, help="checkpoint version to calibrate"
    )
    p.add_argument(
        "--report-dir",
        type=Path,
        default=_REPO_ROOT / "reports",
        help="output directory",
    )
    p.add_argument("--dry-run", action="store_true", help="print JSON to stdout, do not write")
    args = p.parse_args(argv)

    try:
        run(
            demo=args.demo,
            baseline=args.baseline,
            k_list=args.k,
            win_prob_ckpt=args.win_prob_ckpt,
            report_dir=args.report_dir,
            dry_run=args.dry_run,
        )
    except Exception:
        logger.exception("eval harness aborted")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
