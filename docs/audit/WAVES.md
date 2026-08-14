# Wave Log — gate evidence per wave / phase boundary

Every entry records: scope (F-ids or batch range), commits, gate evidence (named pytest
counts incl. test_ui_smoke, coverage %, headless_validator phases, manifest verify,
PNGs eyeballed by name for UI waves), CI status both legs.

(entries appended chronologically; R0 baseline lives in BASELINE.md)

## Phase P boundary — 2026-08-14 (batches B11–B15, 30 files / ~8,700 LOC read)

- Scope: pipeline core, round-stats, tensor factory + player knowledge + heatmap,
  feature engineering, baselines + validation. No study module scheduled this phase.
- Commits: a58869b (B11), 4bcaf54 (B12), cfffdcb (B13), 8b0445a (B14=cfffdcb note:
  B14 commit cfffdcb, B15 commit 8b0445a). All pushed.
- Findings: F-0016..F-0020 registered (5× P2). F-0016 winner-dtype contract conflict
  (T-DIAG probe scheduled — escalates P1 if demoparser2 emits int); F-0017 heatmap
  double-Y-flip Kivy residue (dead display surface); F-0018 baseline fusion
  layer-priority inversion; F-0019 metric-scale incoherence (CSV percent vs ratio +
  sanity headshot band 100× loose); F-0020 all elite-comparison CSVs absent
  (feature dark on fresh installs — CP0 decision). Two campaign highlights:
  vectorizer.py is the strongest file audited so far (P-X-01/P3-A/D1/D2 quality
  architecture); B14 closed the slot-16 KAST-scale risk as VERIFIED COHERENT.
  Empirical DB verification used R0 backups (ProPlayerStatCard=0 rows, pro
  demos=0, avg_hs/avg_kast confirmed ratio-scale).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed,
  48 skipped, 5 errors — 72.0s — IDENTICAL to R0 baseline** (known reds
  F-0002/F-0003 only; no regression from audit commits). Coverage 55.40%
  (floor 33%) ✓. test_ui_smoke.py: 4/4 green (named run, 7.5s).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged (no UI edits).

## Phase D boundary — 2026-08-14 (batches B04–B10, 69 files / ~13,900 LOC read)

- Scope: storage core/data/aux + 3 migration trees + demo parsing + external sources
  + ingestion packages + orchestration. Study modules 09 (full) + 10 (leverage sections).
- Commits: f2aa445 (B04), 638008a (B05), dc40411 (B06), 4475ff7 (B07), 6c62d68 (B08),
  f3e226f (B09), B10 in this commit. All pushed.
- Findings: F-0012..F-0015 registered this phase (2× P1 new: undefined-logger NameError
  in shard fallbacks; worker 5-min stale threshold = the documented P4-B bug + F-0014
  dead main.py launcher). F-0006 blast radius widened; remediation template identified
  (demo_loader's validate_demo_file wiring). Recon's three-migration-trees concern
  DISSOLVED (two proper tombstones, one canonical chain).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed, 48 skipped,
  5 errors — 71.8s — IDENTICAL to R0 baseline** (known reds F-0002/F-0003 only; no
  regression from audit commits). test_ui_smoke 4/4 green inside the run.
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged (no UI edits).

## Phase F boundary — 2026-08-14 (batches B01–B03, 26 files / 5,365 LOC read)

- Scope: R0 + pass-1 Phase F (core/ + observability/) + study modules 22, 07.
- Commits: 839c24b (R0), 9f2a453 (B01), 0f19ac4 (B02), B03 in this commit. All pushed.
- Findings register: F-0001..F-0011 (2× P1, 9× P2). No fixes applied (diagnose-first).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed, 48 skipped,
  5 errors — 73.7s — IDENTICAL to R0 baseline** (known reds F-0002 tick-rate SSOT,
  F-0003 symlink privilege; no regression from audit commits). Coverage floor passed.
- test_ui_smoke.py: 4/4 green inside the run (screen walk, theme switching, language
  roundtrip, collapse/resize).
- CI: not triggered (docs-only paths are ignored by design; branch filter issue = F-0004).
- Render matrix: unchanged (no UI edits; committed design-close matrix stands).
