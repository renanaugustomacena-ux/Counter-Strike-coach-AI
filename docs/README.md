# Macena CS2 Analyzer — Documentation Index

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 8 (Documentation Governance)

This directory contains comprehensive documentation for the Macena CS2 Analyzer project — a sophisticated tactical analysis and AI coaching application for Counter-Strike 2. Documentation is organized into user guides, technical specifications, research papers, vision books, and utility scripts.

## Directory Structure

```
docs/
├── USER_GUIDE.md                       # Complete user guide (English)
├── USER_GUIDE_IT.md                    # Guida utente completa (Italiano)
├── USER_GUIDE_PT.md                    # Guia do usuário completo (Português)
├── QUICKSTART.md                       # Quick-start guide
├── AI_ARCHITECTURE_ANALYSIS.md         # AI architecture deep-dive (English)
├── AI_ARCHITECTURE_ANALYSIS_IT.md      # Analisi architettura AI (Italiano)
├── AI_ARCHITECTURE_ANALYSIS_PT.md      # Análise da arquitetura AI (Português)
├── ERROR_CODES.md                      # Error code reference
├── EXIT_CODES.md                       # Exit code reference
├── INDUSTRY_STANDARDS_AUDIT.md         # Industry standards compliance audit
├── MISSION_RULES.md                    # Project mission and rules
├── PRODUCT_VIABILITY_ASSESSMENT.md     # Product viability analysis
├── PROJECT_SURGERY_PLAN.md             # Architecture surgery plan
├── cybersecurity.md                    # Cybersecurity assessment
├── prompt.md                           # AI assistant prompting guide
├── logging-and-plan.md                 # Logging architecture documentation
├── Book-Coach-1A.md/pdf               # Vision book part 1A — Neural core
├── Book-Coach-1B.md/pdf               # Vision book part 1B — RAP Coach & data sources
├── Book-Coach-2.md/pdf                # Vision book part 2 — Services & infrastructure
├── Book-Coach-3.md/pdf                # Vision book part 3 — Program logic & UI
├── Studies/                            # 17 research papers (deep dives)
├── generate_zh_pdfs.py                 # Chinese PDF generation utility
├── md2pdf.mjs                          # Markdown to PDF converter (Node.js)
└── package.json                        # Docs tooling (markdownlint, etc.)
```

## User Documentation

### User Guides (3 Languages)

The user guides cover installation, setup, feature walkthroughs, troubleshooting, and best practices:

- **[USER_GUIDE.md](USER_GUIDE.md)** — Complete user guide (English)
- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia do usuário completo (Português)
- **[QUICKSTART.md](QUICKSTART.md)** — Quick-start guide for getting up and running fast

Each guide covers:
1. Installation and environment setup
2. First demo ingestion (the 10/10 rule)
3. Coaching screen walkthrough
4. Match history and performance analysis
5. Settings and configuration
6. Troubleshooting common issues

## Technical Documentation

### Architecture Specifications

- **AI Architecture Analysis** — Deep-dive into the AI subsystem
  - [English](AI_ARCHITECTURE_ANALYSIS.md) | [Italian](AI_ARCHITECTURE_ANALYSIS_IT.md) | [Portuguese](AI_ARCHITECTURE_ANALYSIS_PT.md)

### Reference Documents

| Document | Purpose |
|----------|---------|
| [ERROR_CODES.md](ERROR_CODES.md) | All error codes with causes and remediation |
| [EXIT_CODES.md](EXIT_CODES.md) | Process exit codes for scripts and daemons |
| [INDUSTRY_STANDARDS_AUDIT.md](INDUSTRY_STANDARDS_AUDIT.md) | Compliance audit against industry standards |
| [MISSION_RULES.md](MISSION_RULES.md) | Project mission statement and development rules |
| [PRODUCT_VIABILITY_ASSESSMENT.md](PRODUCT_VIABILITY_ASSESSMENT.md) | Product viability and market analysis |
| [PROJECT_SURGERY_PLAN.md](PROJECT_SURGERY_PLAN.md) | Architecture surgery and refactoring plan |
| [cybersecurity.md](cybersecurity.md) | Cybersecurity assessment and threat model |
| [logging-and-plan.md](logging-and-plan.md) | Structured logging architecture and roadmap |

### AI Assistant Integration

- **[prompt.md](prompt.md)** — Structured prompts and workflows for AI-assisted development, code review, and system maintenance

### Vision Books

The "Coach Books" describe the full product vision, technical architecture, and business strategy:

| Book | Focus | Size |
|------|-------|------|
| [Book-Coach-1A](Book-Coach-1A.md) | Neural core: JEPA, VL-JEPA, AdvancedCoachNN, MaturityObservatory | 1,315 lines |
| [Book-Coach-1B](Book-Coach-1B.md) | RAP Coach (7 components), data sources (demo, HLTV, Steam, FACEIT, FAISS) | 1,176 lines |
| [Book-Coach-2](Book-Coach-2.md) | Services, 10 analysis engines, knowledge/RAG/COPER, database, training pipeline | 2,492 lines |
| [Book-Coach-3](Book-Coach-3.md) | Full program logic, Qt UI (13 screens), ingestion, tools, tests, build | 3,143 lines |

Available in Markdown and PDF formats.

## Research & Deep Dives

### Studies Directory

The **[Studies/](Studies/)** directory contains 17 in-depth technical research papers covering the theoretical foundations and implementation details:

- **Epistemics & Game Theory:** Bayesian belief networks, rational adversarial play, death probability estimation
- **Coaching Architecture:** RAP Coach design, COPER mode (Context + Observation + Pro Reference + Experience + Reasoning)
- **Spatial Intelligence:** Z-cutoff handling, multi-level maps (Nuke, Vertigo), engagement range analysis
- **Momentum Systems:** Temporal momentum modeling, critical moment detection, baseline decay
- **Neural Architectures:** VL-JEPA vision-language alignment, Hopfield memory integration, LTC dynamics
- **Feature Engineering:** Unified 25-dimensional tactical vector, heuristic quantization
- **Analysis Pipelines:** Round-level statistics, HLTV 2.0 rating computation, utility usage analysis

## Utilities

### `generate_zh_pdfs.py`

Generates Chinese PDF versions of documentation. Run from the project root:

```bash
python docs/generate_zh_pdfs.py
```

### `md2pdf.mjs`

Node.js-based Markdown to PDF converter. Requires npm dependencies:

```bash
cd docs && npm install && node md2pdf.mjs
```

### `package.json`

Docs tooling configuration for markdownlint and PDF generation.

## Getting Started

1. Start with **[QUICKSTART.md](QUICKSTART.md)** or **[USER_GUIDE.md](USER_GUIDE.md)** for installation and setup
2. Read the **Vision Books** (1A → 1B → 2 → 3) for the full system architecture
3. Explore **[Studies/](Studies/)** for deep technical understanding
4. Check **[ERROR_CODES.md](ERROR_CODES.md)** when debugging issues

## Development Notes

- All documentation is in Markdown format for maximum portability
- Technical terms, class names, and code references remain in English across all translations
- PDF generation requires either the Node.js toolchain or Python packages
- The `CLAUDE.md` file at the project root contains engineering principles and development guidelines
