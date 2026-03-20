# Changelog

All notable changes to the Macena CS2 Analyzer are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-20

### Added
- End-to-end coaching pipeline: WATCH > LEARN > THINK > SPEAK
- JEPA self-supervised pre-training with InfoNCE contrastive loss and EMA target encoder
- RAP Coach architecture (LTC-Hopfield memory, Mixture-of-Experts strategy layer)
- COPER coaching pipeline with 4-level fallback chain (COPER > Hybrid > RAG > Base)
- Experience Bank with EMA effectiveness scoring and context-similarity retrieval
- PySide6/Qt desktop frontend (13 screens, MVVM, 3 visual themes)
- Legacy Kivy/KivyMD frontend (maintained as fallback)
- 4-daemon session engine (Scanner, Digester, Teacher, Pulse)
- 3-stage maturity gating (Calibrating > Learning > Mature)
- HLTV 2.0 rating calculation per match
- Tick-level demo parsing via demoparser2 (zero decimation)
- 25-dimensional canonical feature vector (FeatureExtractor)
- Game-theory analysis (expectiminimax, Bayesian death probability, deception index)
- Neural role classification (5 roles: entry, support, lurk, AWP, anchor)
- Bayesian belief models for opponent mental state tracking
- HLTV pro stats scraping via FlareSolverr/Docker
- Ollama integration for natural-language coaching refinement
- 2D tactical viewer with real-time demo replay
- Temporal baseline decay for skill evolution tracking
- Conviction Index (5-signal composite model confidence)
- RASP integrity checking and integrity manifest
- Cross-platform CI/CD pipeline (GitHub Actions, 6 stages)
- 1500+ automated tests with headless validator
- SQLite WAL mode with auto-migration (Alembic)
- Automated backup strategy with safety gates
- Multi-language support (English, Italian, Portuguese)
- PyInstaller distribution build for Windows

### Security
- SHA-pinned GitHub Actions for supply chain security
- Bandit SAST + detect-secrets + pip-audit in CI
- OS keyring integration for credential storage
- Input validation with Pydantic models at all boundaries
