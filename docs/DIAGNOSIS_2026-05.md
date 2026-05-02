# DIAGNOSIS — 2026-05

Single canonical state-of-the-system snapshot for the Macena CS2 Analyzer
project. Replaces 9 prior dump-style docs (see §6). Refresh when material
state changes; do not append narrative.

**Owner:** Renan Augusto Macena · **Branch:** `main` (post-`da2d490`) · **Last refresh:** 2026-05-03

---

## 1. Executive summary

Repo state is **GREEN** for runtime, validation, and tests:

- `./.venv/bin/python tools/headless_validator.py` → **312/319 PASS, 0 fail, 7 warn, exit 0** (`VERDICT: PASS`).
- `./.venv/bin/python -m pytest Programma_CS2_RENAN/tests/` → **1932 passed, 63 skipped, 0 failed**.
- All 8 CLAUDE.md production invariants enforced.
- All 12 oversized functions (>200 lines) refactored; Phase 23 long-fn warning eliminated.
- Documentation surface collapsed to canonical sibling-doc set + this file.

Open work tracked in [TASKS.md](../TASKS.md) and `~/.claude/plans/cs2-coach-flawless-readiness-master-plan.md`. Phase F (refactor) and parts of Phase H (project hygiene) are now done; remaining tracks listed in §5.

---

## 2. Validator current status

Run: `./.venv/bin/python tools/headless_validator.py 2>&1 | tail -25`

```
RESULT: 312/319 passed, 0 failed, 7 warnings
VERDICT: PASS
```

Residual warnings (all by-design / known-deferred):

| # | Source | Warning | Disposition |
|---|---|---|---|
| 1 | Core | `import map_manager: No module named 'kivy'` | Legacy Kivy UI artifact; qt_app is the active UI. Remove `map_manager`/`registry` Kivy imports during Phase H legacy-screen cleanup. |
| 2 | Core | `import registry: No module named 'kivymd'` | Same as #1. |
| 3 | Deps | `Optional deps not installed: shap` | Optional model-explainability dep; coaching pipeline tolerates absence. Install only when shap-driven explanations needed. |
| 4 | RAP | `RAPCoachModel full forward pass: ncps + hflayers required` | RAP coach is opt-in (`USE_RAP_MODEL=True`). `hflayers` is **not on PyPI** — installation requires a wheel from upstream maintainer (master plan §B#5). Defer until RAP path is exercised. |
| 5 | RAP | `compute_sparsity_loss safety: ncps + hflayers required` | Same as #4. |
| 6 | Web-Marquee | `web/match-detail/ not scaffolded` | Gated until P4.1+ per redesign plan. Defer. |
| 7 | Web-Marquee | `web/coach-chat/ not scaffolded` | Same as #6. |

**Pre-commit gate:** all hooks pass (`integrity-manifest-check`, `dev-health-quick`, black, isort, trim/EOF/yaml/json/private-key/large-files/merge-conflict checks).

---

## 3. Open invariants & their guards

These are the production-correctness contracts. Violation = silent corruption. All currently enforced.

| ID | Where | Guard | Current state |
|---|---|---|---|
| **P-X-01** | `feature_engineering/vectorizer.py` | `assert len(FEATURE_NAMES) == METADATA_DIM=25` at module import | ✅ Enforced; 104/104 contract tests pass after refactor |
| **P-RSB-03** | `processing/round_reconstructor.py` | `round_won` excluded from training feature set (label-leak) | ✅ Enforced |
| **NN-MEM-01** | `rap_coach/memory.py:74-78` | Hopfield bypassed until ≥2 forward passes | ✅ Enforced |
| **NN-16** | `backend/nn/ema.py:79` | EMA `apply_shadow()` calls `.clone()` on shadows | ✅ Enforced |
| **NN-JM-04** | `backend/nn/jepa_model.py:323-331` | Target encoder `requires_grad=False` during EMA | ✅ Enforced; preserved verbatim by `_jepa_pretrain_setup_training` helper |
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

Active tracker: `~/.claude/plans/cs2-coach-flawless-readiness-master-plan.md` (single source of truth for open work).

Recently completed (this session, 2026-05-02 → 2026-05-03):

| Track | Status | Commit |
|---|---|---|
| Phase 0 — Pre-flight gates | ✅ DONE | (no commit; verification only) |
| Track A — Dependency restoration | ✅ N/A (venv already provisioned) | — |
| Track B1 — 8 production-fn refactors | ✅ DONE | [`d8c710e`](#commit-d8c710e) |
| Track B2 — 4 tools-side refactors | ✅ DONE | [`da2d490`](#commit-da2d490) |
| Memory housekeeping (NTFS3 resolved + GTX 1650 record) | ✅ DONE | (memory only) |
| Track D — Documentation rebuild | 🟡 IN PROGRESS — this file is D.1 | — |

Open in master plan (proceed in order):

- **Phase E.3** — ROCm decision: keep `_rocm_smoke.sh` and `.cs2_req_no_torch.txt` as cross-stack parity artifacts (not deletion candidates). Already documented above.
- **Phase F.2** — Broad-except remediation (TASKS#28, 32 sites). Independent track.
- **Phase G.4** — Validator-exit-0 acceptance gate. Currently passing; continue to verify after every track lands.
- **Phase H.2 / H.5** — Project hygiene: tools audit + remaining README sweep.
- **Track C1** — UI soft-frost polish (Phase 7). Visual redesign substrate landed in `bd033ca`; frost-tier tokens + `card.py` FROSTED depth tier + QSS layering pending. Needs running Qt app for visual verification.
- **Track C2 (Phase 8)** — Legacy screen adoption (8 screens still on pre-redesign layouts: user_profile, profile, settings, help, wizard, faceit_config, steam_config; partial coach). Defer until C1 ships.

---

## 6. Replaces these stale docs (delete after sign-off)

This file consolidates and supersedes nine prior dump-style docs. CLAUDE.md mandates canonical sibling-doc set only (`REFERENCE.md`, `AUDIT.md`, `TASKS.md`); these violate that rule and should be removed in a single atomic `git rm` commit:

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

Atomic deletion command (run only after user sign-off):

```bash
git rm \
  PYCHARM_CONFIGURATION_GUIDE.md \
  'PYCHARM_CONFIGURATION_GUIDE _reference.md' \
  KNOWLEDGE_TRANSFER_TO_CS2_COACH.md \
  reporting.md \
  docs/AUDIT_PROGRESS.md \
  docs/DEEP_AUDIT_FINDINGS.md \
  docs/COACH_QUALITY_ROADMAP.md \
  docs/ENGINEERING_HANDOFF.md \
  docs/FRONTEND_ANALYSIS.md
git commit -m "docs: collapse 9 stale dump docs into DIAGNOSIS_2026-05.md"
```

Verify exact filename of the literal-space duplicate via `ls -la PYCHARM*` before staging.

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
