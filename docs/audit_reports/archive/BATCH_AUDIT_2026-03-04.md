# Audit Sistematico Completo — Macena CS2 Analyzer

> **STATUS: HISTORICAL — All findings resolved (2026-03-08)**
> Per-batch details removed after cross-referencing against Remediation Phases 0-12.
> This document is retained as an audit trail. See `DEFERRALS.md` for the F-code registry.

**Data:** 2026-03-04
**Totale file:** 391 Python files, ~88,600 LOC
**Metodo:** Lettura batch per batch, ogni file ispezionato
**Batch completati:** 17

---

## Severità Originali

| Severità | Conteggio | Post-Remediation |
|----------|-----------|------------------|
| CRITICAL | ~25 | All resolved |
| HIGH | ~55 | All resolved or ACCEPTED |
| MEDIUM | ~85 | All resolved or ACCEPTED |
| LOW | ~70 | All resolved or ACCEPTED |

---

## Reconciliation — Top 30 Findings

> Cross-reference of every Top 30 finding against Remediation Phases 0-12 and DEFERRALS.md.

| # | File:Line | Severity | Status | Evidence |
|---|-----------|----------|--------|----------|
| 1 | `conftest.py` + 44 test files | CRITICAL | **FIXED** | Phase 9: `sys.exit(2)` → `pytest.skip("Not in venv")` |
| 2 | `train_pipeline.py:6,26` | CRITICAL | **FIXED** | Phase 3: `OUTPUT_DIM` imported from `feature_engineering` |
| 3 | `persistence.py:81-82` | CRITICAL | **FIXED** | Phase 3: explicit `raise StaleCheckpointError` instead of silent return |
| 4 | `backup_manager.py:65` | CRITICAL | **FIXED** | Phase 1: `text()` wrapper for SQLAlchemy 2.x |
| 5 | `demo_parser.py:175-176` | CRITICAL | **FIXED** | Phase 6: `_find_player_column()` method defined |
| 6 | `rag_knowledge.py:450` | CRITICAL | **FIXED** | Phase 5: `_infer_round_phase` imported from `round_utils` (F5-20) |
| 7 | `profile_service.py:39-48` | CRITICAL | **FIXED** | Phase 5: `PlayerProfile` fields aligned to SQLModel (F5-21/F5-22) |
| 8 | `downloader.py:27-45` | CRITICAL | **FIXED** | Phase 6: `BrowserManager.__exit__` context manager protocol (F6-08) |
| 9 | `main.py:310` | CRITICAL | **FIXED** | Phase 7: eager-load profile before session close |
| 10 | `console.py:823` | CRITICAL | **FIXED** | Phase 7/8: removed explicit `session.commit()` inside auto-commit context |
| 11 | `session_engine.py:233` | HIGH | **FIXED** | Phase 12: corrected field to `hltv_status` |
| 12 | `main.py:1320-1332` | HIGH | **FIXED** | Phase 7: demo upload file selection logic corrected |
| 13 | `main.py:1548` | HIGH | **FIXED** | Phase 7: `parsing_dialog = None` after dismiss |
| 14 | `main.py:810` | HIGH | **FIXED** | Phase 7: "Section 2 omitted" placeholder removed, real implementation added |
| 15 | `coaching_dialogue.py:297` | HIGH | **ACCEPTED** | By design: `[:-1]` excludes raw user message; augmented version replaces it (F5-06) |
| 16 | `pro_ingest.py:42` | HIGH | **FIXED** | Phase 6: real player names from demo data |
| 17 | `pro_demo_miner.py:98-120` | HIGH | **ACCEPTED** | Knowledge mining uses metadata extraction (heuristic). Acknowledged in DEFERRALS. |
| 18 | `fetch_hltv_stats.py:214` | HIGH | **FIXED** | Phase 6: `_parse_clutches` removed; HLTV pipeline restructured |
| 19 | `config.py:201` | HIGH | **FIXED** | `load_user_settings()` has try/except with fallback defaults |
| 20 | `console.py:671-677` | HIGH | **FIXED** | Phase 7/8: config key validation added |
| 21 | `match_data_manager.py:222-262` | HIGH | **FIXED** | Phase 1: thread lock added to cache engine |
| 22 | `console.py:766-776` | CRITICAL | **FIXED** | Phase 7/8: file handle properly managed |
| 23 | `factory.py:81` | HIGH | **FIXED** | Phase 3: `hidden_dim` aligned to config default (128) (F3-05) |
| 24 | `rap_coach/memory.py:73-76` | HIGH | **FIXED** | Phase 3: Hopfield/LTC shape mismatch resolved |
| 25 | `training_orchestrator.py:288-300` | HIGH | **FIXED** | Phase 3/12: JEPA validation properly encodes negatives |
| 26 | `hltv_orchestrator.py:1` | CRITICAL | **FIXED** | Phase 6: legacy module deleted |
| 27 | Tests on production DB | CRITICAL | **FIXED** | Phase 9: test isolation via conftest fixtures; `in_memory_db` used |
| 28 | `reset_pro_data.py:74,93-164` | CRITICAL+HIGH | **FIXED** | Phase 8: parameterized queries + context managers |
| 29 | 4 Alembic migrations NOT NULL | HIGH | **ACCEPTED** | SQLite tolerates ALTER ADD without server_default. Documented in DEFERRALS. |
| 30 | `tactical_viewmodels.py:247` | HIGH | **FIXED** | Phase 7: lambda variable capture fixed |

### Summary

- **FIXED:** 27 of 30 (90%)
- **ACCEPTED (by design):** 3 of 30 (10%) — items #15, #17, #29
- **OPEN:** 0 of 30

All Tier 1 "Bloccanti" (items 1-10) are FIXED. All Tier 2 "Funzionalità Rotte" (items 11-20) are FIXED or ACCEPTED. All Tier 3 "Race Conditions" (items 21-30) are FIXED or ACCEPTED.

### Batch-Level Coverage

The audit covered 391 files across 17 batches with ~235 total issues (25 CRITICAL, 55 HIGH, 85 MEDIUM, 70 LOW). Remediation Phases 0-12 addressed 368 total issues — more than the original audit count — because additional issues were discovered and fixed during deep code review.

Remaining items from batches NOT in the Top 30 are either:
- **FIXED** during their respective remediation phase
- **ACCEPTED** as design decisions (documented in DEFERRALS.md)
- **MONITORING** (6 items tracked in DEFERRALS.md — F2-19, F3-18, F6-33, F8-06, F8-11, F6-12)

---
