> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Suite di Test

Suite di test completa con oltre 1,515 test seguendo la piramide di test (unit > integration > e2e).

## Principi Fondamentali

- **Nessun dato mock per la logica di dominio** — Dati DB reali o `pytest.skip`
- **Mock solo ai confini I/O** — Rete, filesystem, API esterne
- **Tolleranza zero per dati sintetici** — Ogni valore deve provenire da fonti reali
- **Gerarchia di test** — Unit (>70%) > Integration (>20%) > E2E (~10%)

## File di Test Principali

- `conftest.py` — Fixture Pytest (real_db_session, real_player_stats, real_round_stats)
- `test_security.py` — Test di sicurezza (shell injection, protezione .env)
- `test_services.py` — Test del livello servizi (CoachingService, AnalysisService, DialogueEngine)
- `test_integration.py` — Test di integrazione con database reale
- `test_temporal_baseline.py` — 20 test di decadimento baseline temporale
- `test_chronovisor_highlights.py` — Test ChronovisorScanner

## Test di Analisi e ML

- `test_analysis_engines.py`, `test_game_theory.py` — Test moduli di analisi
- `test_jepa_model.py`, `test_skill_model.py` — Test modelli ML
- `test_spatial_and_baseline.py`, `test_z_penalty.py` — Test motore spaziale

## Test Specializzati

- `test_demo_parser.py`, `test_dem_validator.py` — Test parsing demo
- `test_models.py` — Test modelli database
- `automated_suite/` — Esecutore test automatizzato

## Esecuzione Test

```bash
python -m pytest Programma_CS2_RENAN/tests/ -x -q
```
