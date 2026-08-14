# CP0 — Diagnosis-Complete Checkpoint (2026-08-14)

Both passes done: every one of the 618 ledger rows read personally
(Pass 1, 76 batches), then re-crossed through 10 lenses + coverage
sweep (Pass 2). T-DIAG executed with backups and evidence. NO fixes
applied anywhere — this document is the decision menu.

## Register totals
**44 findings: 0 × P0 · 12 × P1 · 32 × P2** (FINDINGS.md is the full
evidence table; every row has file:line evidence and a proposed fix).

The codebase's honest headline: **no P0 exists.** The architecture's
war-story discipline (R4/WR/26-*/GAP doctrine comments + pinning
tests) is the strongest I have seen in a personal project — Phase T
confirmed nearly every historical bug has a regression net.

## The 12 P1s (proposed W1/W2 scope)
| ID | One-liner | Fix size |
|---|---|---|
| F-0001 | Both integrity manifests stale (45/15/0 drift; root copy carries deleted main.py) | W1 opener: resync core/, DELETE root copy |
| F-0004 | CI branch filter misses feat/** and chore/** — zero CI runs on real branches | 1-line filter + PR workflow |
| F-0006 | pyo3 PanicException bypasses every demo-parse guard | catch (Exception, PanicException) at ~6 sites |
| F-0012/F-0013 | parse-timeout implementation + executor shutdown traps (Phase D pair) | scoped rework, tests exist |
| F-0014 | hltv_sync start_detached launches DELETED main.py; dormant path lies | point at real entrypoint; continue-not-return |
| F-0015 | run_worker keeps the 5-min stale threshold P4-B already fixed at 30 | align to SSOT setting |
| F-0037 | Ingestion double-processing: check-then-act + FIVE trigger surfaces | claim-atomically; single fix, 5 surfaces covered |
| F-0038 | Main-thread DB writes in 3 screens (profile save, chronovisor scan, wizard finish) | move to Worker pattern (template exists) |
| F-0039 | verify_all_safe schedules 13 bare-invocation MUTATING tools (rebuild_monolith timeout-kill = data loss) | prefix/allowlist gate + per-tool dry-run defaults |
| F-0040 | build_pipeline SANITIZES (deletes DBs/models/logs) before honoring --test-only | move sanitize after the early-return |
| F-0043 | Training entry exits 0 on "Training Aborted" — automation blind | non-zero exit + test data-gate |

(F-0002/F-0003 — the two known-red gate members — are P2 one-liners
that W2 clears first so the gate goes fully green early.)

## Decision clusters (need your call at this checkpoint)
1. **Safety-tool family (F-0039/40/41/43)** — the "safe" runner and
   build tooling can destroy data or lie about success. Proposed: one
   focused W2 sub-wave; gold standard already exists in-repo
   (wipe_for_reingest_safe / seed_hltv_top_n patterns).
2. **Map-name SSOT** — 12 divergent known-map lists. Proposed: one
   authority module consumed everywhere (W3, mechanical).
3. **L7 language decision** — ALL coaching advice is English by
   construction and FOUR test suites pin those strings. Options:
   (a) keep advice EN as a product decision (zero churn, document it);
   (b) i18n-ify advice = engine + 4 suites in one coordinated wave.
   The UI chrome i18n gaps (pro_player_detail, faceit, wizard,
   constructor literals) are fixable either way (W2/W3).
4. **Theme-switch staleness** — instance-styled widgets never restyle
   on theme change (FilterChip/StatusChip/roster/banners). Proposed:
   one refresh_styling wiring wave (W3).
5. **JEPA/RAP readiness** — 26-RANGE-01 open contract (25-dim targets
   vs 10-dim head) is GUARDED loud, not resolved; RAP behind maturity
   gate. Proposed: leave as guarded (they are research-track), only
   docs note at W6. Say if you want them closed instead.
6. **reset_pro_data retrofit** — deletes more than the gold-standard
   wipe with none of its safety generation (W3).
7. **F-0044 shadow pytest.ini** — delete it so test config stops
   depending on invocation shape (W3 one-liner + meta-test).

## Wave plan (as locked in the campaign plan, now with real scopes)
- **W1** — manifest resync + root-manifest delete + CI filter fix
  (F-0001, F-0004). Isolated commits, full gate after each.
- **W2** — the 12 P1s by subsystem + the two known-red one-liners
  (F-0002 SSOT import, F-0003 skipif). Regression test per fix.
- **W3** — P2 behavioral batches: safety-tool family, map SSOT,
  theme staleness, dead-code ledger (L10 table), test-debt items
  (stale Bug#4 suite, rating-parity class, F-0044).
- **W4** — tooling ratchet: black align, ruff introduction, mypy
  ladder (course-09 playbook), coverage floor raise, `slow`/marker
  hygiene, dependency-conflict gates.
- **W5** — hygiene preflight (tracked-vs-disk-vs-manifest); LFS
  attributes + line-ending policy respected (NO global renormalize).
- **W6** — trilingual READMEs + CHANGELOG + audit close-out; then
  **branch consolidation** (your directive): merge
  chore/nuke-proof-audit → feat/frontend-design-atlas → main, delete
  side branches (I will confirm right before deletion).

## Gate truth at this checkpoint
Every phase boundary ran the full gate: **2 failed, 2500 passed, 48
skipped, 5 errors — byte-identical to the R0 baseline every time**
(the 2 reds are F-0002/F-0003 themselves); coverage 55.40% vs 33%
floor; test_ui_smoke.py 4/4 named at every boundary. T-DIAG left
production checkpoints byte-identical (hash-verified) and the only DB
delta was the dry-run's own documented split-label write.

**Approve the wave plan (or amend the clusters above) and W1 starts.**
