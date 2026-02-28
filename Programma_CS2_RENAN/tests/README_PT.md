> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Suíte de Testes

Suíte de testes abrangente com mais de 390 testes seguindo a pirâmide de testes (unit > integration > e2e).

## Princípios Fundamentais

- **Nenhum dado mock para lógica de domínio** — Dados DB reais ou `pytest.skip`
- **Mocks apenas em limites I/O** — Rede, sistema de arquivos, APIs externas
- **Tolerância zero para dados sintéticos** — Todo valor deve originar de fontes reais
- **Hierarquia de testes** — Unit (>70%) > Integration (>20%) > E2E (~10%)

## Arquivos de Teste Principais

- `conftest.py` — Fixtures Pytest (real_db_session, real_player_stats, real_round_stats)
- `test_security.py` — Testes de segurança (shell injection, proteção .env)
- `test_services.py` — Testes da camada de serviços (CoachingService, AnalysisService, DialogueEngine)
- `test_integration.py` — Testes de integração com banco de dados real
- `test_temporal_baseline.py` — 20 testes de decaimento de baseline temporal
- `test_chronovisor_highlights.py` — Testes ChronovisorScanner

## Testes de Análise e ML

- `test_analysis_engines.py`, `test_game_theory.py` — Testes de módulos de análise
- `test_jepa_model.py`, `test_skill_model.py` — Testes de modelos ML
- `test_spatial_and_baseline.py`, `test_z_penalty.py` — Testes do motor espacial

## Testes Especializados

- `test_demo_parser.py`, `test_dem_validator.py` — Testes de parsing de demos
- `test_models.py` — Testes de modelos de banco de dados
- `automated_suite/` — Executor de testes automatizado

## Executando Testes

```bash
python -m pytest Programma_CS2_RENAN/tests/ -x -q
```
