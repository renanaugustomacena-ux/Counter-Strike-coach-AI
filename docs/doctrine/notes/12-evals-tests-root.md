# Cluster 12 — `evals/` + root `tests/` + `tests/forensics/`

Files read (28): evals/cs2_coach_bench/{run_eval, score_responses}; tests/{conftest,
setup_golden_data, test_coach_answer_eval, test_eval_harness, test_lock_files,
test_lock_release_ownership, test_single_instance_posix, test_sync_pro_players,
test_rescrape_placeholder_pros, test_d3_rederive, verify_chronovisor_logic,
verify_chronovisor_real, verify_csv_ingestion, verify_map_integration,
verify_reporting, verify_superposition}; tests/forensics/{check_db_status,
check_failed_tasks, debug_env, debug_nade_cols, debug_parser_fields,
probe_missing_tables, test_forensic_parser, test_skill_logic,
verify_map_dimensions, verify_spatial_integrity}.

## Purpose map

| Group | Role |
|---|---|
| `cs2_coach_bench` | 200-question CS2 coaching benchmark. Two backends: `coach` (full pipeline: RAG + Experience Bank + LLM via CoachingDialogueEngine) vs `ollama:<model>` (raw LLM, no retrieval) — **the A/B design isolates the RAG/experience contribution from raw model knowledge**. 5 categories (map_tactics, economy, mid_round, pro_knowledge, mechanics), latency tracked per question, JSONL reports. Scorer: 5-dimension human rubric, 0–3 each (tactical_correctness, cs2_currentness — "CS2 not CSGO-era", specificity, pro_grounding, actionability), per-category breakdown, two-report comparison. NOTE: the docstring advertises an "LLM-as-judge" mode but `--mode` choices only implement `manual` — docstring drift. |
| Lock-file suite | The strongest test cluster in the root tree. `test_lock_files`: acquire/release/dead-PID reclaim/live-PID conflict/context manager; **R4 HIGH TOCTOU** — old read→check→write acquire let concurrent contenders all win; O_CREAT\|O_EXCL now proven with a 16-thread contention test asserting exactly 1 winner; 26-WIN-02 never-allocated-PID liveness (WinError 87 crashed the probe); 26-WIN-01 SIGINT handler restored in teardown (leaked handler failed Windows CI after all tests passed); lock names with path separators sanitized (no `.locks` escape). `test_lock_release_ownership` (F-0009): release() must NEVER unlink a FOREIGN live lock — "the docstring always claimed no-op but the body unlinked whatever existed", defeating D-track/HLTV mutual exclusion; own-PID orphan (crash recovery) still removable. `test_single_instance_posix` (F-0010): the POSIX single-instance guard used to return True unconditionally ("Windows-only deployments") — permitting concurrent SQLite writers on Linux. |
| `test_d3_rederive` | P2-10: the 2026-05-06 shard recovery wrote `v1-d3-recovered` rows with a **hardcoded tick_rate=64.0**. Re-derive mode must fix from .dem headers when the file exists and re-mark rows with an honest default-rate sentinel when it doesn't — "**never silently bless a fabricated rate as header-derived**". Dry-run classifies without writing; per-shard backups; sentinel rows upgrade when the .dem reappears. |
| GAP-0x tool tests | Root-tree tests for tools (in-memory SQLite patched into the manager — real logic, no production DB): GAP-04 eval_harness (brier score props; dry-run report statuses honest: llm_baseline=NOT_IMPLEMENTED, win_prob_calibration=NOT_AVAILABLE); GAP-05 sync_pro_players (dry-run default, mutation only under --apply, idempotent); GAP-06 rescrape_placeholder_pros (CHAT-06 remediation: dry-run lists without instantiating the fetcher, preflight abort rc=2, per-player fetch, **post-rescrape `_still_default` verification** — a "successful" scrape that leaves the sentinel row still fails rc=1); GAP-15 coach_answer_eval (Unicode-typography normalization, token-coverage fact matching for paraphrased demo names, all/any/cluster check modes). |
| `verify_*` scripts | Standalone runtime verifiers (venv-guarded, exit 2 outside venv): superposition (FiLM context sensitivity — same input, two contexts, outputs MUST differ; full RAPCoachModel forward with named output-head checks), map integration (25-dim layout spot-checked BY INDEX — health@0, view sin/cos@12/13 — a live copy of the P-X-01 contract), reporting (real ticks from a real shard → heatmap), csv ingestion (Ext_ tables populated). |
| Chronovisor twins | `verify_chronovisor_logic`: synthetic signals (clean spike ⇒ "play" severity 0.3, drop ⇒ "mistake", 7σ noise floor ⇒ zero false positives, NMS clustering) with an explicit docstring defending synthetic data for algorithm unit tests — "does NOT represent 'mock data' in the production system". `verify_chronovisor_real`: the twin that "forbids the use of synthetic or mock data" — real shard ticks, honest about feeding a normalized equipment-value stream as a pipeline smoke (0 moments is a valid outcome). **The no-mock doctrine's boundary is drawn in these two files**: synthetic inputs are legitimate for pure signal-processing math; anything touching the product pipeline must use real data or skip. |
| forensics/ | Standalone diagnostics with a consistent discipline: import guard (raise ImportError if imported — pytest can't accidentally collect them), venv guard, path stabilization, bounded queries (TQ-F02-01 limit 500 on failure backlogs). test_forensic_parser renamed from `forensic_parser_test.py` (never matched pytest collection!) and re-pointed at the DP-06 demo SSOT ("the old path never existed"). test_skill_logic: beginner ⇒ level ≤3, pro ⇒ ≥8, one-hot skill tensor; docstrings encode the R4 "0.0-is-real" raw component scale contract. debug_env still probes **Kivy** — stale from the pre-Qt era. |
| `setup_golden_data` | Builds `tests/golden_data/golden.db` from a real golden.dem: full tick-field list with a core-field fallback, 12 event tables, header metadata — the fixture-generation path for parser-dependent tests. |

## Invariants observed (doctrine candidates)

- **Comparative evaluation is designed to attribute gains**: coach-vs-raw-LLM A/B isolates what retrieval adds; scored on a fixed rubric with a currentness dimension (CS2-not-CSGO) that guards against stale-era knowledge.
- **The synthetic-data boundary is explicit**: pure-math signal tests may generate inputs (and say so); pipeline tests must use real data or skip. Both sides of the boundary are written down in the files themselves.
- **Repairs must not launder fabricated values**: the d3 re-derive contract (header-derived vs default-rate sentinel, upgradeable when evidence appears) is the anti-fabrication rule applied to *metadata repair itself*.
- **Remediation tools verify their own effect**: rescrape returns failure if the placeholder sentinel survives a "successful" scrape — success is measured on the data, not the action.
- **Mutual exclusion is tested adversarially**: contention (16 threads, exactly 1 winner), foreign-lock protection, dead-PID reclaim, hostile lock names, cross-platform liveness — the lock layer earns its trust.
- Standalone scripts defend against wrong invocation modes (import guards, venv guards) so the test suite's collection surface stays intentional.

## Risks / open questions carried forward

- score_responses docstring/implementation drift (judge mode advertised, only manual implemented) — small but it's the doctrine's "comments must tell the truth" class.
- `debug_env.py` probes Kivy — dead relic of the pre-Qt UI; candidate for the replace-not-delete sweep.
- eval reports live under `evals/cs2_coach_bench/reports/` — no retention/, gitignore status not verified here.
- llm_baseline eval section is NOT_IMPLEMENTED (honest status) — the doctrine roadmap should decide whether the 200-question bench replaces it or feeds it.

---

**PHASE 1 COMPLETE**: every entry in READING-MANIFEST.md is now ticked (clusters 01–15).
