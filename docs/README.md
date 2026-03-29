# Macena CS2 Analyzer — Documentation Index

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Primary Document

**[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — The unified technical reference for the entire project. Contains: system architecture, current state audit, open findings, execution plan (phased surgeries), product roadmap, troubleshooting guide, and all appendices (error codes, env vars, feature vector spec, database schema). **Start here.**

## Directory Structure

```
docs/
├── ENGINEERING_HANDOFF.md          # Unified technical reference (start here)
├── QUICKSTART.md                   # 5-minute quick-start guide
├── README.md / _IT.md / _PT.md    # This index (3 languages)
│
├── books/                          # Vision books (project vision & architecture)
│   ├── Book-Coach-1A.md / .pdf     # Neural core: JEPA, VL-JEPA, AdvancedCoachNN
│   ├── Book-Coach-1B.md / .pdf     # RAP Coach, data sources (demo, HLTV, Steam)
│   ├── Book-Coach-2.md / .pdf      # Services, analysis engines, COPER, database
│   └── Book-Coach-3.md / .pdf      # Program logic, Qt UI, ingestion, tools, build
│
├── guides/                         # User-facing documentation
│   ├── USER_GUIDE.md               # Complete user guide (English)
│   ├── USER_GUIDE_IT.md            # Guida utente (Italiano)
│   └── USER_GUIDE_PT.md            # Guia do usuário (Português)
│
├── Studies/                        # 17 research papers (theoretical foundations)
│   ├── README.md / _IT.md / _PT.md # Study index
│   ├── Fondamenti-Epistemici.md    # Epistemics & truth
│   ├── Architettura-JEPA.md        # JEPA architecture
│   └── ... (15 more)               # See Studies/README.md
│
├── archive/                        # Superseded documents (kept for reference)
│   ├── AI_ARCHITECTURE_ANALYSIS.md # Superseded by ENGINEERING_HANDOFF
│   ├── PROJECT_SURGERY_PLAN.md     # Superseded by ENGINEERING_HANDOFF
│   ├── PRODUCT_VIABILITY_ASSESSMENT.md
│   ├── INDUSTRY_STANDARDS_AUDIT.md
│   ├── logging-and-plan.md
│   ├── MISSION_RULES.md
│   ├── cybersecurity.md
│   ├── ERROR_CODES.md
│   ├── EXIT_CODES.md
│   └── prompt.md
│
└── tooling/                        # PDF generation utilities
    ├── generate_zh_pdfs.py         # Chinese PDF generator
    ├── md2pdf.mjs                  # Markdown to PDF (Node.js)
    └── package.json                # npm dependencies
```

## Reading Order

1. **[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Technical reference, execution plan, current state
2. **[QUICKSTART.md](QUICKSTART.md)** — Get the app running in 5 minutes
3. **[guides/USER_GUIDE.md](guides/USER_GUIDE.md)** — Full user walkthrough
4. **[books/](books/)** — Vision books (1A -> 1B -> 2 -> 3) for the full product vision
5. **[Studies/](Studies/)** — Deep research papers on theoretical foundations

## Quick Reference

| Need | Go to |
|------|-------|
| What is this project? | ENGINEERING_HANDOFF, Section 1 |
| What works today? | ENGINEERING_HANDOFF, Part II |
| What needs fixing? | ENGINEERING_HANDOFF, Part III (Open Findings Registry) |
| How to fix it (ordered steps)? | ENGINEERING_HANDOFF, Part IV (Execution Plan) |
| Error codes | ENGINEERING_HANDOFF, Appendix A |
| Environment variables | ENGINEERING_HANDOFF, Appendix C |
| Feature vector (25-dim) | ENGINEERING_HANDOFF, Appendix E |
| Database schema | ENGINEERING_HANDOFF, Appendix F |
| Troubleshooting | ENGINEERING_HANDOFF, Appendix G |
| Product roadmap | ENGINEERING_HANDOFF, Part V |

## Notes

- The `archive/` directory contains the original individual documents that were consolidated into ENGINEERING_HANDOFF.md. They are preserved for historical reference.
- The Vision Books (books/) describe the aspirational product vision. They will be updated to match the codebase once the program is stable.
- All documentation is in Markdown format. PDFs are generated with the tools in `tooling/`.
- The `CLAUDE.md` file at the project root contains engineering directives and development rules.
