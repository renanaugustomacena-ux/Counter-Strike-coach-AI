# Wave Log — gate evidence per wave / phase boundary

Every entry records: scope (F-ids or batch range), commits, gate evidence (named pytest
counts incl. test_ui_smoke, coverage %, headless_validator phases, manifest verify,
PNGs eyeballed by name for UI waves), CI status both legs.

(entries appended chronologically; R0 baseline lives in BASELINE.md)

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
