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

## The 12 P1s (grep-verified against the register; proposed W1/W2 scope)
| ID | Subsystem | One-liner | Fix size |
|---|---|---|---|
| F-0001 | infra/integrity | Both manifests stale (45/15/0 drift; root copy carries deleted main.py) | W1 opener: resync core/, DELETE root copy |
| F-0004 | infra/ci | Branch filter misses feat/** and chore/** — zero CI runs on real branches | 1-line filter + PR workflow |
| F-0006 | ingestion/parsing | pyo3 PanicException bypasses every demo-parse guard | catch (Exception, PanicException) at all parser sites |
| F-0012 | storage/shards | Undefined name `logger` (module has only `_logger`) — fallback paths raise NameError | rename + regression test |
| F-0014 | daemons/hltv | start_detached launches DELETED main.py; dormant path exits while notifying "retrying" | real entrypoint; continue-not-return |
| F-0015 | daemons/run_worker | Keeps the 5-min stale threshold P4-B already fixed at 30 (duplicate-processing) + skip-after-claim leak | align to SSOT setting; check-before-claim |
| F-0030 | services/role-insights | Live insight fabricates "IGL (100% confidence)" for balanced-K/D players | feed real features / suppress fabricated confidence |
| F-0032 | control/ml-stop | Operator STOP is swallowed per phase — training continues, status lies | propagate stop exception; honest final status |
| F-0037 | ingestion/concurrency | Zero cross-runner exclusion — concurrent triggers double-parse demos (FIVE trigger surfaces) | atomic claim; single fix covers all surfaces |
| F-0038 | ui/threading | THREE screens touch the DB on the GUI thread | move to Worker pattern (template exists) |
| F-0039 | tools/safety | "Safe" runner executes 13 bare-invocation MUTATING tools (rebuild_monolith timeout-kill = data loss) | gate list + dry-run defaults |
| F-0040 | tools/build | build_pipeline SANITIZES (deletes DBs/models/logs) BEFORE honoring --test-only | move sanitize after the early-return |

(F-0002/F-0003 — the two known-red gate members — are P2 one-liners
W2 clears first so the gate goes fully green early. F-0043, exit-0 on
"Training Aborted", is P2 and rides with the safety cluster below.)

## Decision clusters (need your call at this checkpoint)
1. **Safety-tool family (F-0039/40 P1 + F-0041/43 P2)** — the "safe" runner and
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
