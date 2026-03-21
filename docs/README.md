# Macena CS2 Analyzer — Documentation Index

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 8 (Documentation Governance)

This directory contains comprehensive documentation for the Macena CS2 Analyzer project — a sophisticated tactical analysis and AI coaching application for Counter-Strike 2. Documentation is organized into user guides, technical specifications, research papers, and utility scripts.

## Directory Structure

```
docs/
├── USER_GUIDE.md                       # Complete user guide (English)
├── USER_GUIDE_IT.md                    # Guida utente completa (Italiano)
├── USER_GUIDE_PT.md                    # Guia do usuário completo (Português)
├── Progetto-Renan-Cs2-AI-Coach.md      # Full architecture specification
├── AI_ARCHITECTURE_ANALYSIS.md         # AI architecture deep-dive (English)
├── AI_ARCHITECTURE_ANALYSIS_IT.md      # Analisi architettura AI (Italiano)
├── AI_ARCHITECTURE_ANALYSIS_PT.md      # Análise da arquitetura AI (Português)
├── ERROR_CODES.md                      # Error code reference
├── EXIT_CODES.md                       # Exit code reference
├── HLTV_SYNC_SERVICE_SPEC.md           # HLTV sync service specification
├── INDUSTRY_STANDARDS_AUDIT.md         # Industry standards compliance audit
├── prompt.md                           # AI assistant prompting guide
├── generate_manual_pdf_it.py           # PDF manual generator utility
├── logging-and-plan.md                 # Logging architecture documentation
├── Studies/                            # 17 research papers (deep dives)
├── Book-Coach-1A*.md/pdf               # Vision book part 1A
├── Book-Coach-1B*.md/pdf               # Vision book part 1B
├── Book-Coach-2*.md/pdf                # Vision book part 2
├── Book-Coach-3*.md/pdf                # Vision book part 3
└── package.json                        # Docs tooling (markdownlint, etc.)
```

## User Documentation

### User Guides (3 Languages)

The user guides cover installation, setup, feature walkthroughs, troubleshooting, and best practices:

- **[USER_GUIDE.md](USER_GUIDE.md)** — Complete user guide (English)
- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia do usuário completo (Português)

Each guide covers:
1. Installation and environment setup
2. First demo ingestion (the 10/10 rule)
3. Coaching screen walkthrough
4. Match history and performance analysis
5. Settings and configuration
6. Troubleshooting common issues

## Technical Documentation

### Architecture Specifications

- **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** — Full 12-section architecture specification (Italian)
  - System architecture and data flow diagrams (Mermaid)
  - Neural network models (RAP Coach, JEPA, NeuralRoleHead)
  - Memory systems (LTC-Hopfield hybrid)
  - Coaching pipeline (COPER mode)
  - Database schema and storage architecture
  - UI/UX design patterns (MVVM)

- **AI Architecture Analysis** — Deep-dive into the AI subsystem
  - [English](AI_ARCHITECTURE_ANALYSIS.md) | [Italian](AI_ARCHITECTURE_ANALYSIS_IT.md) | [Portuguese](AI_ARCHITECTURE_ANALYSIS_PT.md)

### Reference Documents

| Document | Purpose |
|----------|---------|
| [ERROR_CODES.md](ERROR_CODES.md) | All error codes with causes and remediation |
| [EXIT_CODES.md](EXIT_CODES.md) | Process exit codes for scripts and daemons |
| [HLTV_SYNC_SERVICE_SPEC.md](HLTV_SYNC_SERVICE_SPEC.md) | HLTV pro stats scraper specification |
| [INDUSTRY_STANDARDS_AUDIT.md](INDUSTRY_STANDARDS_AUDIT.md) | Compliance audit against industry standards |
| [logging-and-plan.md](logging-and-plan.md) | Structured logging architecture and roadmap |

### AI Assistant Integration

- **[prompt.md](prompt.md)** — Structured prompts and workflows for AI-assisted development, code review, and system maintenance

### Vision Books

The "Coach Books" describe the full product vision, technical architecture, and business strategy:

| Book | Focus |
|------|-------|
| Book-Coach-1A | Foundation: problem statement, market analysis, product vision |
| Book-Coach-1B | Technical: neural architectures, training pipeline, data model |
| Book-Coach-2 | Implementation: coaching modes, UI/UX, integration points |
| Book-Coach-3 | Strategy: monetization, SDK licensing, open-core model |

Available in Markdown and PDF formats, in English, Italian, and Portuguese.

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

### `generate_manual_pdf_it.py`

Converts the Italian user guide (`USER_GUIDE_IT.md`) to a formatted PDF manual using markdown-to-PDF conversion. Run from the project root:

```bash
python docs/generate_manual_pdf_it.py
```

### `package.json`

Docs tooling configuration for markdownlint and other Markdown quality checks. Install with:

```bash
cd docs && npm install
```

## Getting Started

1. Start with **[USER_GUIDE.md](USER_GUIDE.md)** for installation and setup
2. Review **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** for system architecture
3. Explore **[Studies/](Studies/)** for deep technical understanding
4. Check **[ERROR_CODES.md](ERROR_CODES.md)** when debugging issues

## Development Notes

- All documentation is in Markdown format for maximum portability
- Technical terms, class names, and code references remain in English across all translations
- Mermaid diagrams are used for architecture and data flow visualization
- PDF generation requires the `markdown` and `weasyprint` Python packages
- The `CLAUDE.md` file at the project root contains engineering principles and development guidelines
