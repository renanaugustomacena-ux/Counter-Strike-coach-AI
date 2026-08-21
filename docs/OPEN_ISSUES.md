# Open Issues — consolidated register (updated 2026-08-21, post-sweep)

> Product of the 2026-08-21 docs sanitation + the same-day fix sweep
> (branch `fix/open-issues-sweep`). **TASKS.md remains the single source of
> truth for the actionable backlog** — entries here either point at a TASKS
> row or are doc-only findings. When an item lands, delete its row here.

## 1. CLOSED by the 2026-08-21 sweep

| ID | What closed |
|---|---|
| OI-1 | data_quality per-item completeness enumeration (was: one bad shard → "0 matches" in a green report) |
| OI-2 | match_date provenance: resolver ladder + `match_date_source` column (alembic `a7b8c9d0e1f2`) + ingestion wiring + split warning + backfill tool |
| OI-7 | thin-baseline floor: 10 → `MIN_DEMO_BASELINE_ROWS = 30` |
| OI-8 | demo/archive root never `$HOME`; `DEMO_ARCHIVE_PATH` honored |
| F-0011 | single-handler logging, per-process log files via `CS2_LOG_ROLE` |
| F-0017 | heatmap C-03 single-flip + dead Kivy surface removed |
| F-0018 | baseline fusion layers emit empirical keys only (+ dead `.name` fallback fixed) |
| F-0019 | percent/ratio coherence: CSV loader normalization + sanity band + extended self-heal |
| F-0020 | elite CSV builder (`tools/build_elite_csvs.py`) + per-component EliteAnalytics degradation — **generation itself runs on the data box (§3)** |
| F-0021 | flash-bait detection keys on real blind signal (`is_blinded`), honest-dark otherwise |
| F-0023 | VL concept loss on temperature-scaled logits; τ now receives gradient |
| F-0024 | P9-02 embedding-collapse hard-stop wired into the production epoch loop (VL path emits variance too) |
| F-0025 | RAP side resolution via `core/team_codes.normalize_team` (shard 'TERRORIST' handled; T roles reachable) |
| F-0026 | train/serve tensor-resolution parity (64² at both inference sites; resolutions in sidecar) |
| F-0028 | hybrid engine dead ML inference removed (honest RAG+Z docs) |
| F-0029 | insight adapter refuses pretrain-only checkpoints (`head_trained` sidecar gate) |
| F-0031 | utility analysis derives throw counts from RoundStats |
| #28.2/.3/.4 | broad-except queue closed (see TASKS #28 rows for dispositions) |
| #47 (hazard) | HLTV schema reconciliation made non-destructive (add-in-place / stale-preserve); formal alembic adoption stays G7 |
| #64 (mechanical) | wrong-shape fixtures repointed to the 10-dim head; adapter↔vectorizer axis contract pinned |
| TASKS drift | #38 and #65 rows aligned to their 2026-08-03 closures |

## 2. Still open — needs the Linux data box (run in the next data/training session)

| # | Item |
|---|---|
| D-1 | `alembic upgrade head` on the monolith (brings `a7b8c9d0e1f2` / match_date_source) |
| D-2 | `python tools/backfill_match_dates.py --apply` → then re-run split assignment (real chronology for the anti-leak split) |
| D-3 | `python tools/build_elite_csvs.py --apply` (regenerates the elite reference CSVs from hltv_metadata.db + monolith) |
| D-4 | **31 of 34 HLTV `.rar` archives** still to extract and ingest (67 GB on the USB volume) |
| D-5 | **6 part-demos** (`-p1`/`-p2`) ingested as separate matches — merging each pair would recover real training data |
| D-6 | **47 historical demos** with `data_quality='full_sql_round_count_anomaly'` (461 rows) — round-numbering audit; all UNASSIGNED |
| D-7 | **Monolith on USB SATA** — training is I/O-bound; moving `database.db` (~254 GB) to NVMe (~271 GB free needed) is the next real performance win |
| D-8 | 2026-08-03 Linux machine config: set `PRO_DEMO_PATH` + complete the first-run wizard |

## 3. Still open — owner-gated / post-retrain (unchanged sequencing)

- **R8** retrain ladder (owner launches; see `jepa_training_tuning_observations_2026-05-06.md`)
- **R9** post-retrain: #58 residual (F1.5 A/B bench, concept head), #64 target-semantics design (the only #64 residue), transformers 5.x bump + RAG re-embedding, Phase-6 `game_states` wiring decision (strategy/win-prob/economy modules still have no producer)
- **R10** trilingual docs (incl. stale `docs/README_IT.md` / `README_PT.md` index generation)
- **#67** tool/test layout consolidation (R10 window) · **#44/#45** deferred by design · **G7** hltv alembic adoption
- **R11** final training · **R12** git-history rewrite (owner force-push)

## 4. Environment known-issues

Machine-specific known issues (Linux venv stale shebangs / G9 venv recreation,
cross-OS pre-commit hook rule, NTFS3 volume history) stay documented in
[DIAGNOSIS_2026-05.md](DIAGNOSIS_2026-05.md) §4 — per-box state, not repo work items.
