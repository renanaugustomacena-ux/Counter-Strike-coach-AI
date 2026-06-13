# DIAGNOSIS — 2026-05

Single canonical state-of-the-system snapshot for the Macena CS2 Analyzer
project. Replaces 9 prior dump-style docs (see §6). Refresh when material
state changes; do not append narrative.

**Owner:** Renan Augusto Macena · **Branch:** `main` (post-`1878514`) · **Last refresh:** 2026-06-13

---

## 1. Executive summary

Repo state is **GREEN** for runtime and validation; **1 test failure** (skill-vector expectation, tracked as Programme Phase C0):

- `./.venv/bin/python tools/headless_validator.py` → **314/319 PASS, 0 fail, 5 warn, exit 0** (`VERDICT: PASS`).
- `./.venv/bin/python -m pytest` (scoped) → **2028 passed, 1 failed, 14 skipped, 5 xpassed**.
- All 11 REFERENCE.md §3 invariants enforced (verified 2026-06-13).
- JEPA training: val loss ~1.8977, maturity state `doubt`. Plateau root-caused to fixed-seed 5,024-tick/epoch subsampling (fix designed, not yet implemented — Programme Phase B).
- 14 arxiv JEPA/VL-JEPA papers added to `docs/research/arxiv/`.

Open work tracked in [TASKS.md](../TASKS.md) and `~/.claude/plans/cs2-completion-2026-06-13/` (completion programme, 7 phases A–G).

---

## 2. Validator current status

Run: `./.venv/bin/python tools/headless_validator.py 2>&1 | tail -25`

```
RESULT: 314/319 passed, 0 failed, 5 warnings
VERDICT: PASS
```

Residual warnings (all by-design / known-deferred):

| # | Source | Warning | Disposition |
|---|---|---|---|
| 1 | Core | `import map_manager: No module named 'kivy'` | Legacy Kivy UI artifact; qt_app is the active UI. Programme Phase C11 retires these imports. |
| 2 | Core | `import registry: No module named 'kivymd'` | Same as #1. |
| 3 | Deps | `Optional deps not installed: shap` | Optional model-explainability dep; coaching pipeline tolerates absence. |
| 4 | Web-Marquee | `web/match-detail/ not scaffolded` | Gated until P4.1+ per redesign plan. Defer. |
| 5 | Web-Marquee | `web/coach-chat/ not scaffolded` | Same as #4. |

Note: ncps + hflayers warnings (#4/#5 in prior version) are now resolved — both packages installed in venv.

---

## 3. Open invariants & their guards

These are the production-correctness contracts. Violation = silent corruption. All currently enforced.

| ID | Where | Guard | Current state |
|---|---|---|---|
| **P-X-01** | `feature_engineering/vectorizer.py` | `assert len(FEATURE_NAMES) == METADATA_DIM=25` at module import | ✅ Enforced; 104/104 contract tests pass after refactor |
| **P-RSB-03** | `processing/round_reconstructor.py` | `round_won` excluded from training feature set (label-leak) | ✅ Enforced |
| **NN-MEM-01** | `rap_coach/memory.py:111, :175-180` | Hopfield bypassed until ≥2 forward passes | ✅ Enforced |
| **NN-16** | `backend/nn/ema.py:79, 90` | EMA `apply_shadow()` calls `.clone()` on shadows | ✅ Enforced |
| **NN-JM-04** | `backend/nn/jepa_trainer.py:51-52` | Target encoder `requires_grad=False` during EMA | ✅ Enforced |
| **DS-12** | `demo_format_adapter.py:49` | `MIN_DEMO_SIZE = 10 MB` | ✅ Enforced |
| **P-VEC-02 / P3-A** | `vectorizer._finalize_vector` | NaN/Inf clamp; >5% rate per batch raises `DataQualityError` | ✅ Enforced; helper extracted but logic byte-for-byte identical |
| **LEAK-01** | `training_orchestrator._rap_collect_per_tick` | When per-tick `all_players` context absent, mask sample (`val_mask=False`) instead of substituting `round_outcome` | ✅ Enforced; refactor preserves verbatim — confirmed by AST diff |
| **REPR-01** | `jepa_train._jepa_pretrain_finalize` | EMA step counter persisted to `model._saved_ema_step` for resume reproducibility | ✅ Enforced |
| **DET-01** | `run_full_training_cycle.py` (B#3, uncommitted in master plan) | `set_global_seed()` called immediately after argparse | Master plan B#3 — uncommitted on disk; verify before resuming Phase A. |
| **Tick-decimation forbidden** | `run_ingestion._save_sequential_data` + `_build_match_tick_dataframe` + `_build_legacy_tick_dataframe` | Every input row maps 1:1 to one output row; player-name filter only | ✅ Enforced |
| **HLTV DB separation** | `hltv_metadata.db` ≠ `database.db` | Feature-purpose separation; `get_hltv_db_manager()` vs `get_db_manager()` | ✅ Enforced; do not conflate |

---

## 4. Hardware context

**Personal laptop (default workstation):**
- GPU: NVIDIA GeForce GTX 1650 (Turing, compute capability 7.5)
- VRAM: 4096 MiB
- Driver: 580.126.09 (CUDA 13.0 runtime supported)
- Implication: full-batch JEPA training will OOM. Use `torch.cuda.amp.autocast` + reduced batch (start at `batch_size=4`) + gradient accumulation. Inference unaffected at normal sizes.

**Secondary machine (occasional):**
- GPU: AMD Radeon RX 9070 XT (RDNA 4) — ROCm stack
- Authored the Phase 0–4 visual redesign that landed in `bd033ca`.
- Repo retains cross-stack parity artifacts: `_rocm_smoke.sh`, `.cs2_req_no_torch.txt`, ROCm-aware install paths in launch scripts. **Do not delete** during doc cleanup.

**Venv:**
- Python 3.12.3 at `./.venv/bin/python` (canonical interpreter; system has only `python3`).
- Torch: `2.11.0+cu130` (working; do not downgrade).
- 142 packages installed including PySide6 6.11.0, demoparser2 0.41.1, watchdog 5.0.3, scikit-learn 1.8.0, sentence-transformers 3.4.1, faiss-cpu, polars.
- **Known issue:** `./.venv/bin/pip` shebang has stale path from a venv relocation (`/media/renan/New Volume/Counter-Strike-coach-AI/...` missing the `PROIECT/` segment). Workaround: use `./.venv/bin/python -m pip ...` for any pip operation. Real fix (deferred): recreate venv or rewrite shebang.

**Filesystem:**
- Repo lives on `/dev/sda2` (NTFS3 kernel driver). Past corruption incident 2026-04-29 02:09 UTC silently zeroed files; resolved 2026-05-02 via `chkdsk` from Windows. Volume currently clean (`dmesg | grep ntfs3` empty). Long-term recommendation: reformat to ext4/btrfs OR move active repos to a Linux-native volume.

---

## 5. Active backlog cross-reference

Active programme: `~/.claude/plans/cs2-completion-2026-06-13/` (15-file completion programme; supersedes all prior plan files including `cs2-coach-flawless-readiness-master-plan.md` which no longer exists on disk).

Programme phases: A (foundation/truth) → B (training engine) → C (code quality) → D (data pipeline) → E (documentation) → F (product completion) → G (release/data ops). See `01-MASTER-PLAN.md` for full checklist and session log.

---

## 6. Replaced these 9 stale docs (removed 2026-05-03)

This file consolidates and supersedes nine prior dump-style docs that violated the CLAUDE.md canonical sibling-doc rule. They were already gitignored under the `.gitignore` "Internal review / audit / engineering handoff documents" section (lines 95+) — i.e., **never tracked in git history**. Removed from local disk 2026-05-03 via plain `rm` (not `git rm`); 384 KB freed; no repo-history change since they never lived there:

1. `PYCHARM_CONFIGURATION_GUIDE.md` (749 L) — IDE setup, external-tool config; not part of code or build.
2. `PYCHARM_CONFIGURATION_GUIDE _reference.md` (830 L, note literal space in filename) — duplicate of #1.
3. `KNOWLEDGE_TRANSFER_TO_CS2_COACH.md` (1019 L) — narrative from prior project; superseded by current code state.
4. `reporting.md` (89 L) — superseded by `Programma_CS2_RENAN/reporting/` source.
5. `docs/AUDIT_PROGRESS.md` (5.4K) — duplicate intent with `AUDIT.md`.
6. `docs/DEEP_AUDIT_FINDINGS.md` (14K) — frozen findings; relevant items absorbed into `AUDIT.md`.
7. `docs/COACH_QUALITY_ROADMAP.md` (31K) — phase planning superseded by master plan.
8. `docs/ENGINEERING_HANDOFF.md` (163K) — large narrative handoff; superseded.
9. `docs/FRONTEND_ANALYSIS.md` (8.8K) — pre-redesign legacy UI analysis.

**Do NOT delete:**
- `jepa.md` (active reference, linked from `REFERENCE.md`)
- `docs/OPEN_PROBLEMS.md` (active roadmap)
- `docs/books/*.md` (genuine educational content)
- `docs/archive/*` (intentionally archived; already removed from active surface)
- Two PDFs in repo root (`CS2_Coach_Modernization_Report.pdf`, `CS2_Coach_Supplement_N260.pdf`) — already untracked per `.gitignore`.
- `_rocm_smoke.sh`, `.cs2_req_no_torch.txt` — cross-stack parity artifacts (see §4).

Audit trail (executed 2026-05-03):

```bash
rm \
  PYCHARM_CONFIGURATION_GUIDE.md \
  'PYCHARM_CONFIGURATION_GUIDE _reference.md' \
  KNOWLEDGE_TRANSFER_TO_CS2_COACH.md \
  reporting.md \
  docs/AUDIT_PROGRESS.md \
  docs/DEEP_AUDIT_FINDINGS.md \
  docs/COACH_QUALITY_ROADMAP.md \
  docs/ENGINEERING_HANDOFF.md \
  docs/FRONTEND_ANALYSIS.md
```

This action is irreversible (the files were never tracked, so they exist nowhere in git history). If anything in them is later needed, regenerate from current code state or recreate from external backups.

---

## 7. How to refresh this file

When state changes materially (new validator failure, invariant breach, hardware swap, master-plan phase completion):

1. Run `./.venv/bin/python tools/headless_validator.py 2>&1 | tail -15` and update §2.
2. Diff `git log --oneline ${LAST_REFRESH_COMMIT}..HEAD` and update §5.
3. Run `./.venv/bin/python -m pytest Programma_CS2_RENAN/tests/ --tb=no -q | tail -3` and update §1.
4. If invariants changed, update §3 against `CLAUDE.md` "Critical Invariants" section.
5. Bump the **Last refresh** date at the top.

Keep this file under 250 lines; prune §5 once items absorbed elsewhere.

---

**End of diagnosis.**
