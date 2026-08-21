# Open Issues — consolidated from the docs sweep (2026-08-21)

> Product of the 2026-08-21 docs sanitation: every issue still open in the old
> diagnosis/handoff/audit documents, gathered in one place. **TASKS.md remains the
> single source of truth for the actionable backlog** — entries here either point at
> a TASKS row or are doc-only findings that never got one. When an item lands,
> delete its row here (and close the TASKS row if one exists).

---

## 1. Code-verified open defects (no TASKS row — verified still present 2026-08-21)

| # | Where | Issue |
|---|---|---|
| OI-1 | `Programma_CS2_RENAN/backend/nn/data_quality.py:116-130` | Match-completeness enumeration sits in ONE `try` around the whole loop with `except Exception: logger.debug(...)` — the first failing shard aborts the loop at iteration 0, the report prints `Complete matches: 0, Incomplete: 0` (false) and still says PASS. Informational only (the training gate uses a different path), but it is a wrong number in a green report. Fix: per-item try + raise log level to `warning`. This is the 4th instance of the pattern fixed elsewhere in the 2026-07 campaigns (SESSION_HANDOFF 2026-07-26 item 3). |
| OI-2 | `Programma_CS2_RENAN/backend/storage/db_models.py:66` | `PlayerMatchStats.match_date` is `default_factory=datetime.now(utc)` — an **ingestion timestamp, not the match date**. The "chronological anti-leak" split therefore orders by ingestion order. `matchresult.date` is also an ingestion timestamp and `hltv_metadata.db` carries no per-demo dates. Needs a true source (HLTV event metadata or demo header) (SESSION_HANDOFF 2026-07-26 item 4). |

## 2. Deferred audit findings (Nuke-Proof Audit, closed 2026-08-14)

The campaign resolved 44/44 findings: 31 fixed, **13 deferred with written reasons**.
Full evidence and proposed fixes live in [audit/FINDINGS.md](audit/FINDINGS.md) — these
rows are the still-open remainder.

| ID | Area | One-liner | Blocked on |
|---|---|---|---|
| F-0011 | observability | N per-logger `RotatingFileHandler`s + 2 processes share one rotating log file — rotation races / interleaving | Multiprocess logging redesign (single-writer usage today) |
| F-0017 | processing/heatmap | Heatmap grid double-flips Y (Kivy residue) — latent vertical mirror for any Qt/matplotlib consumer | Visual ground truth against a known heatmap before flipping the flip |
| F-0018 | baselines | Fusion layer-priority inversion — hard defaults from layers 2/3 clobber earlier empirical layers | Elite-baseline family review together with F-0020 |
| F-0019 | baselines/validation | CSV layer ingests KAST/HS% as percent into a ratio-scaled baseline; sanity band is percent-scaled | CSV layer inactive until F-0020 files exist |
| F-0020 | data assets | All 7 EliteAnalytics reference CSVs + pro-baseline CSV absent — elite-comparison degraded on fresh installs | Data acquisition + CP0 decision (ship / optional download / retire feature) |
| F-0021 | analysis/deception | Flash-bait detection keyed to dead CS2 event `player_blind` — bait rate degenerates to 1.0 or 0.0 | demoparser2 event-vocabulary research on live demos |
| F-0023 | nn/vl-jepa | Concept training BCE on raw cosine sims can't fit its labels; inference readout is a different function | CP0 #5 research track (guarded) |
| F-0024 | nn/orchestrator | P9-02 embedding-collapse hard-stop bypassed on the production training path (detector never fed) | CP0 #5 research track (guarded) |
| F-0025 | nn/rap-training | RAP value/strategy labels resolve `team` from an attribute monolith rows don't have → every sample treated as CT | CP0 #5 research track (guarded) |
| F-0026 | nn/rap-inference | Train/inference tensor-resolution skew — training at 64², both inference paths at default 128/224 | CP0 #5 research track (guarded) |
| F-0028 | coaching/hybrid | Hybrid engine computes ML predictions then discards them — synthesis is RAG + baseline-Z only | Design decision: wire predictions in or rename honestly (F1 adapter may supersede) |
| F-0029 | coaching/jepa-adapter | Adapter arms on pretrain-only checkpoints whose coaching head is untrained → noise becomes insights when `USE_JEPA_MODEL` on | CP0 #5; also gated by TASKS#64 (finetune contract) |
| F-0031 | services/phase-6 | Utility/strategy/economy Phase-6 modules dark — analyzer requires stat keys no producer emits | Feature wiring (map `*_per_round` columns or re-key analyzer) |

## 3. Data & ops backlog (from SESSION_HANDOFF, last verified 2026-07-26 → 2026-08-03)

State-of-disk items from the Linux data box; not verifiable from other machines, believed open.

| # | Item |
|---|---|
| OI-3 | **31 of 34 HLTV `.rar` archives** still to extract and ingest (67 GB on the USB volume). |
| OI-4 | **6 part-demos** (`-p1`/`-p2` fragments) still ingested as separate matches — the split gate keeps them out, but merging each pair into one map would recover real training data. |
| OI-5 | **47 historical demos** with `data_quality='full_sql_round_count_anomaly'` (461 rows, ingested 2026-05-08) need a round-numbering audit. All UNASSIGNED — they don't touch training today. |
| OI-6 | **Monolith `database.db` (~254 GB) lives on a USB SATA volume** — training is I/O-bound (GPU 3-6%). Moving it to NVMe (~271 GB free needed) is the next real performance win. |
| OI-7 | **Thin-baseline threshold**: the demo layer of `pro_baseline` activates at exactly 10 rows (1 match) → tiny stds, inflated z-scores on local installs. Consider a higher MIN. |
| OI-8 | **Demo archive directory defaults to the user home** (`~/ingested/`) — reconsider the location. |
| OI-9 | **2026-08-03 Linux machine config**: `PRO_DEMO_PATH` unset (falls back to `~`); first-run wizard never completed there (`SETUP_COMPLETED` absent). Set both via the settings screen / wizard on next use. |

## 4. Already tracked in TASKS.md (pointers only — no content duplicated)

- **#28.2 / #28.3 / #28.4** — broad-except narrowing (session_engine, demo_parser, lifecycle).
- **#44** (GAP-11 sub-tick movement) · **#45** (GAP-12 pause/resume + team_switch) — deferred by design.
- **#47** (GAP-14) — bring `hltv_metadata.db` under alembic (Phase G7).
- **#58** (26-HYB-01/F1) — WIP; residual: F1.5 A/B bench post-retrain + concept head (needs VL-JEPA checkpoint).
- **#64** (26-RANGE-01) — finetune CLI is shape-broken (10-dim head vs [N,25] target); target contract decision is a pre-requisite for R9.
- **#67** — tool/test layout consolidation (R10 window, not before R8).
- **Roadmap blocks**: R8 retrain ladder (owner-gated, see `jepa_training_tuning_observations_2026-05-06.md` §Retrain ladder) → R9 post-retrain (incl. transformers 5.x bump + re-embedding) → R10 trilingual docs → R11 final training → R12 git-history rewrite (owner-gated).

## 5. Environment known-issues

Machine-specific known issues (Linux venv stale shebangs / G9 venv recreation, cross-OS
pre-commit hook rule, NTFS3 volume history) stay documented in
[DIAGNOSIS_2026-05.md](DIAGNOSIS_2026-05.md) §4 — they are per-box state, not repo work items.
