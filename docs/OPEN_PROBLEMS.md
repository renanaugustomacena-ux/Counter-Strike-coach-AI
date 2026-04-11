# Open Problems — Read This First

> Last updated: 2026-04-11
> Read this at the start of every session. If we drift, come back here.

---

## The Vision

A **fully offline, privacy-first** CS2 coaching desktop app that beats cloud competitors (Leetify, Scope.gg, Refrag) through **game theory depth** no one else has: Bayesian death probability, expectiminimax action trees, Shannon entropy utility scoring, momentum/tilt detection, blind spot identification, economy optimization, engagement range profiling, deception indexing — 9 engines that already work today.

**What makes this different:** YOUR replays, YOUR habits, analyzed locally, compared against pro baselines. One-time purchase, no subscription, no cloud upload. Ghost player overlay (v1.0) shows AI-predicted "where you should stand."

### Product Roadmap

| Version | Milestone | Key Deliverables |
|---------|-----------|-----------------|
| **v0.1** | Early Access | Ship game theory + COPER coaching, CPU-only installer, itch.io ($15-20) |
| v0.2 | Quality | Error toasts, settings polish, 50% test coverage |
| v0.3 | ML Alpha | JEPA fine-tuned (50+ epochs), ghost player prototype |
| v0.5 | RAP Beta | RAP reactivated (if 5 criteria met), VL-JEPA concept explanations |
| v1.0 | Full Release | Full coaching pipeline, ghost player overlay, Linux+Steam |
| v2.0+ | Future | Live game overlay, cloud sync, team analytics, mobile |

---

## Where We Are Now

**Phase:** Teaching the Coach (pro data only, no user demos, no active coaching)
**Demos:** 97 .dem files on USB SSD, 564 per-match DBs, ~68 aggregated into production tables. Re-aggregation script ready.
**Models:** JEPA unblocked but **zero training epochs** run. RAP disabled. LLM = Llama 3.1 8B via Ollama (no fine-tuning).
**Coach Book:** v3 shipped (151 entries). Target is 1500.
**Hardware:** AMD Ryzen 9 9950X + RX 9070 XT (16GB VRAM) with ROCm 7.2. PyTorch 2.9.1+rocm6.3 GPU working. Local 8B LoRA fine-tuning is now feasible.
**Environment:** Python 3.12, venv at `~/.venvs/cs2analyzer/`, FlareSolverr running, 308/313 validator checks pass (5 warnings: kivy/kivymd optional, shap optional, ncps/hflayers optional for RAP).

---

## Resolved Since Last Session (2026-04-09 → 2026-04-11)

The following bugs from the previous OPEN_PROBLEMS were verified as **already fixed**:

| ID | Fix Summary |
|----|-------------|
| WR-31 | `restore_backup()` now deletes WAL/SHM before restoring (STOR-01) |
| WR-40 | Bomb state tracked via pointer-based forward scan in demo_loader |
| WR-44 | `time_in_round` clips at 115 (not 175), test added |
| WR-45 | `raise None` replaced with proper ConnectionError |
| WR-51 | `context_len` → `_JEPA_CONTEXT_LEN` (local constant) |
| WR-52 | `torch.tanh()` → `torch.sigmoid()` for [0,1] targets |
| WR-53 | Zero-padding replaced with repeat-last-tick strategy |
| WR-63 | `output_dim` uses `OUTPUT_DIM` (10) not `METADATA_DIM` (25) |
| WR-64 | `_validate_input_dim` handles both 2D and 3D input |
| WR-71 | `_log_dir` → `PROJECT_ROOT / "logs"` |
| ROOT-02 | `"complete"` → `"completed"` typo fixed |
| SVC-01 | Dialogue context correctly appends both user/assistant messages |
| SVC-02 | G-08 fallback to traditional coaching on empty corrections |
| SVC-04 | `belief_estimator` wired into `analysis_orchestrator` |
| PROC-01 | entity_id=-1 handled via position-based matching (R4-06-02) |
| PROC-04 | `recent_avg_raw is not None` explicit check (not `or`) |
| KNW-01 | WR-60 temporal filtering on feedback matching |
| STOR-02 | `close_all()` acquires `_engine_lock` |
| CTRL-01 | `get_hltv_db_manager().create_db_and_tables()` in db_governor |
| CORE-01 | `refresh_settings()` updates all globals including ACTIVE_THEME etc. |
| NN-04b | `set_total_steps()` properly computes from epochs * batches |
| NN-05b | `CoachNNConfig.output_dim` defaults to `OUTPUT_DIM` |
| DS-03 | Rate limit sleep capped at `min(..., 300)` |
| DS-04 | Path traversal sanitized via `os.path.basename` + comparison |
| JT-01 | Raw `sqlite3.connect()` removed from jepa_train.py |
| JT-03 | `assert _MIN_TICKS_FOR_SEQUENCE >= context_len + target_len` |
| JT-04 | `torch.save` uses atomic tmpfile + `os.replace` |
| JT-05 | Same as WR-52 (sigmoid) |
| JT-06 | Same as WR-53 (repeat-last-tick) |

| WR-79 | "Knowledge_mc" name leak sanitized in coaching prompt | `b9d4acf` |
| WR-80 | False NN attribution removed from coaching system prompt | `b9d4acf` |

Also fixed this session:
- 5 tools with hardcoded `/media/renan/` paths → updated to USB SSD path
- `user_settings.json` PRO_DEMO_PATH and DEFAULT_DEMO_PATH set
- `match_data` symlink → 564 per-match databases now accessible
- `launch.sh` Python version check relaxed to >=3.10
- `.pre-commit-config.yaml` updated for Python 3.12
- PyCharm `.idea/` config updated for Python 3.12 interpreter
- FlareSolverr Docker container started
- Re-aggregation script created at `scripts/reaggregate.sh`

---

## Remaining Open Problems

### Data & Pipeline
| # | Problem | Status | Effort |
|---|---------|--------|--------|
| DP-01 | Re-aggregation: ~30 demos not yet in roundstats/playermatchstats | **Script ready** (`scripts/reaggregate.sh`) | 30-90 min runtime |
| DP-02 | Coach can't answer per-player/per-round drill-down questions | Not started | 1 session |
| DP-03 | Analytics page shows anonymous aggregates — needs per-player breakdown | Not started | 1-2 sessions |
| DP-04 | HLTV scraping CSS selectors drifted — only 3 players scraped | Blocked (needs testing) | 1 session |

### Coach Intelligence
| # | Problem | Status | Effort |
|---|---------|--------|--------|
| CI-01 | JEPA model: trainer ready, data ready, zero epochs run | Ready to run | 1 session (GPU hrs) |
| CI-02 | No CS2 eval benchmark — can't measure coaching quality | Not started | Multi-session |
| CI-03 | No LLM fine-tuning scaffolding (LoRA/PEFT) | Not started | Multi-session |
| CI-04 | Coach Book at 151 entries, target 1500 | Not started | Several sessions |
| CI-05 | Pro baseline ignores HLTV database | Not started | 1 session |
| WR-76 | Round Reconstructor missing — tick data never reaches LLM | Not started | 3-5 days |
| WR-77 | Coordinate-to-callout mapping missing | Not started | 2-3 days |
| WR-78 | LLM hallucinates when data insufficient | Not started | 1 day |

### Frontend
| # | Problem | Status | Effort |
|---|---------|--------|--------|
| FE-01 | Chat requires Ollama + 400MB SBERT with no progress indicator | Partial | 1 session |
| FE-03 | Demo parsing 30-60s with no progress bar | Not started | 1 session |
| FE-08 | Analytics module silently returns empty | Partial | With DP-03 |

### Data Quality
| # | Problem | Status | Effort |
|---|---------|--------|--------|
| DQ-01 | `flash_assists` and `unused_utility_per_round` still zero in data | Partial | Will improve after re-aggregation |
| DQ-02 | `is_blinded` feature always zero (CS2 removed event) | Identified | `flash_duration` workaround exists but needs data re-repair |

---

## Recommended Session Order (path to v0.1)

1. **Run re-aggregation** — `bash scripts/reaggregate.sh` (30-90 min). Unblocks everything downstream.
2. ~~**WR-79 + WR-80** — Quick coaching quality wins.~~ **DONE** (commit `b9d4acf`).
3. **CI-04** — Expand Coach Book to 500+ entries. Biggest cheap quality win.
4. **DP-02** — Wire per-player/per-match retrieval into coaching chat.
5. **DP-04** — HLTV scraping session (test FlareSolverr, verify CSS selectors).
6. **CI-01** — JEPA pretraining (GPU time on RX 9070 XT).
7. **CI-02** — Build eval benchmark. Prerequisite to fine-tuning.
8. **v0.1 packaging** — PyInstaller spec, CPU-only torch, dependency cleanup.

### Beyond v0.1
- **CI-03** — LLM fine-tuning scaffolding (LoRA/PEFT, now feasible with 16GB VRAM)
- **Ghost player prototype** — Requires trained RAP model (v0.3-v1.0)
- **Books refactor** — 8 sessions, IT+EN, section collisions
- **RAP reactivation** — 5 criteria must be met (see Handoff §31)

---

## Rules for Every Session

- Read this document first.
- Don't start new features until the current session's scope is done.
- Don't claim "done" until the user verifies with eyes on screen.
- If we drift, stop and say "we're drifting from [X], should we continue or refocus?"
- Every fix must answer: whose data? which player? which match? No anonymous aggregates.
