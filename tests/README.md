> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Root-Level Verification and Forensic Tests

Root-level verification and forensic tests for critical system components.

## Purpose

These tests verify end-to-end functionality, data integrity, and critical subsystem behavior using real production-like data.

## Key Test Files

- `conftest.py` — Root-level fixtures for verification tests
- `verify_chronovisor_logic.py` — Chronovisor logic verification (scale detection, deduplication)
- `verify_chronovisor_real.py` — Chronovisor verification with real demo data
- `verify_csv_ingestion.py` — CSV ingestion pipeline verification
- `verify_map_integration.py` — Map integration and spatial data verification
- `verify_reporting.py` — Reporting pipeline verification (PDF generation, visualizations)
- `verify_superposition.py` — Superposition network verification
- `setup_golden_data.py` — Golden test data setup for regression testing

## Test Philosophy

- **Forensic approach** — Tests investigate real data paths and actual system behavior
- **No synthetic data** — All tests use real demo files or production-equivalent data
- **Skip if unavailable** — Tests skip gracefully if required data is missing
- **End-to-end coverage** — Focus on integration points and cross-module workflows

## Running Verification Tests

```bash
# Run all verification tests
python -m pytest tests/ -v

# Run specific verification
python tests/verify_chronovisor_real.py

# Setup golden data for regression testing
python tests/setup_golden_data.py
```

## Notes

These tests complement the main test suite in `Programma_CS2_RENAN/tests/` with higher-level, integration-focused verification.
