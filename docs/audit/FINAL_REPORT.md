# Nuke-Proof Audit — Final Report (2026-08-14)

One day, one campaign, the whole project: read twice, diagnosed fully,
fixed to a green gate, documented trilingually.

## Numbers
| Metric | Value |
|---|---|
| Files read personally (Pass 1) | 618 / 618 (76 batches + R0) |
| LOC covered | ~155,000 |
| Cross-cutting lenses (Pass 2) | L1–L10 + L-COV; every ledger row tagged |
| Findings registered | 44 (0 P0 · 12 P1 · 32 P2) |
| Findings resolved | **44 / 44** — 31 fixed@sha (each with same-commit regression tests), 13 deferred with written reasons |
| Test gate before → after | 2 failed / 2500 passed / 5 errors → **0 failed / 2574 passed / 0 errors** |
| Coverage floor | 33% → **50%** (suite ~55.8%) |
| headless_validator | FAIL → **PASS** |
| Integrity manifest | 45/15 drift → **GREEN** (stale root duplicate deleted) |
| CI | zero runs ever on real branches → **green pipeline on every push** |
| Study companion | 7 modules of 04-PROGRAMMAZIONE-PYTHON read and applied (STUDY_LOG.md) |

## What made this "nuke-proof"
1. **Every claim has evidence.** 76 dossiers, a findings register with
   file:line proof, per-wave gate numbers, T-DIAG executed with backups
   and byte-identical checkpoint hashes.
2. **Every fix has a net.** Same-commit regression tests, plus
   permanent doctrine tests (no GUI-thread DB access; no bare tick-rate
   literals; no re-declared map lists; single pytest config; safety
   runner census).
3. **Every deferral has a reason.** Nothing is silently open: the 13
   deferred items name their blocking condition (research track per
   CP0 #5, missing reference data, visual ground truth needed…).
4. **The tooling now defends itself.** pre-commit (black/isort/ruff +
   integrity manifest + dev-health) green on every commit; CI runs on
   the real branch conventions with a dependency gate.

## Decisions of record (CP0, user-approved)
- Coaching advice stays **English** (product decision).
- F-0039 safety family **fixed, not deleted**.
- JEPA 25-vs-10 fine-tune contract stays **guarded** (26-RANGE-01).
- Map names: **one authority** (`core/known_maps.py`).
- Phantom references are **replaced with the real entry point,
  never just deleted** (user rule, applied throughout).

## Where everything lives
- `docs/audit/FINDINGS.md` — the 44-row register, statuses final.
- `docs/audit/WAVES.md` — per-phase/wave gate evidence.
- `docs/audit/CONTRACTS.md` — the ten lens contract tables.
- `docs/audit/dossiers/D-B01..D-B76.md` — per-file dossiers.
- `docs/audit/CP0.md` — the checkpoint + decision log.
- `docs/audit/STUDY_LOG.md` — course modules → lessons → applications.
- `docs/audit/sweeps/S-*.md` — mechanical census evidence.
