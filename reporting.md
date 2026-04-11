# Code Integrity Audit Report

> **Status (2026-04-11):** All 8 findings have been **FIXED** and verified. See ENGINEERING_HANDOFF.md §44 (DA-1..DA-8) and §53 (commit `5bbd2b3`). This report is retained as historical record.

**Total Files Audited: 1 / 1**
**Issues Found: 8 (all resolved)**
**CRITICAL: 0 | HIGH: 1 | MEDIUM: 4 | LOW: 3**

---

## 1. jepa_train.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/backend/nn/jepa_train.py` (642 lines)

### Findings

* **Line 103, 126, 169, 209** — `conn = sqlite3.connect(_DB_PATH, check_same_thread=False)`
  **Classification:** Silent Fail
  **Severity:** HIGH
  **Evidence:** Four raw sqlite3 connections opened without `PRAGMA journal_mode=WAL` or `PRAGMA busy_timeout`. The monolith DB enforces WAL at the ORM layer (`database.py:98`), but raw connections bypass this. If the Quad-Daemon engine runs concurrently (Scanner/Digester writing ticks while training reads), a non-WAL reader can see inconsistent data or trigger `SQLITE_BUSY` with no retry. The `check_same_thread=False` flag further increases risk by allowing cross-thread sharing of a non-WAL connection.
  **Fix:** After each `sqlite3.connect()`, add `conn.execute("PRAGMA journal_mode=WAL"); conn.execute("PRAGMA busy_timeout=30000")`

* **Line 367-381** — Negative sampling with `batch_size_actual == 1`
  ```python
  effective_negatives = min(num_negatives, batch_size_actual - 1)
  if effective_negatives > 0 and batch_size_actual > 1:
      ...
  else:
      neg_indices = torch.zeros(batch_size_actual, max(1, effective_negatives), ...)
  negatives = target[neg_indices]
  ```
  **Classification:** False Positive (loss computes but is meaningless)
  **Severity:** MEDIUM
  **Evidence:** When the last batch has exactly 1 sample, `effective_negatives = 0`, the else-branch creates `neg_indices` pointing to index 0 (the sample itself). `negatives = target[0]` equals the positive target. `jepa_contrastive_loss(pred, target, negatives)` receives positive == negative, producing degenerate loss (log(exp(sim)/exp(sim)) = log(1) = 0). The gradient for this batch is zero — no learning signal, but no corruption either. Occurs once per epoch at most.
  **Fix:** Guard: `if batch_size_actual < 2: continue` before the negative sampling block.

* **Line 39 vs Line 54** — `_MIN_TICKS_FOR_SEQUENCE = 20` decoupled from `context_len + target_len`
  ```python
  _MIN_TICKS_FOR_SEQUENCE = 20  # line 39
  # ...
  context_len: int = 10, target_len: int = 10  # line 54
  ```
  **Classification:** False Positive (works by coincidence, not contract)
  **Severity:** MEDIUM
  **Evidence:** The minimum ticks constant (20) exactly equals `context_len + target_len` (10+10) but is not derived from them. If either changes independently, `JEPAPretrainDataset.__getitem__` would produce under-sized tensors that crash the DataLoader collation. No compile-time assertion links these values.
  **Fix:** Add assertion: `assert _MIN_TICKS_FOR_SEQUENCE >= context_len + target_len` in `JEPAPretrainDataset.__init__`, or derive the constant.

* **Line 579** — `torch.save(checkpoint, path)`
  **Classification:** Silent Fail
  **Severity:** MEDIUM
  **Evidence:** Non-atomic write. If the process crashes, is killed, or the disk fills mid-save, the checkpoint file is left in a corrupt partial state. The next `load_jepa_model()` call would fail with an opaque `RuntimeError` or `pickle.UnpicklingError` instead of finding the previous valid checkpoint.
  **Fix:** Write to a temp file in the same directory, then `os.replace(tmp, path)` for atomic swap.

* **Line 137** — `if avg_kast > 0:`
  ```python
  avg_kast = float(row_kast[0]) if row_kast and row_kast[0] is not None else 0.0
  if avg_kast > 0:
      for td in tick_dicts:
          td["kast"] = avg_kast
  ```
  **Classification:** False Negative (edge case)
  **Severity:** LOW
  **Evidence:** A legitimate KAST of exactly 0.0 (every round: died, no kills, no assists, not traded) would skip injection. The vectorizer fallback `estimate_kast_from_stats()` also returns 0.0 (no stats in tick data), so the end result is identical. No functional impact, but the `> 0` guard is semantically wrong — it conflates "no data" with "zero data."
  **Fix:** Change to `if row_kast is not None and row_kast[0] is not None:` and always inject the value.

* **Line 213** — `WHERE is_pro = 0` (no sample_weight filter)
  ```python
  "SELECT demo_name, player_name FROM playermatchstats "
  "WHERE is_pro = 0 "
  ```
  **Classification:** False Negative
  **Severity:** LOW
  **Evidence:** `load_user_match_sequences()` does not filter `sample_weight > 0`. If ghost user players existed (sample_weight=0), they would be included in fine-tuning data. Currently no user demos are ingested (project phase: "teach the coach"), so this is not exploitable. The pro counterpart at line 173 correctly filters `AND sample_weight > 0`.
  **Fix:** Add `AND sample_weight > 0` to the WHERE clause for parity.

* **Line 617** — `parser.add_argument("--model-path", default="models/jepa_model.pt")`
  **Classification:** Silent Fail
  **Severity:** LOW
  **Evidence:** Relative path default. If `__main__` is invoked from a directory other than the project root (e.g., `cd /tmp && python -m Programma_CS2_RENAN.backend.nn.jepa_train --mode pretrain`), the model saves to `/tmp/models/jepa_model.pt` instead of the project's `models/` directory. The `models/` directory may not exist at the relative path, causing `FileNotFoundError`.
  **Fix:** Resolve relative to `_PROJECT_ROOT`: `default=str(_PROJECT_ROOT / "models" / "jepa_model.pt")`

### Functions verified PASS (no findings)

* `JEPAPretrainDataset.__len__` (line 60) — trivially correct
* `load_pro_demo_sequences` (lines 151-195) — ghost filter present, empty guard present, logging correct
* `train_jepa_pretrain` main loop (lines 352-431) — seed set, EMA schedule correct per Assran et al., gradient clipping present, early stopping present, callbacks properly opened/closed
* `train_jepa_finetune` (lines 462-546) — encoder freeze enforced, separate optimizer for LSTM+MoE only, gradient clipping present
* `load_jepa_model` (lines 588-606) — `weights_only=True` safe, `strict=True` default catches dim mismatches
