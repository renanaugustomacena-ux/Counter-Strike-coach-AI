> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Testes de Verificação e Forenses no Nível Raiz

Testes de verificação e forenses no nível raiz para componentes críticos do sistema.

## Propósito

Estes testes verificam funcionalidade end-to-end, integridade de dados e comportamento de subsistemas críticos usando dados reais semelhantes aos de produção.

## Arquivos de Teste Principais

- `conftest.py` — Fixtures de nível raiz para testes de verificação
- `verify_chronovisor_logic.py` — Verificação de lógica do Chronovisor (detecção de escala, deduplicação)
- `verify_chronovisor_real.py` — Verificação do Chronovisor com dados de demo reais
- `verify_csv_ingestion.py` — Verificação do pipeline de ingestão CSV
- `verify_map_integration.py` — Verificação de integração de mapas e dados espaciais
- `verify_reporting.py` — Verificação do pipeline de relatórios (geração PDF, visualizações)
- `verify_superposition.py` — Verificação da rede de superposição
- `setup_golden_data.py` — Configuração de dados golden para testes de regressão

## Filosofia de Testes

- **Abordagem forense** — Testes investigam caminhos de dados reais e comportamento efetivo do sistema
- **Nenhum dado sintético** — Todos os testes usam arquivos de demo reais ou dados equivalentes a produção
- **Skip se indisponível** — Testes pulam graciosamente se dados necessários estiverem ausentes
- **Cobertura end-to-end** — Foco em pontos de integração e workflows entre módulos

## Executando Testes de Verificação

```bash
# Executar todos os testes de verificação
python -m pytest tests/ -v

# Executar verificação específica
python tests/verify_chronovisor_real.py

# Configurar dados golden para testes de regressão
python tests/setup_golden_data.py
```

## Notas

Estes testes complementam a suíte de testes principal em `Programma_CS2_RENAN/tests/` com verificação de nível superior focada em integração.
