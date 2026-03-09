# Audit Reports — Document Index

> **Last Updated:** 2026-03-09
> **Project:** Macena CS2 Analyzer
> **Status:** All remediation complete. 368 issues fixed across 12 phases. All documents cross-referenced.

---

## Active Documents (01-10)

Comprehensive audit reports from the latest review cycle. Cross-referenced against current codebase on 2026-03-09.

| Document | Scope | Open Findings | Notes |
|----------|-------|:---:|-------|
| `01_FOUNDATION_ARCHITECTURE.md` | Core architecture, config, lifecycle | Pruned | Cross-referenced 2026-03-08 |
| `02_DATA_PERSISTENCE.md` | Database, storage, backup, migrations | Pruned | Cross-referenced 2026-03-08 |
| `03_DATA_ACQUISITION.md` | Demo parsing, HLTV, Steam, ingestion | Pruned | Cross-referenced 2026-03-08 |
| `04_FEATURE_ENGINEERING.md` | Feature pipeline, vectorizer, baselines | Pruned | Cross-referenced 2026-03-08 |
| `05_NEURAL_NETWORKS.md` | RAP Coach, JEPA, training, inference | Pruned | Cross-referenced 2026-03-08 |
| `06_ANALYSIS_COACHING.md` | Game theory, coaching service, analysis | Pruned | Cross-referenced 2026-03-08 |
| `07_DESKTOP_APPLICATION.md` | Kivy UI, screens, viewmodels, layout | ~64 | 13 OBSOLETE removed, 6 EVOLVED |
| `08_TESTING_QUALITY.md` | Test suite, CI/CD, validation | ~44 | 4 OBSOLETE removed (both HIGHs fixed) |
| `09_PIPELINE_AUDIT.md` | End-to-end pipeline audit | 39 VALID | 26 FIXED, 12 EVOLVED, 6 BY_DESIGN |
| `10_LITERATURE_REVIEW.md` | Academic analysis (Sections 1-2 only) | N/A | Section 3 removed (debunked) |

---

## Archived Documents

Historical audit reports from the initial code audit (Feb 27) and remediation tracking (Feb-Mar 2026). All findings have been cross-referenced and resolved.

### Phase Reports (condensed — FIXED items removed)

| Document | Original Issues | Remaining | Status |
|----------|---:|---:|--------|
| `archive/phase01_foundation_storage.md` | 37 | 0 | All resolved |
| `archive/phase02_processing_pipeline.md` | 42 | 13 | 12 ACCEPTED, 1 MONITORING |
| `archive/phase03_neural_networks.md` | 38 | 6 | 5 ACCEPTED, 1 MONITORING |
| `archive/phase04_analysis_coaching.md` | 24 | 1 | 1 ACCEPTED |
| `archive/phase05_services_knowledge.md` | 38 | 3 | 3 ACCEPTED |
| `archive/phase06_core_datasources_ingestion.md` | 34 | 9 | 8 ACCEPTED, 1 MONITORING |
| `archive/phase07_ui_entrypoints.md` | 42 | 9 | 9 ACCEPTED |
| `archive/phase08_tools_validation.md` | 38 | 12 | 10 ACCEPTED, 2 MONITORING |
| `archive/phase09_test_suite.md` | 35 | 3 | 3 ACCEPTED |
| **Total** | **328** | **56** | **51 ACCEPTED, 5 MONITORING** |

### Tracking Documents

| Document | Purpose | Status |
|----------|---------|--------|
| `archive/BATCH_AUDIT_2026-03-04.md` | Systematic audit of 391 files (Italian). Top 30 reconciliation. | Historical — all resolved |
| `archive/FINAL_SYNTHESIS.md` | Executive summary of phase reports | Historical — updated with final stats |
| `archive/DEFERRALS.md` | F-code registry (170 codes) | 111 FIXED, 54 ACCEPTED, 5 MONITORING |
| `archive/REMEDIATION_PLAN.md` | Master plan for 12 remediation phases | Complete — all phases executed |
| `archive/AISTATE.md` | G-issue tracker (9 issues) | Complete — all 9 resolved |
| `archive/PHASE11_REVIEW.md` | Phase 11 review plan | Complete — all action items executed |
| `archive/VALIDATION_REPORT.md` | Headless validator snapshot | 296/298 PASS |

---

## Remaining Open Items (5 MONITORING)

These items are tracked and await production data or future enhancement:

| F-Code | File | Description |
|--------|------|-------------|
| F2-19 | `role_thresholds.py` | Inter-threshold consistency validation stub |
| F3-18 | `evaluate.py` | Zero-vector SHAP baseline (replace with training sample mean) |
| F6-33 | `event_registry.py` | Handler path references not validated at registration |
| F8-06 | `Goliath_Hospital.py` | Regex-based import scan (matches in comments/strings) |
| F8-11 | `context_gatherer.py` | Substring matching creates false reverse deps |

---

## Document Lineage

```
Feb 27, 2026  Initial deep code audit (262 files, 328 issues)
              → phase01-09 reports + FINAL_SYNTHESIS
Feb 28        Remediation begins (Phase 1)
Mar 04        BATCH_AUDIT (391 files, ~235 issues, Italian)
Mar 06        REMEDIATION_PLAN created
Mar 07        PHASE11_REVIEW plan
Mar 08        All 12 phases complete (368 fixes)
              Comprehensive audit 01-08 created
              Pipeline audit: 83 issues cataloged
Mar 09        All documents cross-referenced against current codebase
              26 pipeline findings confirmed FIXED
              Section 3 of literature review removed (debunked)
              All historical documents archived
```
