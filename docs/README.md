# Macena CS2 Analyzer — Documentation Index

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Primary References (project root)

| Document | Purpose |
|----------|---------|
| **[REFERENCE.md](../REFERENCE.md)** | Architecture, dim contract, constants, skills, tests, configs |
| **[TASKS.md](../TASKS.md)** | Backlog, errors, execution status |
| **[CHANGELOG.md](../CHANGELOG.md)** | Change history |

## Directory Structure

```
docs/
├── QUICKSTART.md                   # 5-minute quick-start guide
├── README.md / _IT.md / _PT.md     # This index (3 languages)
│
├── RE_INGESTION_GUIDE.md           # Ops: full re-ingestion & training pipeline
├── concurrency_policy.md           # Ops: DB lock policy for long-running migrations
├── rollback_procedure.md           # Ops: DB rollback to the 2026-05-03 baseline
├── strategy_taxonomy.md            # coachingexperience.strategy_label taxonomy
│
├── DIAGNOSIS_2026-05.md            # Historical: May 2026 data diagnosis
├── SESSION_HANDOFF.md              # Historical: session handoff notes
├── jepa_training_tuning_observations_2026-05-06.md   # Historical training notes
├── rap_training_known_issue_2026-05-05.md            # Historical known issue
├── restoration_baseline_2026-05-03.json              # Rollback baseline row counts
├── d2a/d2c/d3/d4/m1 *_report_*.json, dem_availability.json,
│   playermatchstats_coverage_report_2026-05-05.json  # Historical run reports (dated)
│
├── books/                          # Vision books (project vision & architecture)
│   ├── Book-Coach-1A .md/.pdf      # Neural core: JEPA, VL-JEPA, AdvancedCoachNN
│   ├── Book-Coach-1B .md/.pdf      # RAP Coach, data sources (demo, HLTV, Steam)
│   ├── Book-Coach-2  .md/.pdf      # Services, analysis engines, COPER, database
│   ├── Book-Coach-3  .md/.pdf      # Program logic, Qt UI, ingestion, tools, build
│   │                               # (each with -en / -pt variants)
│   ├── analogy-book .md/.pdf       # Analogy companion (with -en / -pt variants)
│   ├── codebase-understanding/     # 9-chapter codebase walkthrough (01–09)
│   ├── REFACTOR_PLAN.md
│   └── TRANSLATION_GLOSSARY.md
│
├── guides/                         # User-facing documentation
│   ├── USER_GUIDE.md               # Complete user guide (English)
│   ├── USER_GUIDE_IT.md            # Guida utente (Italiano)
│   └── USER_GUIDE_PT.md            # Guia do usuário (Português)
│
├── research/                       # Research library catalog
│   └── INDEX.md                    # Bibliography index; the PDFs themselves are
│                                   # git-ignored and not present in a fresh checkout
│
├── ux-audit/                       # UX visual audit + screen renders
│   ├── UX_VISUAL_AUDIT.md
│   └── renders/                    # CS16 / CS2 / CSGO screenshots
│
└── tooling/                        # PDF generation utilities
    ├── generate_zh_pdfs.py         # Mermaid → SVG + dark-themed PDF generator
    ├── md2pdf.mjs                  # Markdown to PDF (Node.js)
    └── package.json / package-lock.json
```

## Reading Order

1. **[../REFERENCE.md](../REFERENCE.md)** — Architecture, invariants, technical reference
2. **[QUICKSTART.md](QUICKSTART.md)** — Get the app running in 5 minutes
3. **[guides/USER_GUIDE.md](guides/USER_GUIDE.md)** — Full user walkthrough
4. **[books/](books/)** — Vision books (1A -> 1B -> 2 -> 3) for the full product vision
5. **[research/INDEX.md](research/INDEX.md)** — Research paper bibliography

## Quick Reference

| Need | Go to |
|------|-------|
| What is this project? | `../README.md` |
| Architecture and invariants | `../REFERENCE.md` |
| Backlog and execution plan | `../TASKS.md` |
| Feature vector (25-dim) | `../REFERENCE.md` §2 |
| Storage architecture / schema | `../REFERENCE.md` §5 |
| Re-ingestion / training pipeline | `RE_INGESTION_GUIDE.md` |
| Troubleshooting | `guides/USER_GUIDE.md` — Troubleshooting section |
| In-app help content | `../Programma_CS2_RENAN/data/docs/troubleshooting.md` |

## Notes

- Files with dates in their names (`*_2026-*`) are historical snapshots from past
  restoration/training runs — they describe the state at that date, not the current state.
- The Vision Books (books/) describe the aspirational product vision. They will be updated
  to match the codebase once the program is stable.
- All documentation is in Markdown format. PDFs are generated with the tools in `tooling/`.
