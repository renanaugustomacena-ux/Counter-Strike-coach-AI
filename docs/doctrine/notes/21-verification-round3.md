# Verification round 3 — neural core v2 read on Windows (2026-09-12)

Mission (user directive, 2026-09-12): the Linux milestone had landed (PR #101,
CORREZIONE_NUCLEO_NEURALE Parte III steps 0–4, merged 2026-09-11) and the README
sweep was waiting as PR #102. Order given: merge first so the repo is ONE branch
locally and on GitHub, then **read before fixing** — "take decisions without
assumptions but with the full picture in front". Method: the trilogy read in
full (Parte I–III, 2,603 lines), then the whole `backend/nn/jepa_v2/` package,
`schema_v2.py`, `naming.py`, `tools/export_episodes.py`,
`tools/benchmark_jepa_v2_vs_legacy.py`, `persistence.py`, the 12 new test
files, DOCTRINE + notes 07a/07b/07c/16/17/18/20, the session-handoff
conventions; plus three bounded surveys within the 5-sub-agent cap (legacy
training stack map, Windows CI crash forensics, IT/PT README fidelity). Every
fix below was pinned by a test that FAILED first; nothing was changed on the
strength of a hypothesis alone.

## Ladder results (Windows 10, project venv, `CI` unset so ui_smoke runs)

| Gate | Before (main @ 5a9c9bb) | After (this round) |
|---|---|---|
| L2 pytest (both roots) | 2928 passed / **2 failed** / 57 skipped | **2942 passed / 0 failed** / 57 skipped (151 s) |
| L1 headless_validator | PASS 318/319 | PASS 318/319 |
| portability_test | **9/10, 1 CRITICAL** | 10/10, 0 critical |
| integrity manifest | 2/2 | 2/2 after regen |
| CI `Tests (windows-latest)` | red since de1af57 (2026-08-29) | **green**: 2872 passed / 0 failed / 74 skipped (run 34692797730) |

## What the read established (evidence, not opinion)

- **Milestone 1 is real and well-built**: SIGReg parity with two reference
  implementations, causal Transformer with QK-norm/RoPE/SwiGLU, per-step cosine,
  bf16 without scaler, episode-aware sampler that never pads, D-17 labels
  derived inside the episode, exporter that streams shards, v2 sidecar with
  schema fingerprint, 12 test files. The plan's mathematics (Parte II §12) is
  reproduced by tools the repo ships.
- **The step-4 exam has not run**: `docs/benchmarks/` does not exist; the 20k-step
  GPU run and the D-18 verdict are the next Linux session's job. Everything
  below that touches training was fixed BEFORE that exam on purpose.
- **Windows truth**: the two red tests on main were one cp1252 bug (D-38); the
  CI Windows leg had been red since 2026-08-29 for a reason unrelated to the
  neural core (D-37), and that crash kills pytest before its summary, so it hid
  every later Windows failure. The Integration CI jobs were red for a third
  unrelated reason (D-40).

## D-34 — the prediction loss never reached half the encoder (FIXED)

`losses.py` attached L_next / L_multi / batch-SIGReg to `z = taps[served_tap]`
(`encoder.py:59`, served_tap = n_layers // 2 = 2). Blocks 3–4 therefore received
gradient ONLY through the temporal-SIGReg tap at `taps[-1]`. Measured on the
default config with `lambda_sigreg_temporal = 0`: per-block grad-norms
`[0.051, 0.040, 0.0, 0.0]`. Parte III §4.6 attaches the loss to the encoder
output and §4.5 serves an intermediate tap as a READ-OUT (LeNEPA's
intermediate-layer probing); the implementation conflated the two, which also
throws away the "Guillotine" benefit the plan cites. Fix: the loss reads
`taps[-1]` (un-normed last block); serving is unchanged. Two lockstep tests:
prediction terms alone reach every block; the loss depends on `taps[-1]`.
This is the one change of this round that alters what the 20k-step exam
trains — recorded here so it can be reverted in one commit if the operator's
decision register (see D-45) says otherwise.

## D-35 — v2 dry-run wrote and resumed production checkpoints (FIXED)

`JepaV2Trainer.run` saved `jepa_v2_encoder` / `jepa_v2_full` unconditionally;
`cli.run_jepa_v2` resumed from `jepa_v2_full` unless `--no-resume`. A
`--dry-run` smoke (60 steps) therefore overwrote the production encoder and the
next real run resumed from the smoke weights with `step = 60`. The legacy
orchestrator honours B4 ("dry-run never writes", `training_orchestrator.py:436-458`).
Fix: `dry_run` flag on the trainer (no saves, logged once) and no resume in
dry-run; test asserts an empty models dir after a dry run.

## D-36 — the documented entry point could not budget a v2 run (FIXED)

`run_full_training_cycle.py --model-type jepa_v2` hands `args` to
`run_jepa_v2`, which reads `steps` / `probe_every` / `data_dir` / `no_resume`
with `getattr` defaults; the parser never declared them, so `--epochs` and
`EPOCHS=` were silently ignored for v2 and the `train.sh` help said the
opposite. Fix: the four flags declared in the parser (group "jepa_v2 only"),
`--epochs` help marked legacy-only, `train.sh` header corrected; five parser
tests.

## D-37 — Windows CI access violation at the splash test (FIXED, CI-verified)

Forensics over seven runs (all logs, stacks normalised): the first red
`Tests (windows-latest)` is **de1af57** (system tray, PR #95), not the slideshow
PR; the crash stack is byte-identical on every red run since; runner image,
PySide6 6.11.0, numpy, torch identical between the last green and the first
red. de1af57 added `tests/test_tray.py`, which sorts before
`test_v1_blockers.py`, builds two real `MainWindow`s and only calls
`deleteLater()` on them — pytest never returns to the Qt event loop, so both
hidden C++ windows outlive the module with their DeferredDelete queued. The
next main-thread pump is `QSplashScreen.showMessage` in
`test_splash_status_updates` (`app.py:80`), which faults natively. Locally
(Python 3.12.10) the crash does not reproduce even with the CI ordering and
`CI=true`; the runner has 3.11.9 — the one software variable not testable
here. Fix: `_release()` in `test_tray.py` closes, queues the delete, then
`QApplication.sendPostedEvents(None, DeferredDelete)` + `processEvents()`, and
a new postcondition test asserts no `MainWindow` survives the module — it
FAILED before the flush (2 survivors) and passes after. PR #103's Windows
CI leg ran the splash test to completion (2872 passed / 0 failed, run
34692797730) — the first green `Tests (windows-latest)` since 2026-08-29; the
Integration Windows job went green in the same run (D-40).

## D-38 — cp1252 text writes in the neural-core tools (FIXED; D-28 class)

`benchmark_jepa_v2_vs_legacy.py:676` wrote the markdown report with
`Path.write_text(report)`; the report carries "Δpos R²". Same failure class as
D-28. Fix: `encoding="utf-8"` on the report and on the six sibling JSON writes
of the tool family, plus an AST sweep test
(`test_neural_core_text_encoding.py`) that pins the rule for
`tools/{benchmark,export_episodes,measure_*,verify_math_claims}.py` and
`backend/nn/jepa_v2/*.py`.

## D-39 — benchmark contender A was misaligned, not "approximate" (FIXED)

`_encode_legacy` padded four zeros at the END of the 21-d v2 vector; the
retired v1 slots are 16–19 (kast_estimate, map_id, round_phase, weapon_class),
in the MIDDLE. The legacy encoder therefore received time_in_round / bomb /
teammates / enemies_alive in its retired slots and team_economy in slot 20.
Fix: `_bridge_v2_to_v1` zero-fills 16..19 in place; test round-trips through
`vectorizer.remap_v1_to_v2`. D-18 verdict never depended on A; the stale
"Known Issues" lines of the report were corrected too.

## D-40 — portability false positive that kept Integration CI red (FIXED)

`test_wallpaper_slideshow.py:110` used the literal `"Z:/nowhere/ghost.png"`;
`tools/portability_test.py` flags any drive-letter path as CRITICAL. The
Integration CI jobs failed on `PORTABILITY CERTIFICATION: FAILED` from PR #94
on. Fix: a nonexistent sibling of a real fixture file. Certification 10/10.

## Registered, NOT fixed (operator decisions or later steps)

- **D-41** `run_full_training_cycle.py` for `jepa_v2` still opens the monolith
  (`CoachTrainingManager()`), runs `assign_dataset_splits()` (a DB WRITE) and
  the pre/post `eval_harness` baseline that loads the LEGACY `jepa_brain`; v2
  reads only safetensors shards. Parte III §0.2 restricts training-code DB
  access. Also: `train.sh` default `MODEL_TYPE=all` exits 1 (coach_v2 is a
  `NotImplementedError` sentinel); `"rap-lite"` is in `_LEGACY_TRAIN_TYPES`
  but the orchestrator has no branch for it; two `SummaryWriter`s open the
  same run dir (`cli.py:80`, `trainer.py:95`); `JEPA_V2_DATA_DIR` has no
  registered default (literal `/data/PROIECT/cs2_v2` fallback).
- **D-42** `tools/export_episodes.py:547` stamps `tick_rate = "64"` as a
  literal; `patch_ticks = 8` is fixed while Parte I §7.3 wants
  `P = round(tick_rate/8)`. Law III (tick rate per demo) — re-export is the
  operator's call.
- **D-43** `checkpoint_hashes.json` is keyed by `str(absolute path)`
  (`persistence.py:91,106`): the 21 Linux entries are inert on Windows and
  vice versa, so CTF-1 verification silently never runs off the training box;
  the file is both git-tracked and listed in `.gitignore:221`.
- **D-44** Freeze scope: `ALLOW_LEGACY_NEURAL_TRAINING` guards only
  `TrainingOrchestrator` construction. `jepa_train.py __main__`,
  `train.py`, the supervised Phase 2/3 `latest.pt` writers (also reached by
  `batch_ingest` after a frozen Phase 1), `role_head` and
  `win_probability_trainer` still train. Parte I step 0's acceptance ("no new
  jepa_brain*/rap_coach*") holds; the plan's wider intent does not.
- **D-45** Provenance gaps (Law I): the trilogy's evidence files
  `docs/research/verify_math_claims_2026-09-05.json` and
  `name_join_coverage_2026-09-05.json` are gitignored (`.gitignore:178`), so
  every number in Parte II §12 and the benchmark's "historical row" is
  local-only; the decision IDs the v2 code cites in comments (D-04..D-20,
  A-12..A-39, C-1..C-18, B12) resolve NOWHERE in the repo — they are not this
  register's D-xx. LOCATED the same day through a read-only WSL mount of the
  Linux root partition: `~/.claude/projects/-media-renan-WORK-RECOVERED1-PROIECT-
  Counter-Strike-coach-AI/memory/neural-core-v2/` (`v2_contract.md` D-01..D-20,
  `v2_workmap.md` C-1..C-18 and A-1..A-39, `v2_decisions.md` A1..A23 and open
  questions B1..B30, `v2_inventory.md`, `verify_corpus.report.txt`). Now versioned
  under `docs/doctrine/notes/neural-core-v2/`, as the Linux session note itself
  asked. Cross-checks: its A8 and D-15 put the losses on the projector of the
  ENCODER OUTPUT and serve `taps[2]` as a read-out — D-34 is consistent with the
  register; its A1 chose `P = round(tick_rate/8)` — D-42 is a real gap between
  register and code, harmless today because T1 measured every demo at 64 Hz.
  The evidence JSONs stay local (gitignored).
- **D-46** Plan/code drift: Parte III line references are ~12 lines stale in
  §1.1/§6.2/§7.3; the named freeze test lives in `test_legacy_frozen.py`, not
  `test_training_orchestrator_logic.py`; `jepa.md` carries no pointer to the
  trilogy; `nn/README*.md:142` and `experimental/rap_coach/README*.md:53-68`
  describe orchestrator construction without the freeze; `train_docker.sh`
  help still says `jepa|rap|all`; Parte III §6.3 lists `encode_raw_negatives`
  and `_augment_with_moco_queue` as dead but both are on the live legacy path
  (`training_orchestrator.py:729`, `jepa_trainer.py:260,263,582-583`).

## Conventions honoured / noted

- Commits carry no AI trailer (fundamental §0.6, Parte III §0.1); PR #102's
  commit b19c470 had one — recorded, not rewritten.
- `docs/SESSION_HANDOFF.md` says never open SQLite on NTFS with `?mode=ro`;
  Parte III §0.2 mandates `mode=ro` and forbids `immutable=1` on Linux. Both
  are operator rules for different machines; the exporter follows the Linux
  rule and runs there.

## Shipped

Branch `fix/verification-round3` → PR #103 (Problem/Solution/Verification/Risk), merged 2026-09-12 with all 19 checks green, branch deleted.
Register updated: D-34..D-40 fixed, D-41..D-46 registered. README trio
committed with the `naming.py` description corrected in three languages.
