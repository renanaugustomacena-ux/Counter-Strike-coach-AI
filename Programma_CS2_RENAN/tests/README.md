> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Test Suite

Comprehensive test suite with 390+ tests following the test pyramid (unit > integration > e2e).

## Key Principles

- **No mock data for domain logic** — Real DB data or `pytest.skip`
- **Mocks only at I/O boundaries** — Network, filesystem, external APIs
- **Zero tolerance for synthetic data** — Every value must originate from real sources
- **Test hierarchy** — Unit (>70%) > Integration (>20%) > E2E (~10%)

## Core Test Files

- `conftest.py` — Pytest fixtures (real_db_session, real_player_stats, real_round_stats)
- `test_security.py` — Security tests (shell injection, .env protection)
- `test_services.py` — Service layer tests (CoachingService, AnalysisService, DialogueEngine)
- `test_integration.py` — Integration tests with real database
- `test_temporal_baseline.py` — 20 temporal baseline decay tests
- `test_chronovisor_highlights.py` — ChronovisorScanner tests

## Analysis & ML Tests

- `test_analysis_engines.py`, `test_game_theory.py` — Analysis module tests
- `test_jepa_model.py`, `test_skill_model.py` — ML model tests
- `test_spatial_and_baseline.py`, `test_z_penalty.py` — Spatial engine tests

## Specialized Tests

- `test_demo_parser.py`, `test_dem_validator.py` — Demo parsing tests
- `test_models.py` — Database model tests
- `automated_suite/` — Automated test runner

## Running Tests

```bash
python -m pytest Programma_CS2_RENAN/tests/ -x -q
```
