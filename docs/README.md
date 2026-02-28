# Macena CS2 Analyzer - Documentation Index

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

This directory contains comprehensive documentation for the Macena CS2 Analyzer project, a sophisticated tactical analysis and AI coaching application for Counter-Strike 2.

## User Documentation

### User Guides
- **[USER_GUIDE.md](USER_GUIDE.md)** — Complete user guide (English)
  Installation, setup, feature walkthroughs, troubleshooting, and best practices

- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
  Italian translation of the complete user guide

- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia do usuário completo (Português)
  Brazilian Portuguese translation of the complete user guide

## Technical Documentation

### Architecture & Design
- **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** — Full project architecture specification (Italian)
  Comprehensive 12-section technical specification with Mermaid diagrams covering:
  - System architecture and data flow
  - Neural network models (RAP Coach, JEPA, NeuralRoleHead)
  - Memory systems (LTC-Hopfield)
  - Coaching pipeline (COPER mode)
  - Database schema and storage architecture
  - UI/UX design patterns

### AI Assistant Integration
- **[prompt.md](prompt.md)** — AI assistant prompting guide
  Structured prompts and workflows for AI-assisted development, code review, and system maintenance

### Utilities
- **[generate_manual_pdf_it.py](generate_manual_pdf_it.py)** — PDF manual generator
  Converts the Italian user guide to a formatted PDF manual

## Research & Deep Dives

### Studies Directory
The **[Studies/](Studies/)** directory contains 17 in-depth technical research papers covering the theoretical foundations and implementation details of the system:

- **Epistemics & Game Theory:** Bayesian belief networks, rational adversarial play, death probability estimation
- **Coaching Architecture:** RAP Coach design, COPER mode (Context + Observation + Pro Reference + Experience + Reasoning)
- **Spatial Intelligence:** Z-cutoff handling, multi-level maps, engagement range analysis
- **Momentum Systems:** Temporal momentum modeling, critical moment detection, baseline decay
- **Neural Architectures:** VL-JEPA vision-language alignment, Hopfield memory integration, LTC dynamics
- **Feature Engineering:** Unified 25-dimensional tactical vector, heuristic quantization
- **Analysis Pipelines:** Round-level statistics, HLTV 2.0 rating, utility usage analysis

## Getting Started

1. Start with **[USER_GUIDE.md](USER_GUIDE.md)** for installation and setup
2. Review **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** for system architecture
3. Explore **[Studies/](Studies/)** for deep technical understanding

## Contributing

See the project root `CLAUDE.md` for engineering principles and development guidelines.
